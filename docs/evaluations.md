# Evaluation and release verification

The skill is the primary product. Tests of the optional Python framework alone
do not establish that the skill guides an AI correctly.

## Skill evaluation

Validate SKILL.md frontmatter, reference closure and installable ZIP contents.
Extract the ZIP into an isolated directory and run its optional checkpoint helper
without importing the repository's Python package. Test atomic revision checks,
duplicate writers, missing acceptance evidence and preservation of receipts.
Also test immutable attempt reservations, candidate-workspace binding, batch identity
deduplication, wrong-role receipts, late reconciliation, upload versus final Submit,
pre-submit blockers and unknown/invalid time denominators. The report helper tests
record projection, not authenticity of an employer response or quality of a CV.

For a revised pipeline exercise, use fictional raw inputs with cross-source mirrors,
an uncertain prior submit, conflicting original/repost dates, missing required
answers, unknown pay and supported adjacent responsibilities. Observe actual local
files and decisions. Do not show the evaluating AI this expected-behavior checklist.

For behavioral forward-testing, give an independent AI the installed skill, a
realistic user request and fictional raw documents/posting evidence. Do not supply
the expected answer. Restrict available tools and external effects explicitly.
Inspect actual output files and persisted state, unsupported claims, tool calls,
permissions and truthful reporting of missing capabilities. A file-only exercise
validates that subset; it is not evidence of live browser submission.

For the v0.2 correction, an independent AI executed a file-only preparation request
from a fictional original CV and supplied posting. It produced an actual tailored
Markdown resume, answer map, preserved original, evidence/QA files, artifact hashes
and a durable checkpoint without importing the legacy framework. It reported zero
live-verification or submission actions. Ambiguities about local preparation versus
form readiness, unspecified formats and message identifiers were used to clarify
the skill. This exercise does not certify live board/browser compatibility.

For the v0.3 pipeline update, an independent file-only exercise reviewed five
fictional sightings representing four exact roles. It produced one fresh editable
resume with a sourced answer map, final-content QA, hashes and a durable checkpoint.
It merged the mirror sighting, used original publication rather than a refresh,
kept an uncertain prior submission unresolved without retry, treated preferred
qualification gaps truthfully, and left a personal recording and prohibited-AI
exercise to the candidate. Missing live access and eligibility stayed explicit:
zero live screens, new submissions or confirmations, and zero submission-ready
packets. The original inputs were preserved. This validates local preparation and
queue decisions within that exercise, not live ATS compatibility or hiring results.

## Ten regression scenarios

The self-contained inputs/expectations in `tests/cases/` cover perfect match,
missing hard requirement, location conflict, salary too low, unverified skill,
duplicate job, conflicting candidate fact, new application question, CAPTCHA and
auto-submit disabled. They can also supply raw fictional inputs for agent evaluations.
Keep expected outcomes hidden from the evaluating agent. Their automated runner
tests the optional deterministic engine, not LLM behavior.

## Commands for maintainers

```sh
python -m unittest discover -s tests -v
python tools/package_skill.py --output /private/build/get-hired-now.zip
python tools/privacy_scan.py --history
git diff --check
```

The GitHub workflow checks unit tests, skill packaging and privacy on Linux and
Windows. The legacy offline demo is retained as a test of the optional reference
engine only. No real application is sent by tests. Live job-board/browser behavior
depends on the installed AI host and must not be claimed without observed execution.
