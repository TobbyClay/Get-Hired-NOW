"""Optional atomic checkpoint helper for the skill; never performs external actions."""

import argparse
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

STAGES = {"DISCOVERED", "EVALUATED", "HUMAN_REQUIRED", "REJECTED", "RESEARCHED", "TAILORED",
          "READY_FOR_REVIEW", "APPROVED", "SUBMITTING", "SUBMITTED", "UNRESOLVED", "FOLLOW_UP"}


def workspace(path):
    root = Path(path).expanduser().resolve()
    if any((p / ".git").exists() or (p / "SKILL.md").exists() for p in (root, *root.parents)):
        raise ValueError("Candidate state must be outside Git checkouts and installed skills")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


@contextmanager
def lock(root):
    path = root / ".checkpoint.lock"
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError("Another writer or interrupted checkpoint owns the lock; inspect before recovery") from None
    try:
        os.write(handle, str(os.getpid()).encode())
        os.close(handle)
        yield
    finally:
        path.unlink(missing_ok=True)


def validate(value, previous=None):
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("Unsupported checkpoint schema")
    if type(value.get("revision")) is not int or value["revision"] < 0:
        raise ValueError("Checkpoint revision must be a nonnegative integer")
    for key, kind in (("permissions", dict), ("integrations", dict), ("jobs", dict),
                      ("events", list), ("next_actions", list)):
        if not isinstance(value.get(key), kind):
            raise ValueError(f"Invalid {key}")
    if "candidate" not in value or (value["candidate"] is not None and not isinstance(value["candidate"], dict)):
        raise ValueError("Candidate must be null or an explicitly supplied profile")
    policy = value["permissions"]
    if policy.get("mode") not in {"OBSERVE", "REVIEW", "AUTONOMOUS"} or type(policy.get("auto_submit")) is not bool:
        raise ValueError("Invalid permission mode or auto_submit type")
    if policy["auto_submit"] and policy["mode"] != "AUTONOMOUS":
        raise ValueError("Automatic submission requires AUTONOMOUS mode")
    if not isinstance(policy.get("grants"), list) or not isinstance(policy.get("approvals"), list):
        raise ValueError("Grants and approvals must be explicit lists")
    for key, job in value["jobs"].items():
        if not isinstance(job, dict) or job.get("stage") not in STAGES:
            raise ValueError("Invalid job stage")
        if job["stage"] in {"SUBMITTING", "UNRESOLVED"} and not job.get("attempts"):
            raise ValueError("An attempted application needs a durable attempt record")
        if job["stage"] in {"SUBMITTED", "FOLLOW_UP"}:
            receipts = job.get("receipts", [])
            if not any(isinstance(r, dict) and r.get("job_key") == key and r.get("outcome") == "accepted"
                       and r.get("evidence") for r in receipts):
                raise ValueError("Confirmed submission requires exact-job acceptance evidence")
    if previous:
        if value["events"][:len(previous["events"])] != previous["events"]:
            raise ValueError("Existing audit events must be preserved")
        for key, job in previous["jobs"].items():
            replacement = value["jobs"].get(key)
            if replacement is None:
                raise ValueError("Existing jobs must be retained")
            for receipt in job.get("receipts", []):
                if receipt not in replacement.get("receipts", []):
                    raise ValueError("Existing receipts must be preserved")
            if job["stage"] in {"SUBMITTED", "FOLLOW_UP"} and replacement["stage"] not in {"SUBMITTED", "FOLLOW_UP"}:
                raise ValueError("Confirmed applications cannot be reopened")
            if job["stage"] in {"SUBMITTING", "UNRESOLVED"} and replacement["stage"] not in {
                "SUBMITTING", "UNRESOLVED", "SUBMITTED", "HUMAN_REQUIRED"
            }:
                raise ValueError("Resolve the existing attempt before further preparation")
            if job["stage"] in {"SUBMITTING", "UNRESOLVED"} and replacement["stage"] == "HUMAN_REQUIRED" and not replacement.get("resolution_evidence"):
                raise ValueError("Resolving an attempt requires actual outcome evidence")
    json.dumps(value, allow_nan=False)


def atomic_write(path, value):
    descriptor, temporary = tempfile.mkstemp(prefix=".checkpoint-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as out:
            json.dump(value, out, indent=2, ensure_ascii=False, allow_nan=False)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def save(root, proposal, expected):
    root = workspace(root)
    with lock(root):
        path = root / "state.json"
        previous = json.loads(path.read_text(encoding="utf-8"))
        if previous["revision"] != expected or proposal["revision"] != expected:
            raise ValueError("Revision changed; reload and merge before saving")
        validate(proposal, previous)
        proposal = dict(proposal, revision=expected + 1, updated_at=datetime.now(timezone.utc).isoformat())
        atomic_write(path, proposal)
    return proposal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "show", "save"])
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--input")
    parser.add_argument("--expected-revision", type=int)
    args = parser.parse_args()
    try:
        root = workspace(args.workspace)
        path = root / "state.json"
        if args.command == "init":
            with lock(root):
                if path.exists():
                    raise ValueError("Existing checkpoint preserved; use show to resume")
                value = json.loads((Path(__file__).resolve().parents[1] / "assets" / "state.example.json").read_text())
                validate(value)
                atomic_write(path, value)
        elif args.command == "save":
            if args.input is None or args.expected_revision is None:
                raise ValueError("Save requires --input and --expected-revision")
            proposal = json.loads(Path(args.input).read_text(encoding="utf-8"))
            save(root, proposal, args.expected_revision)
        if args.command == "show":
            print(path.read_text(encoding="utf-8"))
        else:
            print(json.dumps({"saved": True, "revision": json.loads(path.read_text())["revision"]}))
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(f"Checkpoint blocked: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
