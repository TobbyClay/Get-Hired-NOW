import copy
import hashlib
import json
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from get_hired_now.adapters import DryRunApplicationProvider, FileJobSource
from get_hired_now.engine import Workflow
from get_hired_now.evaluation import evaluate
from get_hired_now.models import DEFAULT_POLICY, digest, job_key, validate_policy
from get_hired_now.onboarding import setup
from get_hired_now.permissions import form_gates, permission, question_scope
from get_hired_now.storage import SQLiteState, private_home
from tools.privacy_scan import scan, scan_text

ROOT = Path(__file__).resolve().parents[1]


def fictional():
    return json.loads((ROOT / "examples" / "fictional-candidate.json").read_text()), json.loads(
        (ROOT / "examples" / "jobs.json").read_text())[0]


class RecordingProvider(DryRunApplicationProvider):
    adapter_id = "test-provider:v1"

    def __init__(self):
        self.calls = 0
        self.challenge = False
        self.extra = []
        self.outcome = "accepted"

    def inspect(self, job):
        form = super().inspect(job)
        form["security_challenge"] = self.challenge
        form["questions"] = copy.deepcopy(form["questions"]) + self.extra
        return form

    def submit(self, job, packet, idempotency_key):
        self.calls += 1
        if self.outcome == "timeout":
            raise TimeoutError("transport uncertain")
        return {"outcome": self.outcome, "job_key": job_key(job), "accepted": True,
                "receipt_id": "fictional-receipt", "evidence": "Synthetic exact-job receipt"}


