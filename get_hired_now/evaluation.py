"""Evidence comparisons; unknown facts never become negative or positive claims."""

from .models import validate_candidate, validate_job


def compare(actual, op, required):
    if op == "eq":
        return type(actual) is type(required) and actual == required
    if op == "gte":
        return type(actual) in {int, float} and type(required) in {int, float} and actual >= required
    if op == "contains":
        return isinstance(actual, list) and required in actual
    raise ValueError("Unsupported comparison")


def evaluate(candidate, job, duplicate=False):
    validate_candidate(candidate)
    validate_job(job)
    if duplicate:
        return {"decision": "DUPLICATE", "reasons": ["duplicate_job"], "claims": {}, "evidence": []}
    reasons, claims, evidence = [], {}, []
    rejected = False
    if not any(role.casefold() in job["title"].casefold() for role in candidate["target_roles"]):
        reasons.append("target_role_conflict")
    # A contradiction anywhere in the fact store needs a candidate correction.
    if any(f["status"] == "conflicted" for f in candidate["facts"].values()):
        reasons.append("conflicting_candidate_fact")
    for req in job["requirements"]:
        fact = candidate["facts"].get(req["fact"])
        known = fact is not None and fact["status"] == "confirmed"
        supported = known and compare(fact["value"], req["op"], req["value"])
        assessment = "supported" if supported else ("contradicted" if known else "unknown")
        evidence.append({"fact": req["fact"], "quote": req["quote"], "source": req["source"],
                         "kind": req["kind"], "assessment": assessment,
                         "candidate_source": fact.get("source") if known else None})
        if supported:
            claims[req["fact"]] = fact["value"]
        if req["kind"] == "preferred":
            continue
        if req["kind"] == "unclear":
            reasons.append("unclear_requirement")
        elif not known:
            reasons.append("unverified_skill" if fact else "missing_candidate_fact")
        elif not supported:
            rejected = True
            reasons.append("missing_hard_requirement")
    if not job["locations"]:
        reasons.append("unknown_location_eligibility")
    elif "*" not in job["locations"] and candidate["location"] not in job["locations"]:
        reasons.append("location_conflict")
    pay = job.get("salary")
    if pay is None:
        reasons.append("unknown_salary")
    elif any(pay[k] != candidate["salary"][k] for k in ("currency", "period", "basis")):
        reasons.append("salary_basis_conflict")
    elif pay["maximum"] < candidate["salary"]["minimum"]:
        reasons.append("salary_too_low")
    # Free-text constraints cannot safely be declared satisfied by string matching.
    # A person supplies exact-job constraint acknowledgements after reviewing them.
    from .models import digest, job_key
    for constraint in candidate["constraints"]:
        fact = candidate["facts"].get("constraint:" + digest([job_key(job), digest(job), constraint]))
        if not fact or fact["status"] != "confirmed" or fact.get("value") is not True:
            reasons.append("material_constraint_review")
    return {"decision": "REJECT" if rejected else ("HUMAN_REQUIRED" if reasons else "MATCH"),
            "reasons": sorted(set(reasons)), "claims": claims, "evidence": evidence}
