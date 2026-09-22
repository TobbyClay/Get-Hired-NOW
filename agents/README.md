# Agent responsibilities

These are host-independent role contracts. They do not start agents or select an
LLM provider. The Python core supplies state, deterministic gates and adapters;
a trusted host can implement model-assisted discovery, research and writing.

Every task receives an exact job/batch boundary, the current persisted snapshot,
the evidence needed for that task, and a named owner for its output. Use the least
candidate data needed. The host keeps human approval and settings tools separate
from model-accessible tools. One owner reserves each submission and shared record.

| Role | Scope |
| --- | --- |
| [Discovery](discovery.md) | Read public sources; preserve literal requirements and identities |
| [Evaluator](evaluator.md) | Map requirements to supported candidate evidence |
| [Researcher](researcher.md) | Resolve employer, role, compensation and arrangement uncertainty |
| [Resume tailor](resume-tailor.md) | Prepare truthful local material from supplied evidence |
| [Application](application.md) | Inspect forms, build packets, request guarded execution |
| [Tracker](tracker.md) | Reconcile attempts and exact receipts |
| [Outreach](outreach.md) | Draft follow-up; send only through a separately authorized extension |