class EvaluationFixtures(unittest.TestCase):
    def test_all_ten_regression_cases(self):
        cases = sorted((ROOT / "tests" / "cases").glob("*/input.json"))
        self.assertEqual(len(cases), 10)
        for path in cases:
            with self.subTest(case=path.parent.name):
                data = json.loads(path.read_text())
                expected = json.loads((path.parent / "expected.json").read_text())
                result = evaluate(data["candidate"], data["job"], data.get("duplicate", False))
                gates = result["reasons"] + form_gates(data["candidate"], data["job"], data["form"])
                allowed = permission(data["policy"], "submit", gates)
                self.assertEqual(result["decision"], expected["decision"])
                self.assertEqual(allowed["allowed"], expected["submit_allowed"])
                for reason in expected["reasons"]:
                    self.assertIn(reason, gates + [allowed["reason"]])
                for fact in expected.get("must_not_claim", []):
                    self.assertNotIn(fact, result["claims"])


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = SQLiteState(self.tmp.name)
        self.candidate, self.job = fictional()
        resume = self.state.home / "original.txt"
        resume.write_text("Fictional resume supplied by test user.")
        self.candidate["resume"] = {"path": str(resume), "sha256": hashlib.sha256(resume.read_bytes()).hexdigest()}
        self.policy = copy.deepcopy(DEFAULT_POLICY)
        self.state.save_settings(self.candidate, self.policy)
        self.provider = RecordingProvider()
        self.flow = Workflow(self.state, self.provider)
        self.key = job_key(self.job)
        self.state.discover(self.key, self.job)

    def ready(self):
        self.assertEqual(self.flow.evaluate(self.key)["decision"], "MATCH")
        self.assertTrue(self.flow.prepare(self.key)["allowed"])

    def approve(self):
        self.flow.approve(self.key, self.flow.submission_context(self.key)["context"])

    def autonomous(self, enabled=True):
        self.policy = {"schema_version": 1, "mode": "AUTONOMOUS", "auto_submit": enabled,
                       "allowed_actions": ["submit"]}
        self.state.save_settings(self.candidate, self.policy)

    def test_review_requires_exact_approval_and_receipt(self):
        self.ready()
        self.assertFalse(self.flow.submit(self.key)["allowed"])
        self.assertEqual(self.provider.calls, 0)
        self.approve()
        self.assertEqual(self.flow.submit(self.key)["state"], "SUBMITTED")
        self.assertEqual(self.provider.calls, 1)
        with self.assertRaises(ValueError):
            self.flow.submit(self.key)
        self.assertEqual(self.provider.calls, 1)

    def test_autonomous_needs_two_distinct_switches(self):
        self.autonomous(False)
        self.ready()
        self.assertEqual(self.flow.submit(self.key)["reason"], "auto_submit_disabled")
        self.assertEqual(self.provider.calls, 0)
        self.autonomous(True)
        self.assertEqual(self.flow.submit(self.key)["state"], "SUBMITTED")

    def test_autonomous_requires_action_allowlist(self):
        self.autonomous()
        self.policy["allowed_actions"] = []
        self.state.save_settings(self.candidate, self.policy)
        self.ready()
        self.assertEqual(self.flow.submit(self.key)["reason"], "action_not_authorized")

    def test_observe_never_prepares_or_approves(self):
        self.policy["mode"] = "OBSERVE"
        self.state.save_settings(self.candidate, self.policy)
        self.flow.evaluate(self.key)
        self.assertEqual(self.flow.prepare(self.key)["reason"], "observe_only")
        self.assertEqual(self.provider.calls, 0)

    def test_challenge_after_approval_blocks_transport(self):
        self.ready()
        self.approve()
        self.provider.challenge = True
        self.assertIn("security_challenge", self.flow.submit(self.key)["gates"])
        self.assertEqual(self.provider.calls, 0)

    def test_new_question_after_approval_blocks_transport(self):
        self.ready()
        self.approve()
        self.provider.extra = [{"id": "q-new", "text": "Supply a new fact", "fact": "new_fact",
                                "required": True, "kind": "fact"}]
        self.assertIn("new_application_question", self.flow.submit(self.key)["gates"])
        self.assertEqual(self.provider.calls, 0)

    def test_legal_answer_is_bound_to_exact_question_and_job(self):
        q = {"id": "q-legal", "text": "Fictional declaration A", "fact": "legal_answer", "required": True, "kind": "legal"}
        form = self.provider.inspect(self.job)
        form["questions"].append(q)
        self.assertIn("unexpected_legal_declaration", form_gates(self.candidate, self.job, form))
        self.candidate["facts"]["legal_answer"] = {"value": True, "status": "confirmed", "source": "user:question",
                                                  "scope": question_scope(self.job, q)}
        self.assertEqual(form_gates(self.candidate, self.job, form), [])
        q["text"] = "Fictional declaration B"
        self.assertIn("unexpected_legal_declaration", form_gates(self.candidate, self.job, form))

    def test_candidate_change_revokes_approval_and_packet(self):
        self.ready()
        self.approve()
        self.candidate["location"] = "FICTIONAL-OTHER"
        self.state.save_settings(self.candidate, self.policy)
        result = self.flow.submit(self.key)
        self.assertIn("packet_changed", result["gates"])
        self.assertIn("location_conflict", result["gates"])
        self.assertEqual(self.provider.calls, 0)

    def test_resume_content_change_blocks_submit(self):
        self.ready()
        self.approve()
        Path(self.candidate["resume"]["path"]).write_text("Changed fictional resume")
        self.assertIn("resume_changed", self.flow.submit(self.key)["gates"])
        self.assertEqual(self.provider.calls, 0)

    def test_provider_change_requires_new_packet(self):
        self.ready()
        self.approve()
        self.provider.adapter_id = "other-destination"
        self.assertIn("packet_changed", self.flow.submit(self.key)["gates"])

    def test_approval_expiry(self):
        self.ready()
        self.approve()
        with self.state.transaction() as db:
            db.execute("UPDATE grants SET expires=0")
        self.assertEqual(self.flow.submit(self.key)["reason"], "approval_required")
        self.assertEqual(self.provider.calls, 0)

    def test_transport_timeout_is_never_retried(self):
        self.autonomous()
        self.ready()
        self.provider.outcome = "timeout"
        self.assertEqual(self.flow.submit(self.key)["state"], "UNRESOLVED")
        restarted = Workflow(SQLiteState(self.tmp.name), self.provider)
        with self.assertRaises(ValueError):
            restarted.submit(self.key)
        self.assertEqual(self.provider.calls, 1)
        receipt = {"outcome": "accepted", "accepted": True, "job_key": self.key,
                   "receipt_id": "fixture-receipt", "evidence": "Observed fictional acceptance"}
        self.assertEqual(restarted.reconcile(self.key, receipt)["state"], "SUBMITTED")

    def test_false_acceptance_cannot_become_submitted(self):
        self.assertFalse(self.flow.valid_receipt(self.key, {"outcome": "accepted"}))
        self.assertFalse(self.flow.valid_receipt(self.key, {"outcome": "accepted", "accepted": True,
            "job_key": "another-job", "receipt_id": "receipt", "evidence": "fake"}))

    def test_dry_run_is_never_a_submission(self):
        self.flow = Workflow(self.state, DryRunApplicationProvider())
        self.autonomous()
        self.ready()
        self.assertEqual(self.flow.submit(self.key)["state"], "SIMULATED")

    def test_duplicate_discovery_survives_restart(self):
        restarted = SQLiteState(self.tmp.name)
        self.assertFalse(restarted.discover(self.key, self.job))
        self.assertEqual(len(restarted.list()), 1)
        self.assertEqual(restarted.events(self.key)[-1]["kind"], "duplicate_seen")

    def test_exact_requisition_distinguishes_roles_and_mirrors(self):
        mirror = copy.deepcopy(self.job)
        mirror["url"] = "https://mirror.example.com/another-path"
        self.assertEqual(job_key(mirror), self.key)
        mirror["requisition_id"] = "FICTIONAL-OTHER"
        self.assertNotEqual(job_key(mirror), self.key)
        no_id = {**self.job, "requisition_id": None, "url": "https://jobs.example.com/apply?job=one&utm_source=sample"}
        self.assertEqual(job_key(no_id), job_key({**no_id, "url": "https://jobs.example.com/apply?job=one"}))
        self.assertNotEqual(job_key(no_id), job_key({**no_id, "url": "https://jobs.example.com/apply?job=two"}))

    def test_illegal_transition_and_concurrent_revision_are_rejected(self):
        with self.assertRaises(ValueError):
            self.state.transition(self.key, "SUBMITTED")
        self.state.transition(self.key, "EVALUATED", expected_revision=0)
        with self.assertRaises(ValueError):
            self.state.transition(self.key, "RESEARCHED", expected_revision=0)

    def test_two_workers_cannot_reserve_same_submission(self):
        self.autonomous()
        self.ready()
        ctx = self.flow.submission_context(self.key)
        row = self.state.transition(self.key, "APPROVED")
        self.state.reserve(self.key, ctx["context"], "submit", self.candidate, self.policy, row["revision"], False)
        with self.assertRaises(ValueError):
            SQLiteState(self.tmp.name).reserve(self.key, ctx["context"], "submit", self.candidate, self.policy, row["revision"], False)
        self.assertEqual(self.state.get(self.key)["state"], "SUBMITTING")

    def test_settings_change_between_check_and_reservation_is_rejected(self):
        self.autonomous()
        self.ready()
        ctx = self.flow.submission_context(self.key)
        row = self.state.transition(self.key, "APPROVED")
        changed = {**self.policy, "mode": "OBSERVE", "auto_submit": False}
        self.state.save_settings(self.candidate, changed)
        with self.assertRaises(ValueError):
            self.state.reserve(self.key, ctx["context"], "submit", self.candidate, self.policy, row["revision"], False)

    def test_external_notifications_and_trackers_obey_permissions(self):
        class External:
            external = True
            adapter_id = "test-external-destination"
            calls = 0
            def record(self, row):
                self.calls += 1
            def notify(self, row):
                self.calls += 1
        adapter = External()
        for action in ("notify", "tracker"):
            self.assertFalse(self.flow.auxiliary(self.key, action, adapter)["allowed"])
        self.assertEqual(adapter.calls, 0)
        self.policy = {"schema_version": 1, "mode": "AUTONOMOUS", "auto_submit": False, "allowed_actions": ["notify"]}
        self.state.save_settings(self.candidate, self.policy)
        self.assertTrue(self.flow.auxiliary(self.key, "notify", adapter)["allowed"])
        with self.assertRaises(ValueError):
            self.flow.auxiliary(self.key, "notify", adapter)
        self.assertEqual(adapter.calls, 1)

    def test_unknown_pay_and_material_constraints_are_not_guessed(self):
        self.job["salary"] = None
        self.assertIn("unknown_salary", evaluate(self.candidate, self.job)["reasons"])
        self.candidate["constraints"] = ["Fictional schedule constraint"]
        self.assertIn("material_constraint_review", evaluate(self.candidate, self.job)["reasons"])

    def test_changed_posting_invalidates_constraint_acknowledgement(self):
        constraint = "Fictional schedule constraint"
        self.candidate["constraints"] = [constraint]
        fact_key = "constraint:" + digest([self.key, digest(self.job), constraint])
        self.candidate["facts"][fact_key] = {"value": True, "status": "confirmed", "source": "user:exact-job"}
        self.assertEqual(evaluate(self.candidate, self.job)["decision"], "MATCH")
        self.job["observed_at"] = "2026-01-02T00:00:00Z"
        self.assertIn("material_constraint_review", evaluate(self.candidate, self.job)["reasons"])

    def test_refresh_cannot_reopen_submitted_application(self):
        self.autonomous()
        self.ready()
        self.flow.submit(self.key)
        with self.assertRaises(ValueError):
            self.flow.refresh(self.key, self.job)

    def test_refresh_invalidates_prepared_packet(self):
        self.ready()
        changed = copy.deepcopy(self.job)
        changed["salary"]["maximum"] = 50
        self.assertEqual(self.flow.refresh(self.key, changed)["decision"], "HUMAN_REQUIRED")
        self.assertIsNone(self.state.get(self.key)["body"]["packet"])

    def test_missing_required_fact_is_unknown_not_false(self):
        del self.candidate["facts"]["sample_tool_years"]
        result = evaluate(self.candidate, self.job)
        self.assertEqual(result["decision"], "HUMAN_REQUIRED")
        self.assertEqual(result["evidence"][0]["assessment"], "unknown")

    def test_incomplete_or_wrong_identity_form_fails_closed(self):
        form = self.provider.inspect(self.job)
        form["complete"] = False
        self.assertIn("incomplete_form", form_gates(self.candidate, self.job, form))
        form["job_key"] = "other-job"
        self.assertIn("form_identity_conflict", form_gates(self.candidate, self.job, form))
        self.assertIn("unknown_form", form_gates(self.candidate, self.job, {}))

    def test_human_only_assessment_is_never_answered_by_a_fact(self):
        form = self.provider.inspect(self.job)
        form["questions"][0]["kind"] = "human_only"
        self.assertIn("human_only_assessment", form_gates(self.candidate, self.job, form))

    def test_crashed_reserved_attempt_cannot_be_resubmitted(self):
        self.autonomous()
        self.ready()
        ctx = self.flow.submission_context(self.key)
        row = self.state.transition(self.key, "APPROVED")
        self.state.reserve(self.key, ctx["context"], "submit", self.candidate, self.policy, row["revision"], False)
        restarted = Workflow(SQLiteState(self.tmp.name), self.provider)
        with self.assertRaises(ValueError):
            restarted.submit(self.key)
        self.assertEqual(self.provider.calls, 0)

    def test_security_block_during_transport_is_not_acceptance(self):
        self.autonomous()
        self.ready()
        self.provider.outcome = "security_challenge"
        self.assertEqual(self.flow.submit(self.key)["state"], "HUMAN_REQUIRED")
        self.assertEqual(self.provider.calls, 1)

    def test_preferred_skill_gap_is_not_mandatory(self):
        self.job["requirements"].append({"fact": "unknown_preference", "op": "eq", "value": True,
            "kind": "preferred", "quote": "Fictional preferred skill", "source": "https://jobs.example.com/fictional"})
        result = evaluate(self.candidate, self.job)
        self.assertEqual(result["decision"], "MATCH")
        self.assertNotIn("unknown_preference", result["claims"])

    def test_string_boolean_does_not_enable_autosubmit(self):
        with self.assertRaises(ValueError):
            validate_policy({**self.policy, "auto_submit": "false"})


