"""Workflow orchestration and the only supported route to adapter writes."""

import hashlib
from pathlib import Path

from .adapters import LocalCandidateStore
from .evaluation import evaluate
from .models import digest, job_key, validate_job
from .permissions import form_gates, permission


class Workflow:
    def __init__(self, state, provider, candidates=None):
        self.state = state
        self.provider = provider
        self.candidates = candidates or LocalCandidateStore(state)

    def discover(self, source):
        candidate = self.candidates.load()
        results = []
        for job in source.discover({"target_roles": candidate["target_roles"]}):
            validate_job(job)
            key = job_key(job)
            added = self.state.discover(key, job)
            results.append({"key": key, "decision": "DISCOVERED" if added else "DUPLICATE"})
        return results

    def evaluate(self, key):
        record = self.state.get(key)
        result = evaluate(self.candidates.load(), record["body"]["job"])
        record = self.state.transition(key, "EVALUATED", {"evaluation": result, "packet": None}, record["revision"])
        if result["decision"] != "MATCH":
            self.state.transition(key, "REJECTED" if result["decision"] == "REJECT" else "HUMAN_REQUIRED",
                                  expected_revision=record["revision"])
        return result

    def refresh(self, key, job):
        """Explicitly replace a changed posting without creating a new requisition."""
        validate_job(job)
        if job_key(job) != key:
            raise ValueError("Refreshed posting must identify the same exact job")
        record = self.state.get(key)
        result = evaluate(self.candidates.load(), job)
        record = self.state.transition(key, "EVALUATED", {"job": job, "packet": None, "evaluation": result}, record["revision"])
        if result["decision"] != "MATCH":
            self.state.transition(key, "REJECTED" if result["decision"] == "REJECT" else "HUMAN_REQUIRED",
                                  expected_revision=record["revision"])
        return result

    def _resume_gates(self, candidate):
        resume = candidate.get("resume", {})
        try:
            path = Path(resume["path"]).resolve()
            if not path.is_relative_to(self.state.home) or not path.is_file():
                return ["missing_original_resume"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != resume["sha256"]:
                return ["resume_changed"]
        except (KeyError, OSError, TypeError):
            return ["missing_original_resume"]
        return []

    def prepare(self, key):
        candidate, policy = self.candidates.load(), self.state.setting("policy")
        decision = permission(policy, "prepare")
        if not decision["allowed"]:
            return decision
        record = self.state.get(key)
        if record["state"] not in {"EVALUATED", "RESEARCHED", "TAILORED"}:
            raise ValueError("Evaluate the job before preparing it")
        job = record["body"]["job"]
        result = evaluate(candidate, job)
        form = self.provider.inspect(job)
        gates = result["reasons"] + form_gates(candidate, job, form) + self._resume_gates(candidate)
        if gates:
            if record["state"] == "TAILORED":
                record = self.state.transition(key, "EVALUATED", expected_revision=record["revision"])
            self.state.transition(key, "HUMAN_REQUIRED", {"gates": sorted(set(gates))}, record["revision"])
            return {"allowed": False, "reason": "human_required", "gates": sorted(set(gates))}
        answers = {}
        for question in form["questions"]:
            fact = candidate["facts"].get(question["fact"])
            if fact and fact["status"] == "confirmed":
                answers[question["id"]] = {"value": fact["value"], "source": fact["source"]}
        packet = {"schema_version": 1, "job_key": key, "candidate_hash": digest(candidate),
                  "job_hash": digest(job), "provider": self.provider.adapter_id, "form": form,
                  "claims": result["claims"], "evidence": result["evidence"], "answers": answers,
                  "resume": candidate["resume"], "display_name": candidate["display_name"]}
        if record["state"] == "EVALUATED":
            record = self.state.transition(key, "RESEARCHED", {"source_review": result["evidence"]}, record["revision"])
        if record["state"] == "RESEARCHED":
            record = self.state.transition(key, "TAILORED", {"packet": packet}, record["revision"])
        else:
            # Recover an interrupted prepare only if the old packet still matches.
            if record["body"].get("packet") != packet:
                raise ValueError("Preparation changed; re-evaluate before continuing")
        self.state.transition(key, "READY_FOR_REVIEW", expected_revision=record["revision"])
        return {"allowed": True, "state": "READY_FOR_REVIEW", "packet": packet}

    def submission_context(self, key):
        candidate, policy = self.candidates.load(), self.state.setting("policy")
        record = self.state.get(key)
        if record["state"] not in {"READY_FOR_REVIEW", "APPROVED"}:
            raise ValueError("Application must be ready for review")
        job, packet = record["body"]["job"], record["body"].get("packet")
        form = self.provider.inspect(job)
        gates = evaluate(candidate, job)["reasons"] + form_gates(candidate, job, form) + self._resume_gates(candidate)
        if not packet or packet["candidate_hash"] != digest(candidate) or packet["job_hash"] != digest(job) or packet["form"] != form or packet["provider"] != self.provider.adapter_id:
            gates.append("packet_changed")
        payload = {"action": "submit", "job": job, "packet": packet, "form": form,
                   "candidate_hash": digest(candidate), "policy": policy, "provider": self.provider.adapter_id}
        return {"context": digest(payload), "payload": payload, "gates": sorted(set(gates)),
                "record": record, "candidate": candidate, "policy": policy}

    def approve(self, key, reviewed_context):
        """Trusted host calls ONLY after an explicit human confirmation of the preview."""
        current = self.submission_context(key)
        if current["context"] != reviewed_context or current["gates"]:
            raise ValueError("Action changed or has a hard gate; review again")
        if current["policy"]["mode"] == "OBSERVE":
            raise ValueError("OBSERVE cannot approve external actions")
        record = current["record"]
        if record["state"] == "READY_FOR_REVIEW":
            self.state.transition(key, "APPROVED", expected_revision=record["revision"])
        self.state.grant(current["context"])

    def submit(self, key):
        current = self.submission_context(key)
        candidate, policy, record = current["candidate"], current["policy"], current["record"]
        approved = self.state.has_grant(current["context"])
        decision = permission(policy, "submit", current["gates"], approved)
        if not decision["allowed"]:
            if current["gates"]:
                self.state.transition(key, "HUMAN_REQUIRED", {"gates": current["gates"]}, record["revision"])
            return decision
        if record["state"] == "READY_FOR_REVIEW":
            record = self.state.transition(key, "APPROVED", expected_revision=record["revision"])
        self.state.reserve(key, current["context"], "submit", candidate, policy, record["revision"], approved)
        try:
            receipt = self.provider.submit(record["body"]["job"], record["body"]["packet"], current["context"])
        except Exception:
            # A timeout can happen after acceptance. Never automatically retry it.
            self.state.transition(key, "UNRESOLVED", {"receipt": {"outcome": "unknown"}})
            self.state.finish_effect(current["context"], "UNRESOLVED")
            return {"state": "UNRESOLVED", "reason": "provider_error_reconcile_before_retry"}
        if self.valid_receipt(key, receipt):
            target = "SUBMITTED"
        elif isinstance(receipt, dict) and receipt.get("outcome") == "simulated" and receipt.get("job_key") == key:
            target = "SIMULATED"
        elif isinstance(receipt, dict) and receipt.get("outcome") in {"security_challenge", "validation_failed"}:
            target = "HUMAN_REQUIRED"
        else:
            target = "UNRESOLVED"
        self.state.transition(key, target, {"receipt": receipt})
        self.state.finish_effect(current["context"], target)
        return {"state": target, "receipt": receipt}

    @staticmethod
    def valid_receipt(key, receipt):
        return (isinstance(receipt, dict) and receipt.get("outcome") == "accepted"
                and receipt.get("job_key") == key and receipt.get("accepted") is True
                and isinstance(receipt.get("receipt_id"), str) and bool(receipt["receipt_id"].strip())
                and isinstance(receipt.get("evidence"), str) and bool(receipt["evidence"].strip()))

    def reconcile(self, key, receipt):
        if not self.valid_receipt(key, receipt):
            raise ValueError("An exact-job employer acceptance receipt is required")
        record = self.state.get(key)
        if record["state"] == "SUBMITTING":
            record = self.state.transition(key, "UNRESOLVED", expected_revision=record["revision"])
        if record["state"] != "UNRESOLVED":
            raise ValueError("Only an unresolved attempt can be reconciled")
        return self.state.transition(key, "SUBMITTED", {"receipt": receipt}, record["revision"])

    def auxiliary_context(self, key, action, adapter):
        if action not in {"tracker", "notify"}:
            raise ValueError("Unsupported auxiliary action")
        record = self.state.get(key)
        job = record["body"]["job"]
        payload = {"key": key, "state": record["state"], "employer": job["employer"], "title": job["title"]}
        policy, candidate = self.state.setting("policy"), self.candidates.load()
        context = digest({"action": action, "destination": adapter.adapter_id, "payload": payload,
                          "policy": policy, "candidate": digest(candidate)})
        return context, payload, record, policy, candidate

    def auxiliary(self, key, action, adapter):
        context, payload, record, policy, candidate = self.auxiliary_context(key, action, adapter)
        if adapter.external:
            approved = self.state.has_grant(context)
            # Only a minimal status projection is transmitted, never the candidate/packet.
            decision = permission(policy, action, approved=approved)
            if not decision["allowed"]:
                return decision
            self.state.reserve(key, context, action, candidate, policy, record["revision"], approved)
        try:
            if action == "tracker":
                adapter.record(payload)
            else:
                adapter.notify(payload)
        except Exception:
            if adapter.external:
                self.state.finish_effect(context, "UNRESOLVED")
            return {"allowed": False, "reason": "adapter_error_reconcile_before_retry"}
        if adapter.external:
            self.state.finish_effect(context, "COMPLETED")
        return {"allowed": True, "external": adapter.external}
