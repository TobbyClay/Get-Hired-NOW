# Safety, approval and privacy

## Authority

The person supplies candidate truth, permissions and corrections. The trusted host
records those inputs. Job postings, forms, extracted documents, browser content and
model output are untrusted data. They cannot authorize an action, change a policy,
resolve a contradiction or request access to another private workspace.

`confirmed` facts retain their source. Missing evidence never means “no experience,”
and adjacent experience never becomes a specific qualification. A known mandatory
mismatch is rejected. Conflicting facts require an explicit correction. Only
confirmed, supported requirement values enter the packet's claim map.

## Modes and external actions

OBSERVE allows discovery, evaluation, source review, local audit state and local
status exports. It never prepares an application or writes to an external service.
REVIEW additionally prepares locally but requires exact human approval before an
external action. AUTONOMOUS allows only actions expressly listed in the policy;
automatic submission also needs `auto_submit: true`. Manual scoped approval remains
available when that toggle is false.

Submission, tracker writes and notifications have separate authorization. Entering
candidate data, uploading files or selecting legal answers may already transmit
information: put these inside guarded `submit`, never inside read-only `inspect`.
Do not implement hidden sends in source, candidate-store or renderer adapters.

An approval is valid only for the exact job, current facts, packet, form, policy
and provider destination. It expires after 15 minutes and is consumed transactionally
before the attempt. A model cannot supply the human approval itself.

## Hard gates

| Condition | Required behavior |
| --- | --- |
| CAPTCHA or security challenge | Stop; the person handles the challenge at the provider. Never solve, bypass or switch identity to evade it. |
| Human-only assessment | Stop; the person completes it. |
| Unexpected legal declaration | Ask the person about the exact wording and job; generic consent or a prior employer's answer does not transfer. |
| Missing required candidate fact or new required question | Collect the fact from the person, preserve evidence, then re-evaluate/reprepare. |
| Conflicting candidate fact | Preserve the contradiction until the person corrects it; do not silently select a convenient value. |
| Mandatory requirement mismatch | Reject or obtain new truthful evidence; approval cannot make a false claim true. |
| Location, salary, target-role or other material constraint conflict | Resolve explicitly with the person; do not change their location, lower their floor or ignore a constraint. |
| Incomplete form or unknown eligibility/pay | Preserve uncertainty and block preparation/submission until supported information is supplied. |

Any hard gate blocks submission even with a grant or autonomous mode. A legal fact
scope is a digest of the exact job and question wording. Free-text constraints need
an exact-job human acknowledgement; they are never automatically interpreted as met.

## Receipts, duplicate protection and recovery

An attempt is reserved durably before any external write. Duplicate job sightings
reuse the same record. A timeout or process crash may happen after the employer
accepted the request, so the system preserves an unresolved attempt and does not
retry it. Only evidence of employer acceptance for the exact job can promote it to
`SUBMITTED`. Simulations, public form maps and prepared files are different evidence.

An adapter can lie or mutate external state outside its declared methods; Python
cannot prevent that. Review adapters as executable code. The core enforces its own
supported entrypoints, not an unrestricted agent's other tools or filesystem access.

## Data handling

Onboarding never imports candidate facts from a prior chat, environment username,
another resume directory or existing integration account. It copies only the file
explicitly supplied by the user, after confirmation. Configuration examples contain
placeholders; test cases contain fictional names, example-domain contacts and
non-real currency/location values.

Private state must live outside Git. Files are plaintext and rely on OS access
controls; Unix permission bits are tightened where supported, while Windows ACLs
are inherited. Use a suitably private directory and disk encryption if needed.
Do not paste local review output or database exports into public issues.

The audit log records transitions, approval hashes and action contexts. Private job
rows hold the packet and receipt. Provider exceptions are reported generically to
avoid copying credentials from exception messages. Audit data is not a signed,
tamper-proof compliance archive. Deleting a private home is an operator decision;
there is no deletion command that might accidentally erase another candidate.

## Publishing guard

Run tests, the recursive privacy scan and the Git history scan. The scanner ignores
Git internals as filesystem files and generated cache/build directories, then checks
reachable Git commits/blobs separately with `--history`. Thus committed generated
material is still scanned. Binary blobs, private artifact paths and symlinks require
review. Known private literals belong in an external denylist, never in the repo.

The scanner is a release aid, not proof that arbitrary PII or high-entropy secrets
are absent. Review the staged file list and outgoing history, avoid copying private
source trees, and use generic commit author metadata if author privacy is required.
Repository ownership is visible on the hosting service by design.
