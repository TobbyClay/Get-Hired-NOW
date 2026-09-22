# Architecture

## Separation of responsibilities

```text
Human / trusted agent host
       |
       v
CLI or Workflow API ---- CandidateStore
       |
       +-- evaluator: requirement -> candidate evidence
       +-- permissions: policy + hard gates + scoped approval
       +-- SQLiteState: transitions, revisions, reservations, receipts
       |
       +-- JobSource (read-only discovery)
       +-- ApplicationProvider (inspect, then guarded submit)
       +-- ApplicationTracker (guarded when external)
       +-- NotificationProvider (guarded when external)
       +-- ResumeRenderer (optional local extension)
```

No agent reconstructs application status from a conversation. SQLite holds
`settings`, `jobs`, `events`, `grants` and `effects`. The database's `user_version`
is 1; incompatible future versions fail instead of silently resetting state.

## Contracts

All records are JSON compatible. Candidate and job records use `schema_version: 1`.

| Record | Essential fields |
| --- | --- |
| Candidate | display_name, location, target_roles, salary, constraints, facts, resume |
| Fact | value, status (`confirmed`, `unverified`, `conflicted`), source; optional scope |
| Job | employer, title, requisition_id or URL, observed_at, locations, requirements, salary |
| Requirement | fact key, op (`eq`, `gte`, `contains`), value, kind, literal quote, source |
| Form | exact job_key, complete flag, security_challenge flag, explicit question list |
| Question | id, text, fact key, kind (`fact`, `legal`, `human_only`), required boolean |
| Policy | mode, auto_submit boolean, allowed_actions list |
| Packet | exact job/candidate hashes, provider, inspected form, supported claims, evidence, answers, original resume |
| Receipt | outcome, exact job_key; acceptance additionally needs accepted=true, receipt_id, evidence |

`*` in `locations` means explicitly verified worldwide eligibility. An empty list
means unknown. Currency `TOK` and `FICTIONAL-REGION` occur only in fictional examples.
The evaluator does not infer residence, work authorization or eligibility from an
employer's headquarters or the word “remote.” Encode actual authorization and
other hard conditions as requirements referring to candidate facts.

Confirmed means candidate-supplied/attested with a source, not independently
background-checked. The host must verify source trust. Unknown mandatory evidence
requires a human; a supported contradiction of a hard requirement rejects the job.
A preferred gap does not reject it. Salary comparisons require identical currency,
period and basis. Unknown salary/eligibility is conservatively gated at preparation.

## State and concurrency

The transition graph is enforced in `models.TRANSITIONS`; invalid transitions fail.
Jobs are keyed by normalized employer plus exact requisition ID, or by canonical
URL when no requisition exists. Only marketing query parameters are discarded;
job-specific parameters remain significant. Sources must normalize aliases/clone
IDs explicitly; fuzzy cross-employer deduplication is not implemented.

Every transition increments a revision and appends an audit event in the same
transaction. Callers provide the version they reviewed. `BEGIN IMMEDIATE` reserves
external actions before transport, rechecks candidate and policy snapshots, consumes
the one-use approval when needed, records a unique effect context, and moves an
application into `SUBMITTING`. Concurrent workers cannot reserve that same attempt.

The external call happens after the transaction commits. No database can make an
arbitrary web form and a local transaction atomically commit together. A crash or
timeout therefore requires reconciliation and never an automatic retry. Idempotency
keys are passed to providers that can support them.

`SUBMITTED` requires a structured exact-job receipt, not a successful HTTP request
alone. `SIMULATED` is a separate outcome. `UNRESOLVED` is retained across restarts.
Acceptance cannot be demoted or resubmitted through normal transitions. `FOLLOW_UP`
is an available ledger state; scheduling/outreach delivery is not implemented.

## Approval integrity

The SHA-256 approval context includes the action, posting, full packet, current
form, candidate snapshot hash, policy and provider destination identity. Its expiry
is 15 minutes. Resume bytes are rehashed before execution. Changes require renewed
preparation and/or approval. Hashes detect change; they do not encrypt data or prove
that a fact is true.

The CLI is a trusted human interface. Agent hosts must expose read/prepare/submit
tools separately from human approval and policy editing. Do not let a model call
`grant`, `approve`, `save_settings` or mutate SQLite as though that were human
authorization. Python protocols and local files are not a malicious-code sandbox.

## Implementation scope

The default implementation is synchronous and local, with a deterministic evaluator.
Agent markdown describes research, tailoring and follow-up responsibilities for a
host to implement. No LLM is invoked by this package. The core's `RESEARCHED` and
`TAILORED` states refer to source-evidence review and a selected JSON packet;
they do not assert that a browser investigation or generated resume occurred.
