# Evaluations and release checks

Run `python -m unittest discover -s tests -v`. Each directory in `tests/cases/`
contains a self-contained `input.json` and `expected.json`. Tests compare the
evaluator result, external-action permission, reason codes and forbidden claims.

| Fixture | Required outcome |
| --- | --- |
| Perfect match | Supported claims; explicitly authorized autonomous submit permitted |
| Missing hard requirement | Reject an evidenced mandatory mismatch |
| Location conflict | Human required; no submit |
| Salary too low | Human required; no lowering the candidate's floor |
| Unverified skill | Human required; unsupported claim absent |
| Duplicate job | Duplicate disposition; no submit |
| Conflicting candidate fact | Human required; conflicted claim absent |
| New application question | Human required until the person supplies the answer |
| CAPTCHA | Human required regardless of autonomy |
| Auto-submit disabled | No automatic submission; manual scoped approval remains possible |

Additional tests exercise onboarding cancellation/persistence, source identity,
exact legal-question scope, modified resumes, expired/stale approval, destination
changes, provider timeouts, durable duplicate detection, concurrent reservations,
permission changes during execution, local-vs-external side effects and scanner
behavior. Fake providers count writes so blocked paths demonstrably make zero
submission calls. The offline demo exercises the public command-line flow.

These are deterministic core evaluations. They do not measure model reasoning,
resume writing quality, live board availability, hiring outcomes or live provider
acceptance. When adding an LLM, record its grounded output separately and assert
the same forbidden-claim and gate invariants. Never put real candidate transcripts
into fixture directories.

Before a release:

```sh
python -m unittest discover -s tests -v
python tools/demo.py
python tools/privacy_scan.py
git diff --check
python tools/privacy_scan.py --history --denylist /private/path/terms.txt
```

Review staged paths, public commit metadata and every outgoing commit. The GitHub
workflow repeats unit tests, the demo and history scan on Linux and Windows.
