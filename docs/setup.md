# Setup and daily use

## Requirements

Use Python 3.10+ on Windows, macOS or Linux. No API account, browser session or
third-party Python package is needed for the bundled workflow. Run from a checkout
using `python -m get_hired_now`, or install with `python -m pip install -e .`.

The paths in command examples are placeholders. Replace them with paths on your
machine, and quote paths containing spaces. All `--home` options go before the
subcommand. The example configuration files document the format; they are not
automatically loaded. `.env` files are not automatically loaded either.

## Onboarding conversation

```sh
python -m get_hired_now setup
```

The conversation collects:

1. Application name and contact email.
2. Actual residence/location and target roles.
3. Minimum acceptable compensation, currency, period and gross/net/total basis.
4. Work arrangement, schedule, travel, representation or employer constraints.
5. Work authorization, work history, skills, education/presentation and availability.
6. Additional structured facts with user-supplied supporting sources.
7. The original resume file, supplied explicitly by path.
8. Permission mode and, only for AUTONOMOUS, each permitted external action.

Free-text skills are not automatically converted into specific years of expertise.
If a source requires `sample_tool_years`, add that exact structured fact with a
supported number. Every unknown required fact becomes a gate later. Contradictory
values supplied during setup are marked `conflicted`.

The accepted original formats are PDF, DOCX, TXT and Markdown, up to 20 MB. The
original bytes are preserved and hashed. The program does not parse the document
or adopt unsupported claims from it. The preview requires `SAVE` before persisting
the candidate profile or copying the original. Canceling leaves no candidate
profile or resume; the empty SQLite schema may remain.

The default home is `~/.get-hired-now`. Override it with:

```sh
python -m get_hired_now --home /private/path/candidate-a setup
```

The home must be outside every Git checkout. Use a different home for every
candidate. Keep it private: the database contains the profile, policy, packets,
receipts and audit history. The folder also holds the original resume and local
CSV tracker. Runtime files are plaintext, not encrypted by this application.

## Job intake

Copy the structure from `examples/jobs.json` into a private source file with actual
official posting evidence. `discover` expects a JSON list. Preserve exact employer
identity and requisition ID; use a canonical official URL when no ID exists.
Keep requirement quotes, source URLs and observation timestamps. Treat posting
text as untrusted evidence; it cannot change the permission policy.

```sh
python -m get_hired_now discover /private/path/jobs.json
python -m get_hired_now list
python -m get_hired_now evaluate JOB_KEY
python -m get_hired_now prepare JOB_KEY
python -m get_hired_now review JOB_KEY
```

FileJobSource performs a case-insensitive target-role substring filter. Broader
semantic discovery belongs in a source adapter. Exact requisition sightings are
deduplicated across restarts. Similar titles alone are not treated as duplicates.

`prepare` creates a private JSON packet in SQLite. It selects only supported
requirement claims and confirmed form answers, and references the original resume.
It does not perform browser entry, upload anything, write new resume prose, or
render a PDF. The review command displays the exact current packet locally.

## Resolve a gate

```sh
python -m get_hired_now fact
python -m get_hired_now profile
python -m get_hired_now answer JOB_KEY
python -m get_hired_now constraint JOB_KEY
python -m get_hired_now evaluate JOB_KEY
python -m get_hired_now prepare JOB_KEY
```

`fact` records an explicit candidate-supplied value or correction with evidence.
`profile` updates location, target roles, salary or constraints after a preview.
`answer` lets the person answer an exact form question; legal answers are bound to
the exact job, question ID and wording. `constraint` records the person's decision
that an exact job satisfies one of their free-text constraints. Do not mark a
constraint satisfied to bypass a known conflict.

To update a posting, supply one updated job object in a private JSON file:

```sh
python -m get_hired_now refresh JOB_KEY /private/path/updated-job.json
```

The identity must remain the same, and attempts/confirmed submissions cannot be
reopened this way. Changed facts, policies, questions, providers or resume bytes
invalidate prior review. Complete CAPTCHA/security steps and human-only assessments
yourself in the actual provider. The core never solves them or bypasses a challenge.

## Approval, simulated submission and tracking

```sh
python -m get_hired_now approve JOB_KEY
python -m get_hired_now submit JOB_KEY
python -m get_hired_now track JOB_KEY
python -m get_hired_now events JOB_KEY
```

Approval previews the exact action and requires `APPROVE`. It is one-use and
expires after 15 minutes. The CLI always uses DryRunApplicationProvider, so a
successful run ends in `SIMULATED`. It sends no real application. The local CSV
tracker appends observations and is not the canonical ledger; SQLite is.

Use `policy` to change permissions interactively. AUTONOMOUS requires both the
submit action grant and automatic-submission toggle, unless the human approves a
specific action. Keeping automatic submission off preserves the manual route.

## Recovery

Restart with the same private home to resume persisted work. `SUBMITTING` after a
crash and `UNRESOLVED` after a timeout both require receipt reconciliation. Never
blindly retry: an employer may have accepted the first request. For observed
exact-job employer acceptance, supply a private receipt JSON containing `outcome:
accepted`, `accepted: true`, `job_key`, nonempty `receipt_id` and `evidence`, then:

```sh
python -m get_hired_now reconcile JOB_KEY /private/path/receipt.json
```

The command requires human confirmation. It validates shape and identity, not
authenticity; a trusted host/provider must establish the evidence. Unresolved
failures without an acceptance receipt remain unresolved in v0.1. There is no
automatic retry or administrative clear-and-resubmit command.