class OnboardingAndPrivacyTests(unittest.TestCase):
    def test_private_home_refuses_git_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".git").mkdir()
            with self.assertRaises(ValueError):
                private_home(Path(tmp) / "private")

    def test_onboarding_only_persists_after_confirmation(self):
        for confirmation in ("CANCEL", "SAVE"):
            with self.subTest(confirmation=confirmation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "provided.txt"
                source.write_text("FICTIONAL ORIGINAL RESUME")
                state = SQLiteState(root / "private-home")
                responses = iter(["Fictional Example", "candidate@example.com", "FICTIONAL-REGION",
                    "Example Engineer", "100", "TOK", "year", "gross_base", "", "", "", "", "", "", "",
                    str(source), "REVIEW", confirmation])
                saved = setup(state, ask=lambda prompt: next(responses), tell=lambda text: None)
                self.assertEqual(saved, confirmation == "SAVE")
                self.assertEqual(state.configured(), saved)
                if saved:
                    candidate = state.setting("candidate")
                    self.assertEqual(candidate["display_name"], "Fictional Example")
                    self.assertEqual(Path(candidate["resume"]["path"]).read_text(), source.read_text())
                    self.assertNotIn("work_history", candidate["facts"])
                    self.assertFalse(state.setting("policy")["auto_submit"])
                else:
                    self.assertEqual(list(state.home.glob("original-*")), [])

    def test_scanner_detects_untracked_private_data_and_never_echoes_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "accidental.txt").write_text("private-marker-for-test")
            findings, count = scan(tmp, ["private-marker-for-test"])
            self.assertEqual(count, 1)
            self.assertEqual(findings, [("accidental.txt", "private_denylist_match")])

    def test_scanner_detects_tokens_without_committing_one(self):
        token = "gh" + "p_" + "x" * 36
        self.assertIn(("fixture", "github_token"), scan_text("fixture", token.encode(), []))

    def test_history_scan_catches_a_deleted_private_literal(self):
        with tempfile.TemporaryDirectory() as tmp:
            def git(*args):
                return subprocess.run(["git", "-C", tmp, "-c", "user.name=Example Contributors",
                    "-c", "user.email=contributors@example.invalid", "-c", "commit.gpgsign=false", *args],
                    capture_output=True, check=True)
            git("init")
            path = Path(tmp) / "example.txt"
            path.write_text("private-history-marker")
            git("add", ".")
            git("commit", "-m", "Synthetic history fixture")
            path.write_text("Sanitized current content")
            git("add", ".")
            git("commit", "-m", "Remove synthetic private marker")
            findings, _ = scan(tmp, ["private-history-marker"], history=True)
            self.assertIn(("history:example.txt", "private_denylist_match"), findings)


if __name__ == "__main__":
    unittest.main()
