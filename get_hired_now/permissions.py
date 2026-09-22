"""Fail-closed permission decisions, shared by every external write."""

from .models import Mode, digest, job_key, validate_policy


def question_scope(job, question):
    return digest([job_key(job), question["id"], question["text"], question.get("kind", "fact")])


def form_gates(candidate, job, form):
    if not isinstance(form, dict) or type(form.get("security_challenge")) is not bool or not isinstance(form.get("questions"), list):
        return ["unknown_form"]
    reasons = ["security_challenge"] if form["security_challenge"] else []
    if form.get("job_key") != job_key(job):
        reasons.append("form_identity_conflict")
    if form.get("complete") is not True:
        reasons.append("incomplete_form")
    ids = set()
    for q in form["questions"]:
        if not isinstance(q, dict) or not all(isinstance(q.get(k), str) and q[k].strip() for k in ("id", "text", "fact")):
            reasons.append("unknown_question")
            continue
        if q["id"] in ids or type(q.get("required")) is not bool or q.get("kind") not in {"fact", "legal", "human_only"}:
            reasons.append("unknown_question")
        ids.add(q["id"])
        if q.get("kind") == "human_only":
            reasons.append("human_only_assessment")
            continue
        fact = candidate["facts"].get(q["fact"])
        if q.get("kind") == "legal":
            if not fact or fact.get("status") != "confirmed" or fact.get("scope") != question_scope(job, q):
                reasons.append("unexpected_legal_declaration")
        elif q.get("required") and (not fact or fact.get("status") != "confirmed"):
            reasons.append("new_application_question")
    return sorted(set(reasons))


def permission(policy, action, gates=(), approved=False):
    validate_policy(policy)
    if action not in {"prepare", "submit", "tracker", "notify"}:
        raise ValueError("Unknown action")
    if gates:
        return {"allowed": False, "reason": "human_required", "gates": list(gates)}
    if policy["mode"] == Mode.OBSERVE.value:
        return {"allowed": False, "reason": "observe_only"}
    if action == "prepare":
        return {"allowed": True, "reason": "local_preparation"}
    if approved:
        return {"allowed": True, "reason": "scoped_human_approval"}
    if policy["mode"] == Mode.REVIEW.value:
        return {"allowed": False, "reason": "approval_required"}
    if action == "submit" and not policy["auto_submit"]:
        return {"allowed": False, "reason": "auto_submit_disabled"}
    if action not in policy["allowed_actions"]:
        return {"allowed": False, "reason": "action_not_authorized"}
    return {"allowed": True, "reason": "explicit_autonomous_authorization"}
