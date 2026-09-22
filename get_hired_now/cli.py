"""Small local CLI. No live submission integration is enabled by default."""

import argparse
import json
import sys

from .adapters import CSVTracker, ConsoleNotification, DryRunApplicationProvider, FileJobSource
from .engine import Workflow
from .models import digest, job_key
from .onboarding import ask_text, read_policy, setup
from .permissions import question_scope
from .storage import SQLiteState


def emit(value):
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description="A private, evidence-grounded job-search workflow")
    parser.add_argument("--home", help="Private state directory outside every Git checkout")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("setup", help="Collect a new private profile through a conversation")
    commands.add_parser("policy", help="Interactively review and change permissions")
    commands.add_parser("fact", help="Supply or correct a fact; invalidates old approvals")
    commands.add_parser("profile", help="Interactively correct location, roles, salary or constraints")
    discover = commands.add_parser("discover", help="Import a JSON job source")
    discover.add_argument("source")
    commands.add_parser("list", help="List saved job identities and states")
    for action in ("evaluate", "prepare", "review", "approve", "submit", "events", "track", "notify", "answer", "constraint"):
        command = commands.add_parser(action)
        command.add_argument("key", help="Full job key returned by discover or list")
    refresh = commands.add_parser("refresh", help="Re-evaluate a changed exact-job posting")
    refresh.add_argument("key")
    refresh.add_argument("source", help="JSON file containing one updated job object")
    reconcile = commands.add_parser("reconcile", help="Record supplied exact-job acceptance evidence")
    reconcile.add_argument("key")
    reconcile.add_argument("receipt", help="Private JSON receipt path")
    args = parser.parse_args(argv)
    try:
        state = SQLiteState(args.home)
        flow = Workflow(state, DryRunApplicationProvider())
        if args.command == "setup":
            setup(state)
        elif args.command == "policy":
            candidate = flow.candidates.load()
            policy = read_policy()
            emit(policy)
            if ask_text(input, "Type SAVE to change permissions:") == "SAVE":
                state.save_settings(candidate, policy)
        elif args.command == "profile":
            candidate = flow.candidates.load()
            field = ask_text(input, "Field to correct (location/target_roles/salary/constraints):")
            if field not in {"location", "target_roles", "salary", "constraints"}:
                raise ValueError("Unsupported profile field")
            value = json.loads(ask_text(input, "New value as JSON:"))
            emit({"field": field, "old": candidate[field], "new": value})
            if ask_text(input, "Type SAVE to confirm your supplied correction:") == "SAVE":
                candidate[field] = value
                flow.candidates.save(candidate)
        elif args.command == "fact":
            candidate = flow.candidates.load()
            key = ask_text(input, "Fact key:")
            if key in candidate["facts"]:
                emit({"existing": candidate["facts"][key]})
            value = json.loads(ask_text(input, "Your verified value as JSON:"))
            source = ask_text(input, "What evidence supports the value or correction?")
            if ask_text(input, "Type SAVE to confirm your supplied fact:") == "SAVE":
                candidate["facts"][key] = {"value": value, "status": "confirmed", "source": source}
                flow.candidates.save(candidate)
        elif args.command == "constraint":
            candidate = flow.candidates.load()
            job = state.get(args.key)["body"]["job"]
            emit({"job": job, "constraints": candidate["constraints"]})
            constraint = ask_text(input, "Copy the exact constraint you have reviewed for this job:")
            if constraint not in candidate["constraints"]:
                raise ValueError("Unknown constraint")
            if ask_text(input, "Type SATISFIED only if this job satisfies that constraint:") == "SATISFIED":
                candidate["facts"]["constraint:" + digest([job_key(job), digest(job), constraint])] = {
                    "value": True, "status": "confirmed", "source": "user:exact-job-constraint"}
                flow.candidates.save(candidate)
        elif args.command == "answer":
            candidate = flow.candidates.load()
            job = state.get(args.key)["body"]["job"]
            form = flow.provider.inspect(job)
            emit(form)
            qid = ask_text(input, "Exact question ID to answer yourself:")
            question = next((q for q in form["questions"] if q["id"] == qid), None)
            if not question or question["kind"] == "human_only":
                raise ValueError("Unknown question or human-only assessment; complete it at the provider")
            value = json.loads(ask_text(input, "Your answer as JSON:"))
            if ask_text(input, "Type SAVE to confirm this exact question and answer:") == "SAVE":
                candidate["facts"][question["fact"]] = {"value": value, "status": "confirmed",
                    "source": "user:exact-question", "scope": question_scope(job, question)}
                flow.candidates.save(candidate)
        elif args.command == "discover":
            emit(flow.discover(FileJobSource(args.source)))
        elif args.command == "refresh":
            from pathlib import Path
            emit(flow.refresh(args.key, json.loads(Path(args.source).read_text(encoding="utf-8"))))
        elif args.command == "list":
            emit(state.list())
        elif args.command in {"evaluate", "prepare", "submit"}:
            emit(getattr(flow, args.command)(args.key))
        elif args.command in {"review", "approve"}:
            context = flow.submission_context(args.key)
            emit({"context": context["context"], "payload": context["payload"], "gates": context["gates"]})
            if args.command == "approve":
                if context["gates"]:
                    raise ValueError("Resolve the listed gates; an approval cannot override them")
                if ask_text(input, "Type APPROVE to authorize exactly this application for 15 minutes:") == "APPROVE":
                    flow.approve(args.key, context["context"])
                    print("Scoped approval saved. Run submit to execute it.")
        elif args.command == "events":
            emit(state.events(args.key))
        elif args.command == "track":
            emit(flow.auxiliary(args.key, "tracker", CSVTracker(state.home)))
        elif args.command == "notify":
            emit(flow.auxiliary(args.key, "notify", ConsoleNotification()))
        elif args.command == "reconcile":
            from pathlib import Path
            receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
            emit(receipt)
            if ask_text(input, "Type CONFIRM only if this is observed employer acceptance for the exact job:") == "CONFIRM":
                emit(flow.reconcile(args.key, receipt))
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(f"Cannot continue: {error}", file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("Conversation canceled.", file=sys.stderr)
        return 130
