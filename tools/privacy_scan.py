"""Scan the complete text tree and reachable Git history before publishing.

Optional --denylist is a private, external UTF-8 file with one literal per line.
Findings report paths and rule names, never matched secret values.
This is a conservative release guard, not a universal PII classifier.
"""

import argparse
import re
import subprocess
from pathlib import Path


RULES = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "cloud_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "api_secret": re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    "credential_url": re.compile(r"https?://[^\s/:]+:[^\s/@]+@"),
    "user_home_path": re.compile(r"(?:[A-Z]:[\\/]Users[\\/][^\s/\\]+|/Us" r"ers/[^\s/]+|/ho" r"me/(?!runner\b)[^\s/]+)", re.I),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@(?!(?:example\.(?:com|org|net)|[^\s@]+\.invalid)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "secret_assignment": re.compile(r"(?im)^\s*(?:api_key|password|access_token|client_secret)\s*[:=]\s*['\"]?[A-Za-z0-9_+/=-]{16,}"),
}
GENERATED = {"__pycache__", ".venv", "venv", ".pytest_cache", ".mypy_cache", ".ruff_cache", "build", "dist"}
PRIVATE_PARTS = {"private", "state", "data", "outputs", "work", ".get-hired-now"}
PRIVATE_SUFFIXES = {".pdf", ".docx", ".sqlite", ".sqlite3", ".db", ".pem", ".key", ".p12"}


def scan_text(label, raw, denylist):
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        return [(label, "unreviewed_binary")]
    if "\x00" in content:
        return [(label, "unreviewed_binary")]
    findings = [(label, name) for name, pattern in RULES.items() if pattern.search(content)]
    if any(term.casefold() in content.casefold() for term in denylist):
        findings.append((label, "private_denylist_match"))
    return findings


def path_findings(label):
    p = Path(label)
    findings = []
    if any(x in PRIVATE_PARTS for x in p.parts) or p.suffix.lower() in PRIVATE_SUFFIXES:
        findings.append((label, "private_artifact_path"))
    if p.name.startswith(".env") and p.name != ".env.example":
        findings.append((label, "environment_file"))
    return findings


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def scan(root, denylist=(), history=False):
    root = Path(root).resolve()
    findings, count = [], 0
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if ".git" in relative.parts or any(x in GENERATED or x.endswith(".egg-info") for x in relative.parts):
            continue
        if path.is_symlink():
            findings.append((relative.as_posix(), "symlink_requires_review"))
        elif path.is_file():
            label = relative.as_posix()
            findings.extend(path_findings(label))
            findings.extend(scan_text(label, path.read_bytes(), denylist))
            count += 1
    if history:
        # Every reachable commit/tree/blob is checked, not just the latest checkout.
        objects = git(root, "rev-list", "--objects", "--all").decode().splitlines()
        for entry in objects:
            sha, _, label = entry.partition(" ")
            kind = git(root, "cat-file", "-t", sha).decode().strip()
            if kind == "blob":
                findings.extend(path_findings(label))
                findings.extend(scan_text("history:" + label, git(root, "cat-file", "blob", sha), denylist))
                count += 1
            elif kind == "commit":
                findings.extend(scan_text("commit:" + sha[:12], git(root, "cat-file", "commit", sha), denylist))
    return sorted(set(findings)), count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--denylist", help="Private literal denylist OUTSIDE the repository")
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    denylist = []
    if args.denylist:
        path = Path(args.denylist).resolve()
        if path.is_relative_to(root):
            parser.error("Keep the private denylist outside the repository")
        denylist = [s.strip() for s in path.read_text(encoding="utf-8-sig").splitlines() if s.strip()]
    findings, count = scan(root, denylist, args.history)
    for label, rule in findings:
        print(f"FAIL {label}: {rule}")
    print(f"Scanned {count} file/blob entries; {len(findings)} findings.")
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(main())
