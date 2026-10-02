# Customize the skill

Edit the self-contained skill in `skills/get-hired-now`. Keep essential routing and
rules in SKILL.md and task-specific procedures in linked references. Preserve the
supplied user's facts, authorization, original CV and evidence requirements.

## Tools and integrations

The AI reads its actual tool catalog, follows applicable tool/skill documentation,
and records a capability binding. See the [integration contract](../skills/get-hired-now/references/integrations.md).
An installed job connector can supply discovery. Public search and employer pages
can replace it. Browser tools can inspect/fill real forms. Native document tools
can render resumes. Available spreadsheet tools can maintain an authorized tracker.

No provider or model is mandatory. Do not hard-code an account, sheet ID, browser
profile, personal directory or credential. Do not require a new developer adapter
when existing host tools already perform the operation. Account ambiguity needs
clarification; mere tool availability does not grant external-write permission.

## Candidate preferences

The onboarding conversation collects roles, geography, salary policy, arrangement,
constraints and writing preferences. Put actual values in private state, not SKILL.md.
Updates come from the person with provenance. Unpublished employer pay is unknown,
not an automatic rejection; use the person's undisclosed-pay policy and appropriate
preparation investment.

Configure source/family coverage, original-publication policy, time budgets and goals
with provenance in the private search policy. No numeric application goal, posting-
age maximum, market, pay floor or model roster is imposed on every candidate.
Distinguish a goal from an explicit cap and use the [round contract](../skills/get-hired-now/references/rounds.md)
for streaming, early form checks, carryover and measurements. Compensation research
uses the [salary contract](../skills/get-hired-now/references/salary.md).

## Agent hosts

Follow the portable team contract. Use one AI sequentially or supported, authorized
subagents. Keep one owner for exact-job submission and one for shared state. The
skill does not register vendor-specific models or claim agent launch syntax common
to every host. Use the host's actual mechanisms.

## Optional code

The checkpoint helper is a replaceable durability utility. The legacy Python
framework offers developer examples of deterministic gating, state reservations
and adapter protocols, but using the skill does not require wiring that framework
into the AI. Rich real-world execution is directed through the host's own tools.

When changing behavior, run regression/helper/package tests and perform a realistic
skill exercise with fictional candidate evidence. Report what the AI actually did;
do not label mock-provider success as a live integration test.
