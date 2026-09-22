# Durable state contract

Choose one private candidate workspace outside this skill, its Git checkout and
public/shared output directories. One candidate per workspace. The AI writes the
files using available file tools; users do not author structured state.

```text
<private-workspace>/
  state.json                 Canonical current snapshot and durable event history
  originals/                 Supplied original CV; preserve bytes
  artifacts/<job-key>/        Fresh resume, cover letter, answer map and manifest
  evidence/<job-key>/         Source captures, exact receipts, required decisions
  work/                      Local generation and preview files
```

Start from [the blank state](../assets/state.example.json). Never load the
repository's fictional candidate into a real user's workspace.

## Snapshot fields

- `schema_version: 1`, integer `revision`, `updated_at` in UTC.
- `candidate`: null before intake; then `revision`, supplied identity/contact,
  original resume reference/hash, `facts` (value/status/source), `target_roles`,
  location/work authorization, `salary_policy`, `constraints` and writing preferences.
  Missing supplied values stay null. Preserve evidence and corrections.
- `permissions`: mode, auto_submit, action grants with scope/source, approvals.
- `integrations`: current capability bindings from the integrations reference.
- `jobs`: map keyed by stable employer plus exact requisition, or canonical official
  URL when no ID exists. Keep distinct requisitions separate. Preserve meaningful
  query parameters; merge mirror sightings only with identity evidence.
- `events`: chronological event objects with timestamp, job/action ID, kind and
  concise evidence reference. Store actual sensitive values only where needed.
- `next_actions`: resumable queue, blockers and responsible owner.

Each job includes identity/source timestamps, quoted required/preferred/unclear
requirements, candidate-evidence map, disposition, economics, preparation level,
form feasibility/questions, artifact manifest, stage, attempts and receipts.

Use stage values `DISCOVERED`, `EVALUATED`, `HUMAN_REQUIRED`, `REJECTED`, `RESEARCHED`,
`TAILORED`, `READY_FOR_REVIEW`, `APPROVED`, `SUBMITTING`, `SUBMITTED`, `UNRESOLVED`,
`FOLLOW_UP`. Keep `form_feasibility` and `submission_outcome` separate from stage.
Do not jump directly from a sighting to acceptance. Append intermediate events
even if a single turn completes several stages.

`TAILORED` means the requested local documents are actually produced. It is a valid
completion point for a local preparation request even when live form access is
unavailable. `READY_FOR_REVIEW` requires a complete exact-job packet, actual form
inspection and no unresolved required facts/branches. `APPROVED` additionally
requires current action authorization. Neither state proves submission. A supplied
question list alone cannot establish that a live form is complete.

An accepted job must have an observed exact-job employer receipt. A prior receipt
must never be erased when adding a later event. An existing `SUBMITTING` or
`UNRESOLVED` attempt blocks reapplication until evidence resolves its outcome.
After a crash, inspect saved state before touching a form. A browser tab is not the
ledger. Duplicate sightings add source evidence to the existing job.

## Write discipline

One record owner writes the shared snapshot. Workers return results and never
mutate it concurrently. Read the current revision immediately before a change.
Use atomic replacement and compare-and-swap revision checking when available.
Increment revision, append events and save after each material decision, artifact,
permission change and external attempt/result. The state must be durable before
an external action starts. Never reconstruct receipt counts from memory.

An optional standard-library helper provides exclusive lock, revision comparison,
atomic replacement and shape checks without any network access:

```sh
python <skill-path>/scripts/checkpoint.py init --workspace <private-workspace>
python <skill-path>/scripts/checkpoint.py show --workspace <private-workspace>
python <skill-path>/scripts/checkpoint.py save --workspace <private-workspace> --input <private-proposal.json> --expected-revision 0
```

The AI, not the person, builds the proposal. It must retain the old event history,
candidate evidence and receipts. The helper validates state shape and key safety
invariants; it cannot authenticate consent, understand a CV or enforce permissions
on unrelated host tools. Native transactional storage can replace this helper.
Without Python, use the host's durable file tools with a single writer and atomic
replacement where supported. Without durable storage, provide a downloadable
checkpoint and disclose that automatic crash-safe external execution is unavailable;
do not start autonomous submissions without durable attempt records.
