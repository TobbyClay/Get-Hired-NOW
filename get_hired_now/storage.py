"""SQLite is the source of truth. Transactions reserve writes before transport."""

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .models import TRANSITIONS, digest, validate_candidate, validate_policy


def private_home(path=None):
    root = Path(path or os.environ.get("GET_HIRED_NOW_HOME") or Path.home() / ".get-hired-now").expanduser().resolve()
    if any((p / ".git").exists() for p in (root, *root.parents)):
        raise ValueError("Private state must be outside every Git checkout")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


class SQLiteState:
    """One candidate per private home; separate homes isolate separate people."""

    def __init__(self, home=None):
        self.home = private_home(home)
        self.path = self.home / "workflow.sqlite3"
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in {0, 1}:
                raise ValueError("Unsupported state schema; use a compatible release")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    key TEXT PRIMARY KEY, state TEXT NOT NULL, revision INTEGER NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, at REAL NOT NULL, job_key TEXT, kind TEXT NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS grants (
                    context TEXT PRIMARY KEY, expires REAL NOT NULL, consumed INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS effects (
                    context TEXT PRIMARY KEY, action TEXT NOT NULL, status TEXT NOT NULL);
                PRAGMA user_version=1;
            """)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass  # Windows ACLs are inherited; this is not encryption.

    def _open(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @contextmanager
    def connect(self):
        db = self._open()
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        db = self._open()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _event(self, db, key, kind, body):
        db.execute("INSERT INTO events(at,job_key,kind,body) VALUES(?,?,?,?)",
                   (time.time(), key, kind, json.dumps(body, allow_nan=False)))

    def setting(self, key):
        with self.connect() as db:
            row = db.execute("SELECT body FROM settings WHERE key=?", (key,)).fetchone()
        if row is None:
            raise ValueError("Run interactive setup first")
        return json.loads(row[0])

    def configured(self):
        with self.connect() as db:
            return db.execute("SELECT 1 FROM settings WHERE key='candidate'").fetchone() is not None

    def save_settings(self, candidate, policy):
        validate_candidate(candidate)
        validate_policy(policy)
        with self.transaction() as db:
            for key, value in (("candidate", candidate), ("policy", policy)):
                db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, json.dumps(value, allow_nan=False)))
            db.execute("DELETE FROM grants")
            self._event(db, None, "settings_updated", {"candidate_hash": digest(candidate), "policy_hash": digest(policy)})

    def discover(self, key, job):
        with self.transaction() as db:
            found = db.execute("SELECT 1 FROM jobs WHERE key=?", (key,)).fetchone()
            if found:
                self._event(db, key, "duplicate_seen", {})
                return False
            db.execute("INSERT INTO jobs VALUES(?,?,?,?)", (key, "DISCOVERED", 0, json.dumps({"job": job})))
            self._event(db, key, "discovered", {})
            return True

    def get(self, key):
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE key=?", (key,)).fetchone()
        if row is None:
            raise ValueError("Unknown job key")
        return {**dict(row), "body": json.loads(row["body"])}

    def list(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT key,state,revision FROM jobs ORDER BY rowid")]

    def _transition(self, db, key, target, updates=None, expected_revision=None):
        row = db.execute("SELECT * FROM jobs WHERE key=?", (key,)).fetchone()
        if row is None or target not in TRANSITIONS.get(row["state"], set()):
            raise ValueError("Illegal workflow transition")
        if expected_revision is not None and expected_revision != row["revision"]:
            raise ValueError("State changed; reload before continuing")
        body = json.loads(row["body"])
        body.update(updates or {})
        db.execute("UPDATE jobs SET state=?,revision=revision+1,body=? WHERE key=?",
                   (target, json.dumps(body, allow_nan=False), key))
        self._event(db, key, "transition", {"from": row["state"], "to": target})

    def transition(self, key, target, updates=None, expected_revision=None):
        with self.transaction() as db:
            self._transition(db, key, target, updates, expected_revision)
        return self.get(key)

    def grant(self, context):
        with self.transaction() as db:
            db.execute("INSERT OR REPLACE INTO grants VALUES(?,?,0)", (context, time.time() + 900))
            self._event(db, None, "human_approval", {"context": context, "ttl_seconds": 900})

    def has_grant(self, context):
        with self.connect() as db:
            return db.execute("SELECT 1 FROM grants WHERE context=? AND consumed=0 AND expires>?",
                              (context, time.time())).fetchone() is not None

    def reserve(self, key, context, action, candidate, policy, revision, needs_grant):
        with self.transaction() as db:
            # Prevent settings or concurrent state changes between review and transport.
            for name, expected in (("candidate", candidate), ("policy", policy)):
                value = json.loads(db.execute("SELECT body FROM settings WHERE key=?", (name,)).fetchone()[0])
                if digest(value) != digest(expected):
                    raise ValueError("Settings changed; review the action again")
            row = db.execute("SELECT revision FROM jobs WHERE key=?", (key,)).fetchone()
            if row is None or row[0] != revision:
                raise ValueError("State changed; review the action again")
            if needs_grant:
                changed = db.execute("UPDATE grants SET consumed=1 WHERE context=? AND consumed=0 AND expires>?",
                                     (context, time.time())).rowcount
                if changed != 1:
                    raise ValueError("A fresh scoped human approval is required")
            try:
                db.execute("INSERT INTO effects VALUES(?,?,?)", (context, action, "ATTEMPTING"))
            except sqlite3.IntegrityError:
                raise ValueError("This exact action was already attempted; reconcile instead of retrying") from None
            if action == "submit":
                self._transition(db, key, "SUBMITTING", {"attempt_context": context}, revision)
            self._event(db, key, "action_reserved", {"action": action, "context": context})

    def finish_effect(self, context, status):
        with self.transaction() as db:
            db.execute("UPDATE effects SET status=? WHERE context=?", (status, context))

    def events(self, key):
        with self.connect() as db:
            return [{**dict(r), "body": json.loads(r["body"])} for r in db.execute(
                "SELECT * FROM events WHERE job_key=? ORDER BY id", (key,))]
