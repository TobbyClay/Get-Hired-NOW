# Formal permission contract

The trusted AI host applies this contract before every external action. The skill
does not grant itself permissions and cannot override host/tool restrictions.
Persist the policy and the actual user instruction that established its scope.

| Mode | Public search/research/evaluation | Local preparation | External mutation |
| --- | --- | --- | --- |
| OBSERVE | Allowed within request | Do not prepare/upload application documents | Denied |
| REVIEW | Allowed | Allowed within request | Requires the person's approval for the concrete action |
| AUTONOMOUS | Allowed | Allowed within request | Allowed only for explicitly authorized action categories and scope |

Local checkpoint writes are allowed in all modes. In AUTONOMOUS, automatic
application submission also requires `auto_submit: true`; false means prepare and
seek exact approval. Standing authorization must name real scope (for example,
qualified roles matching saved targets in this batch), not unrestricted authority.
Separate `application`, `tracker`, `notify`, `outreach` and `schedule` grants.
Also record inbox/code, account/profile and interview/calendar scope when used.
Standing application authorization covers the ordinary reviewed contact-data,
resume upload and Submit actions included in that instruction; it does not silently
authorize a new account, unrelated messages or another person's signed-in session.

## Decision order

1. Verify the exact employer/job, current candidate facts, artifact versions,
   complete observed form, intended destination and absence of a previous accepted
   or uncertain attempt. Recheck dynamic conditions immediately before acting.
2. If a hard gate exists, stop the affected action regardless of approval or mode.
3. Deny external mutation in OBSERVE.
4. In REVIEW, require a current approval bound to this concrete payload/destination.
5. In AUTONOMOUS, verify the action's grant, current scope and auto-submit switch;
   otherwise use a specific human approval. Do not reinterpret a missing grant.
6. Persist a unique action/attempt ID and `SUBMITTING` before transmitting data.
   Bind the exact approval to that action when starting. A crash/timeout remains
   unresolved; do not replay it. Standing grants remain scoped rather than consumed
   as if each ordinary application needed a new approval.
7. Record the actual response and evidence. Only exact-role employer acceptance
   permits `SUBMITTED`; other outcomes retain their real failure/uncertainty.

## Hard human gates

- CAPTCHA, security challenge, spam/application cap, or an access control: person
  must resolve at the provider. No automated solving, retry-around-control or evasion.
- Human-only test, attention check, required personal video or assessment.
- An unexpected legal declaration or changed consent wording: collect the person's
  exact answer to that employer/question. Generic approval does not answer it.
- A required fact absent from verified candidate evidence, or conflicting facts.
- A material mandatory-requirement, location, work-authorization, compensation or
  other candidate-constraint conflict. Do not lower a floor or invent eligibility.
- An incomplete required/conditional form branch or ambiguous employer identity.

An undisclosed employer salary is not itself a salary conflict. Record economics
as unknown, reduce tailoring investment if appropriate, and follow the person's
policy on undisclosed pay. Ask only if that policy or a required answer is missing.
An unmet preferred skill is not a hard gate.

## Approval record

Store action ID/category, job key, destination, candidate revision, posting/form
version, hashes or immutable versions of artifacts, exact action preview, the
user-message reference, granted time and expiry. If the host exposes no message ID,
quote the actual instruction with its observed time/context; never invent an ID.
Use the person's stated duration or the host's actual expiry policy. If neither
sets an expiry, record it as unspecified and revalidate payload/scope rather than
inventing a short timeout that repeatedly asks for permission. Record
standing scope separately rather than pretending it is a perpetually fresh exact
approval. A material change requires a new decision or renewed approval.

The person can withdraw authorization at any time. Save the change immediately
and stop pending affected actions. The model must never fabricate the user-message
reference, authorize itself, or mark a hard gate resolved without actual evidence.
Latest explicit corrections and withdrawals override historical permission notes.
A saved automation prompt is not permission to revive a superseded candidate policy.
