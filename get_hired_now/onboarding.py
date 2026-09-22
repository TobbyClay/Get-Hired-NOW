"""Interactive intake. No profile is inferred from machine or conversation state."""

import copy
import hashlib
import json
import math
from pathlib import Path

from .models import DEFAULT_POLICY, validate_candidate, validate_policy


def ask_text(ask, prompt, allow_empty=False):
    while True:
        value = ask(prompt + " ").strip()
        if value or allow_empty:
            return value


def ask_choice(ask, prompt, choices, default):
    while True:
        value = ask(f"{prompt} ({'/'.join(choices)}) [{default}]: ").strip() or default
        if value in choices:
            return value


def read_policy(ask=input, tell=print):
    policy = copy.deepcopy(DEFAULT_POLICY)
    tell("OBSERVE evaluates only. REVIEW requires approval per external action. AUTONOMOUS uses explicit action grants.")
    policy["mode"] = ask_choice(ask, "Permission mode", ["OBSERVE", "REVIEW", "AUTONOMOUS"], "REVIEW")
    if policy["mode"] == "AUTONOMOUS":
        for action in ("submit", "tracker", "notify"):
            if ask_choice(ask, f"Authorize external {action} actions", ["yes", "no"], "no") == "yes":
                policy["allowed_actions"].append(action)
        if "submit" in policy["allowed_actions"]:
            policy["auto_submit"] = ask_choice(ask, "Enable automatic submission", ["yes", "no"], "no") == "yes"
    validate_policy(policy)
    return policy


def setup(state, ask=input, tell=print):
    if state.configured():
        raise ValueError("This private home already has a profile. Use fact/policy commands or a separate home.")
    tell("Let's build your private profile. Nothing is read from another workspace or account.")
    tell("Only the facts you provide will be used. The original resume is stored without extracting or inventing claims.")
    candidate = {"schema_version": 1, "facts": {}}
    candidate["display_name"] = ask_text(ask, "What name should your applications use?")
    contact = ask_text(ask, "What contact email should applications use?")
    candidate["facts"]["contact_email"] = {"value": contact, "status": "confirmed", "source": "user:onboarding"}
    candidate["location"] = ask_text(ask, "Where do you currently live? Use the location code your job sources will use.")
    roles = ask_text(ask, "Which roles are you targeting? Separate roles with commas.")
    candidate["target_roles"] = [x.strip() for x in roles.split(",") if x.strip()]
    tell("Salary expectation is your minimum acceptable amount, not an employer's advertised budget.")
    while True:
        try:
            minimum = float(ask_text(ask, "What is your minimum acceptable compensation amount?"))
            if math.isfinite(minimum) and minimum >= 0:
                break
        except ValueError:
            pass
        tell("Enter a finite, nonnegative number.")
    candidate["salary"] = {"minimum": minimum,
                           "currency": ask_text(ask, "Which currency?").upper(),
                           "period": ask_choice(ask, "Pay period", ["year", "month", "hour"], "year"),
                           "basis": ask_choice(ask, "Pay basis", ["gross_base", "net_base", "total"], "gross_base")}
    constraints = ask_text(ask, "What constraints apply (work arrangement, hours, travel, conflicts, exclusions)? Separate with semicolons; blank means none.", True)
    candidate["constraints"] = [x.strip() for x in constraints.split(";") if x.strip()]
    for field, question in (
        ("work_authorization", "Where and under what conditions are you authorized to work?"),
        ("work_history", "Describe your work history, dates, responsibilities and evidence."),
        ("skills", "List skills you can support with evidence."),
        ("education", "Describe education/certifications and any presentation preferences."),
        ("availability", "What is your availability and any notice period?"),
    ):
        value = ask_text(ask, question + " Leave blank if unknown or omitted.", True)
        if value:
            candidate["facts"][field] = {"value": value, "status": "confirmed", "source": "user:onboarding"}
    tell("Add structured facts required by your job sources (for example, a skill duration). Never guess.")
    while True:
        key = ask_text(ask, "Fact key (blank to finish):", True)
        if not key:
            break
        raw = ask_text(ask, "Fact value as JSON (text in quotes, number, true/false, or list):")
        try:
            value = json.loads(raw)
            if value is None:
                raise ValueError()
        except ValueError:
            tell("Invalid or null JSON; fact was not saved.")
            continue
        source = ask_text(ask, "What evidence supports this fact?")
        if key in candidate["facts"] and candidate["facts"][key]["value"] != value:
            tell("This contradicts a fact already supplied; resolve it with the fact command after setup.")
            candidate["facts"][key]["status"] = "conflicted"
        else:
            candidate["facts"][key] = {"value": value, "status": "confirmed", "source": source}
    while True:
        source = Path(ask_text(ask, "Path to your original CV/resume (.pdf, .docx, .txt or .md):").strip('"')).expanduser()
        if source.is_file() and source.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}:
            content = source.read_bytes()
            if content and len(content) <= 20 * 1024 * 1024:
                break
        tell("Choose a supported, nonempty original resume file up to 20 MB.")
    checksum = hashlib.sha256(content).hexdigest()
    destination = state.home / ("original-" + checksum + source.suffix.lower())
    candidate["resume"] = {"path": str(destination), "sha256": checksum}
    policy = read_policy(ask, tell)
    validate_candidate(candidate)
    tell(json.dumps({"candidate": candidate, "policy": policy}, indent=2))
    if ask_text(ask, "Review these facts. Type SAVE to persist them privately; anything else cancels:") != "SAVE":
        tell("Setup canceled. No profile or resume was saved.")
        return False
    destination.write_bytes(content)
    try:
        destination.chmod(0o600)
        state.save_settings(candidate, policy)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    tell("Private profile saved. No data was sent to an external service.")
    return True
