# Skill architecture

```text
User's conversation + explicitly supplied original CV
                    |
               AI loads SKILL.md
                    |
        onboard -> discover -> evaluate -> research
                    |
          tailor actual files -> review/authorize
                    |
       real host browser/application tools -> receipt
                    |
         private state + tracking + authorized follow-up
```

The user's AI is the executor. SKILL.md supplies routing and operating rules;
references provide task-specific procedures. No model SDK, subprocess agent server
or custom web adapter is required. Real capabilities come from the host's tools.

## Explicit state

The canonical state is a private JSON checkpoint described in the skill's
[state contract](../skills/get-hired-now/references/state.md). It stores supplied
candidate evidence, permissions, actual tool bindings, exact requisitions,
evaluations, documents, attempts, receipts and next actions. Conversation history
is not a substitute. One record owner writes; workers return bounded evidence.

The optional self-contained checkpoint helper provides lock/revision checks, atomic
replacement and basic invariants such as preserving receipts and requiring evidence
for acceptance. It does not perform search or submission. It does not authenticate
consent or sandbox an AI with arbitrary filesystem access.

## Replaceable integrations

The skill's interfaces bind discovery, browser/application operations, candidate
storage, document production, trackers and notifications to actually available
tools. A connector, a browser or a native file tool can satisfy an interface when
its real capabilities and permissions match. Binding records contain no tokens.
Unavailable capabilities are disclosed; a simulation is never a live fallback.

## Permission boundary

The AI checks persisted scope and hard gates before every external action, records
the attempt, executes through the host's actual tool and records the result. The
host's own approvals and security restrictions remain authoritative. Instructions
are an operating contract, not a technical sandbox around arbitrary host tools.

## Role decomposition

The portable [team contract](../skills/get-hired-now/references/team.md) defines
lead, scouts, ATS extraction, fit, salary, writing, form, skepticism and records
responsibilities. One AI can perform them sequentially. Hosts with authorized
subagents can delegate independent bounded work without sharing submission ownership.

## Legacy reference engine

`get_hired_now/` retains the v0.1 SQLite/permission implementation and local
simulation as optional developer material. Its CLI, candidate schema and simulated
provider are not the skill's normal execution path. The skill checkpoint is a
separate format; do not silently merge the two or run the simulation to fulfill
a real application request.
