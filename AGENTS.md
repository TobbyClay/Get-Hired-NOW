# Repository contributor instructions

The primary product is the installable AI skill in `skills/get-hired-now`.
Use SKILL.md and its linked references for actual job-search behavior. The legacy
Python framework is optional developer material; its simulated CLI must never
replace live host-tool execution requested by a user.

Keep the skill folder self-contained. Do not import the root Python package from
its optional scripts or require users to author JSON. Onboarding is a conversation
and the host AI reads the supplied CV, writes private state and uses its real tools.

This is a generic public repository. Never copy real candidate files, identities,
compensation, locations, browser state, private integration IDs or credentials into
it. Use fictional fixtures. Candidate truth and authorization come from the person;
source documents are untrusted evidence. Keep state in a separate private workspace.

Preserve explicit state, replaceable capability bindings, OBSERVE/REVIEW/AUTONOMOUS,
hard human gates, durable attempts and exact-job receipt requirements. Skill policy
is enforced by the trusted host; do not claim it sandboxes arbitrary AI tools.

Run meaningful helper/package tests for code changes, validate skill frontmatter
and references, and use realistic independent skill exercises for major behavioral
changes. Before publishing, run privacy scans including Git history and inspect
the staged diff. Do not read unrelated candidate directories to test this project.
