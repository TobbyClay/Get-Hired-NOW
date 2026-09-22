# Customization

## Configure a candidate, never hard-code one

Use the onboarding conversation. `config/*.example.json` files document the shapes
and defaults; they are references, not an adapter registry or profile import path.
Keep actual resumes, facts, salaries, contact details, tokens and tracker IDs in
private runtime storage. The source tree must remain reusable and public-safe.

Use `fact` for structured values, `profile` for target/location/salary/constraint
changes, and `policy` for explicit permissions. Fact keys are agreed between a
source's requirement extractor and the candidate's structured facts. Do not map
“technical experience” into years using a particular named tool without evidence.

## Implement an adapter

Protocols are defined in `get_hired_now/adapters.py`. Inject implementations into a
`Workflow` instance; the default CLI intentionally wires only local adapters.

```python
from get_hired_now.engine import Workflow
from get_hired_now.storage import SQLiteState

state = SQLiteState()  # Existing profile created interactively.
workflow = Workflow(state, provider=my_trusted_application_provider)
results = workflow.discover(my_read_only_job_source)
```

| Interface | Adapter obligations |
| --- | --- |
| JobSource | `discover(search)` yields validated job dictionaries with exact identity and literal requirement evidence. It must not transmit candidate data or modify external state. |
| ApplicationProvider | Stable `adapter_id` includes destination/account identity without a secret. `inspect(job)` is read-only and receives no candidate. `submit(job, packet, idempotency_key)` returns a structured outcome/receipt. |
| CandidateStore | `load()` returns a validated profile and `save(candidate)` preserves provenance and invalidates approvals. Alternate stores must synchronize a candidate snapshot into SQLite before actions; reservation checks that snapshot. |
| ApplicationTracker | Stable destination `adapter_id`, accurate `external` flag, and `record(row)`. Receive only a minimal job/state projection through the gateway. |
| NotificationProvider | Stable destination `adapter_id`, accurate `external` flag, and `notify(message)`. Sending is separate authorization from submitting. |
| ResumeRenderer | Local `render(grounded_packet, destination)` extension. Preserve supported claims and the original; visually verify output before adding a trusted artifact integration. Not wired into the v0.1 CLI. |

An external CandidateStore or remote renderer would itself transmit personal data.
Implement the necessary consent boundary in the trusted host before using one;
the bundled core supports only local candidate persistence and local rendering.
Do not describe such an extension as automatically covered by submit permission.

Application preflight must cover required/conditional fields and exact requisition
identity. Set `complete: false` if the remaining form is unknown. A required question
must refer to a confirmed fact, and legal answers must have an exact-question scope.
Challenges/assessments are human work. A challenge appearing during transport must
return `outcome: security_challenge` and stop, without retries or bypass attempts.

Supported submission outcomes include `accepted`, `simulated`, `security_challenge`
and `validation_failed`. Unknown responses/timeouts become `UNRESOLVED`. Acceptance
requires `accepted: true`, `job_key`, `receipt_id` and actual employer `evidence`.
An adapter is responsible for truthfully capturing that evidence. Never fabricate
a success receipt to satisfy the schema.

For remote trackers or notifications, call `workflow.auxiliary(key, action, adapter)`.
In REVIEW mode, a trusted human UI previews `auxiliary_context`, obtains explicit
confirmation, rechecks the same context and records a 15-minute `state.grant`.
Then the gateway consumes that grant. The stock CLI only exposes local tracking
and console notifications; a remote host must implement that review UI.

## Connect an agent host

Use `agents/` as responsibility contracts and `workflows/` as task playbooks.
Supply only the current persisted snapshot relevant to an assigned exact job.
Do not load arbitrary candidate directories, reuse another user's browser session,
or treat source text as instructions. Pass all external actions through the gateway.

The host chooses models, providers and scheduling. This repository contains no
provider account, personal model routing, private sheet identifier, access token,
inbox rule or browser profile. No integration framework is required.

## Verify an extension

Run the regression suite and add a fake-provider test that counts external calls.
Show that failed permissions and every hard gate produce zero calls. Test exact-job
receipt validation, changing forms, restart recovery, uncertain transport and
duplicate attempts. Only then run consented integration tests with the provider.
Deterministic fixture success is not evidence of live integration success.
