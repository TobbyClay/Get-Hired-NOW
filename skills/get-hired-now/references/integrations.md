# Tool-backed, replaceable integrations

An adapter here is a named capability binding to tools the host already exposes.
It need not be new executable code. Inspect tool descriptions and relevant installed
skills before invoking them. Never invent tool names, signed-in access or provider
capabilities. Record `available`, `unavailable` or `unverified` and when observed.

| Interface | Preferred execution | Replacement/fallback |
| --- | --- | --- |
| JobSource | Available job-search connector; public search; official employer/ATS pages | Read a supplied URL/posting. Without live web tools, disclose the discovery limitation. |
| ApplicationProvider | Available browser/form tools or documented supported application API | Prepare actual local documents and answer map; leave submission blocked if no submission tool. |
| CandidateStore | Private local files through host file tools | User-controlled private document store, only with explicit data-upload authorization; downloadable checkpoint if storage is unavailable. |
| ResumeRenderer | Host's installed document/PDF skill or existing renderer | Produce an honest editable text/Markdown resume; disclose missing PDF rendering instead of inventing a generated file. |
| ApplicationTracker | Private state plus available spreadsheet/database connector | Private local CSV/Markdown projection; state remains canonical. |
| NotificationProvider | Host's chosen notification or messaging tool | Report in the current conversation. External sending requires separate authorization. |
| ReceiptSource | Submission response, exact-job confirmation page, authorized email connector | Preserve visible evidence; no inbox access solely because it is installed. |

Example shape, filled only from actual inspection:

```json
{
  "job_source": {"status": "unverified", "provider": null, "read_tool": null},
  "application_provider": {"status": "unverified", "provider": null, "inspect_tool": null, "submit_tool": null},
  "candidate_store": {"status": "unverified", "provider": null, "write_tool": null},
  "resume_renderer": {"status": "unverified", "provider": null},
  "tracker": {"status": "unverified", "provider": null, "external": false},
  "notifications": {"status": "unverified", "provider": null, "external": false}
}
```

Adapt these fields to real host names; never store credentials. Tool changes require
rechecking the binding. Account/destination changes invalidate affected approvals.
No capability implies permission: an available mail tool does not authorize sending.

Verify signed-in account identity for candidate-specific actions and keep candidates
separate. Use public discovery with supported status/date/geography filters; check
tool documentation and inspect results rather than assuming a filter name works.
Public discovery services receive search criteria, not resumes, private facts,
answers, application codes or secrets. Personalized matching, external tracking
and inbox access require their own correct-candidate binding and authorized scope.

## Operational boundary

Read-only public inspection must not enter candidate data, upload a file, request
a login link, start an assessment or mutate application state. Some form fields
autosave; typing is an external action even before the submit button.

Before any candidate transmission or external mutation, the owner evaluates the
permission contract and persists the current action/attempt. Then invoke the real
host tool. Immediately persist the observed result. This is the skill's guarded
execution path; it is not the legacy Python DryRunApplicationProvider.

Respect each host tool's actual approvals and platform restrictions. A skill cannot
bypass or technically sandbox arbitrary host tools. If an integration is unavailable,
report the exact missing capability and use an honest supported fallback. Do not
ask someone to build an adapter before using a browser they already have.
