"""Replaceable interfaces. Bundled implementations make no network requests."""

import csv
import json
from pathlib import Path
from typing import Iterable, Protocol

from .models import job_key


class JobSource(Protocol):
    def discover(self, search: dict) -> Iterable[dict]: ...


class CandidateStore(Protocol):
    def load(self) -> dict: ...
    def save(self, candidate: dict) -> None: ...


class ApplicationProvider(Protocol):
    # Include the destination/account identity, not a credential, in adapter_id.
    adapter_id: str
    def inspect(self, job: dict) -> dict: ...  # Read-only; receives no candidate.
    def submit(self, job: dict, packet: dict, idempotency_key: str) -> dict: ...


class ApplicationTracker(Protocol):
    adapter_id: str
    external: bool
    def record(self, row: dict) -> None: ...


class NotificationProvider(Protocol):
    adapter_id: str
    external: bool
    def notify(self, message: dict) -> None: ...


class ResumeRenderer(Protocol):
    def render(self, grounded_packet: dict, destination: Path) -> Path: ...


class FileJobSource:
    def __init__(self, path):
        self.path = Path(path)

    def discover(self, search):
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(value, list):
            raise ValueError("The source file must contain a JSON list of jobs")
        roles = search.get("target_roles", [])
        return [job for job in value if not roles or any(role.casefold() in job["title"].casefold() for role in roles)]


class LocalCandidateStore:
    def __init__(self, state):
        self.state = state

    def load(self):
        return self.state.setting("candidate")

    def save(self, candidate):
        self.state.save_settings(candidate, self.state.setting("policy"))


class DryRunApplicationProvider:
    adapter_id = "dry-run:v1"

    def inspect(self, job):
        return {"job_key": job_key(job), "complete": True, "security_challenge": False,
                "questions": job.get("questions", [])}

    def submit(self, job, packet, idempotency_key):
        return {"outcome": "simulated", "job_key": job_key(job), "idempotency_key": idempotency_key,
                "evidence": "Local simulation only; no application was sent."}


class CSVTracker:
    external = False

    def __init__(self, home):
        self.path = Path(home) / "tracker.csv"
        self.adapter_id = "local-csv:" + str(self.path.resolve())

    def record(self, row):
        def cell(value):
            text = str(value)
            return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text
        fields = ["key", "state", "employer", "title"]
        exists = self.path.exists()
        with self.path.open("a", encoding="utf-8", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=fields)
            if not exists:
                writer.writeheader()
            writer.writerow({k: cell(row[k]) for k in fields})


class ConsoleNotification:
    adapter_id = "local-console:v1"
    external = False

    def notify(self, message):
        print(json.dumps(message, indent=2))
