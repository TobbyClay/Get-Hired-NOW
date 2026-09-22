"""Exercise the public CLI with fictional input, private temporary state, no network."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="get-hired-now-demo-") as temp:
        root = Path(temp)
        resume = root / "supplied.txt"
        resume.write_text("Fictional Candidate\nThree fictional years using Example Tool.\n", encoding="utf-8")
        home = root / "private-home"

        def run(*args, user_input=None):
            result = subprocess.run([sys.executable, "-m", "get_hired_now", "--home", str(home), *args],
                                    cwd=ROOT, input=user_input, text=True, capture_output=True, check=True)
            return result.stdout

        responses = ["Fictional Candidate", "candidate@example.com", "FICTIONAL-REGION", "Example Engineer",
                     "100", "TOK", "year", "gross_base", "", "", "", "", "", "",
                     "sample_tool_years", "3", "fictional:user-supplied-demo", "", str(resume), "REVIEW", "SAVE"]
        run("setup", user_input="\n".join(responses) + "\n")
        print("Interactive setup: saved only user-supplied fictional data in temporary private storage.")
        rows = json.loads(run("discover", str(ROOT / "examples" / "jobs.json")))
        key = rows[0]["key"]
        assert rows[0]["decision"] == "DISCOVERED"
        assert json.loads(run("evaluate", key))["decision"] == "MATCH"
        assert json.loads(run("prepare", key))["state"] == "READY_FOR_REVIEW"
        assert json.loads(run("submit", key))["reason"] == "approval_required"
        print("Review mode: unapproved submission blocked.")
        run("approve", key, user_input="APPROVE\n")
        assert json.loads(run("submit", key))["state"] == "SIMULATED"
        assert json.loads(run("list"))[0]["state"] == "SIMULATED"
        assert json.loads(run("discover", str(ROOT / "examples" / "jobs.json")))[0]["decision"] == "DUPLICATE"
        run("track", key)
        print("Persisted result: SIMULATED. Duplicate re-import detected across processes.")
        print("No real application, notification or network request was sent.")
    print("Temporary demo candidate and state removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
