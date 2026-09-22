"""Versioned, JSON-compatible contracts and deterministic identities."""

import hashlib
import json
import math
from enum import Enum
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class State(str, Enum):
    DISCOVERED = "DISCOVERED"
    EVALUATED = "EVALUATED"
    REJECTED = "REJECTED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    RESEARCHED = "RESEARCHED"
    TAILORED = "TAILORED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    UNRESOLVED = "UNRESOLVED"
    SIMULATED = "SIMULATED"
    FOLLOW_UP = "FOLLOW_UP"


class Mode(str, Enum):
    OBSERVE = "OBSERVE"
    REVIEW = "REVIEW"
    AUTONOMOUS = "AUTONOMOUS"


TRANSITIONS = {
    "DISCOVERED": {"EVALUATED"},
    "EVALUATED": {"EVALUATED", "REJECTED", "HUMAN_REQUIRED", "RESEARCHED"},
    "REJECTED": {"EVALUATED"},
    "HUMAN_REQUIRED": {"EVALUATED"},
    "RESEARCHED": {"TAILORED", "EVALUATED", "HUMAN_REQUIRED"},
    "TAILORED": {"READY_FOR_REVIEW", "EVALUATED"},
    "READY_FOR_REVIEW": {"APPROVED", "EVALUATED", "HUMAN_REQUIRED"},
    "APPROVED": {"SUBMITTING", "EVALUATED", "HUMAN_REQUIRED"},
    "SUBMITTING": {"SUBMITTED", "UNRESOLVED", "SIMULATED", "HUMAN_REQUIRED"},
    "UNRESOLVED": {"SUBMITTED"},
    "SIMULATED": {"EVALUATED"},
    "SUBMITTED": {"FOLLOW_UP"},
    "FOLLOW_UP": set(),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def canonical_url(url):
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("A public HTTP(S) job URL without credentials is required")
    # Retain requisition/query parameters; remove only known marketing parameters.
    query = sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                   if not k.lower().startswith("utm_") and k.lower() not in {"gclid", "fbclid"})
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"),
                       urlencode(query), ""))


def job_key(job):
    employer = job["employer"].strip().casefold()
    identity = ("requisition", employer, job["requisition_id"].strip().casefold()) if job.get("requisition_id") else (
        "url", employer, canonical_url(job["url"]))
    return digest(identity)


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")


def validate_salary(salary, amount):
    if not isinstance(salary, dict):
        raise ValueError("Salary must include amount, currency, period and basis")
    number = salary.get(amount)
    if type(number) not in {int, float} or not math.isfinite(number) or number < 0:
        raise ValueError("Salary amount must be a finite nonnegative number")
    _text(salary.get("currency"), "Salary currency")
    if salary.get("period") not in {"year", "month", "hour"}:
        raise ValueError("Salary period must be year, month or hour")
    if salary.get("basis") not in {"gross_base", "net_base", "total"}:
        raise ValueError("Salary basis must be gross_base, net_base or total")


def validate_candidate(candidate):
    if candidate.get("schema_version") != 1:
        raise ValueError("Unsupported candidate schema version")
    for key in ("display_name", "location"):
        _text(candidate.get(key), key)
    for key in ("target_roles", "constraints"):
        if not isinstance(candidate.get(key), list) or any(not isinstance(x, str) or not x.strip() for x in candidate[key]):
            raise ValueError(f"{key} must be a list of text")
    if not candidate["target_roles"]:
        raise ValueError("At least one target role is required")
    validate_salary(candidate.get("salary"), "minimum")
    if not isinstance(candidate.get("facts"), dict):
        raise ValueError("Candidate facts must be an object")
    for key, fact in candidate["facts"].items():
        _text(key, "Fact key")
        if not isinstance(fact, dict) or fact.get("status") not in {"confirmed", "unverified", "conflicted"}:
            raise ValueError("Every fact needs an explicit evidence status")
        if fact["status"] == "confirmed":
            _text(fact.get("source"), "Fact source")
            if fact.get("value") is None:
                raise ValueError("Confirmed facts cannot be null")


def validate_job(job):
    if job.get("schema_version") != 1:
        raise ValueError("Unsupported job schema version")
    for key in ("employer", "title", "url", "observed_at"):
        _text(job.get(key), key)
    canonical_url(job["url"])
    if job.get("requisition_id") is not None:
        _text(job["requisition_id"], "requisition_id")
    if not isinstance(job.get("locations"), list) or any(not isinstance(x, str) for x in job["locations"]):
        raise ValueError("locations must be a list; an empty list means unknown")
    if job.get("salary") is not None:
        validate_salary(job["salary"], "maximum")
    if not isinstance(job.get("requirements"), list):
        raise ValueError("requirements must be an explicit list")
    for req in job["requirements"]:
        for key in ("fact", "quote", "source"):
            _text(req.get(key), key)
        if req.get("kind") not in {"required", "preferred", "unclear"}:
            raise ValueError("Unknown requirement kind")
        if req.get("op") not in {"eq", "gte", "contains"} or "value" not in req:
            raise ValueError("Unsupported requirement comparison")


def validate_policy(policy):
    if policy.get("schema_version") != 1:
        raise ValueError("Unsupported policy schema version")
    Mode(policy.get("mode"))
    if type(policy.get("auto_submit")) is not bool:
        raise ValueError("auto_submit must be a boolean")
    actions = policy.get("allowed_actions")
    if not isinstance(actions, list) or any(a not in {"submit", "tracker", "notify"} for a in actions):
        raise ValueError("Unknown external action")
    if policy["mode"] != "AUTONOMOUS" and policy["auto_submit"]:
        raise ValueError("auto_submit is available only in AUTONOMOUS mode")


DEFAULT_POLICY = {"schema_version": 1, "mode": "REVIEW", "auto_submit": False,
                  "allowed_actions": []}
