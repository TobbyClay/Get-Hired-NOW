"""Read-only batch counts from a private skill checkpoint; no external operations."""

import argparse
import json
import math
from collections import Counter
from pathlib import Path

MILESTONES = {
    "posting_screened": "screened",
    "role_qualified": "qualified",
    "role_conditional": "conditional",
    "packet_prepared": "prepared",
    "submission_ready": "ready",
    "submit_clicked": "attempted",
}


def duration(value, name):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"Invalid measured {name}")
    return value


def report(state, batch_id):
    if state.get("schema_version") != 1:
        raise ValueError("Unsupported checkpoint schema")
    batch = state.get("rounds", {}).get(batch_id)
    if not isinstance(batch, dict):
        raise ValueError("Unknown batch; do not infer its scope or timings")
    jobs = state["jobs"]
    events = [e for e in state["events"] if e.get("batch_id") == batch_id
              and e.get("job_key") in jobs and e.get("evidence")]
    milestones = {label: set() for label in MILESTONES.values()}
    sightings, source_coverage, family_coverage, latest, blockers = [], {}, {}, {}, {}
    for event in events:
        key, kind = event["job_key"], event.get("kind")
        if kind == "lead_observed":
            sightings.append(event)
        if kind in MILESTONES:
            milestones[MILESTONES[kind]].add(key)
        if kind == "posting_screened":
            for field, coverage in (("source_lane", source_coverage), ("role_family", family_coverage)):
                label = event.get(field) or "unspecified"
                coverage.setdefault(label, set()).add(key)
        if kind == "attempt_result":
            latest[key] = event
        if kind in {"role_blocked", "attempt_result"} and event.get("reason"):
            blockers[key] = event
        if kind == "blocker_resolved" or (kind == "attempt_result" and event.get("outcome") == "accepted"):
            blockers.pop(key, None)
    confirmed = {
        key for key, job in jobs.items()
        if any(isinstance(r, dict) and r.get("job_key") == key and r.get("outcome") == "accepted"
               and r.get("evidence") and r.get("confirmed_in_batch") == batch_id
               for r in job.get("receipts", []))
    }
    attempted = milestones["attempted"]
    prior_attempted = {e["job_key"] for e in state["events"]
                       if e.get("batch_id") and e["batch_id"] != batch_id
                       and e.get("kind") == "submit_clicked" and e.get("job_key") in jobs and e.get("evidence")}
    # Historical acceptance also resolves a current attempt's uncertainty, but
    # never becomes a newly observed confirmation in this batch.
    accepted = {
        key for key, job in jobs.items()
        if any(isinstance(r, dict) and r.get("job_key") == key and r.get("outcome") == "accepted"
               and r.get("evidence") for r in job.get("receipts", []))
    }
    unresolved, failed, security = set(), set(), set()
    for key in attempted - accepted:
        outcome = latest.get(key, {}).get("outcome")
        if outcome == "failed_validation":
            failed.add(key)
        elif outcome == "security_blocked":
            security.add(key)
        else:
            unresolved.add(key)
    elapsed = duration(batch.get("elapsed_seconds"), "elapsed_seconds")
    active = duration(batch.get("active_seconds"), "active_seconds")
    if elapsed is not None and active is not None and active > elapsed:
        raise ValueError("Active operator time cannot exceed wall elapsed time; worker time is separate")
    counts = {label: len(keys) for label, keys in milestones.items()}
    counts.update(raw_discoveries=len(sightings), unique_discoveries=len({e["job_key"] for e in sightings}),
                  confirmed=len(confirmed), confirmed_from_prior_attempts=len((confirmed - attempted) & prior_attempted),
                  confirmed_from_current_submits=len(confirmed & attempted),
                  confirmed_submit_cohort_unknown=len(confirmed - attempted - prior_attempted),
                  unresolved=len(unresolved), failed_validation=len(failed), security_blocked=len(security))
    return {
        "batch_id": batch_id, "counts": counts,
        "source_coverage": {k: len(v) for k, v in sorted(source_coverage.items())},
        "family_coverage": {k: len(v) for k, v in sorted(family_coverage.items())},
        "blocker_reasons": dict(sorted(Counter(e["reason"] for key, e in blockers.items()
                                               if key not in accepted).items())),
        "elapsed_seconds": elapsed, "active_seconds": active,
        "confirmations_per_elapsed_hour": round(len(confirmed) * 3600 / elapsed, 2) if elapsed else None,
        "confirmations_per_active_hour": round(len(confirmed) * 3600 / active, 2) if active else None,
        "stop_reason": batch.get("stop_reason"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--batch", required=True)
    args = parser.parse_args()
    try:
        state = json.loads((Path(args.workspace).expanduser() / "state.json").read_text(encoding="utf-8"))
        print(json.dumps(report(state, args.batch), indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"Report unavailable: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
