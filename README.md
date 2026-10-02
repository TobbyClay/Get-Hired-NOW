# Get-Hired-NOW

**An installable skill that teaches your AI to run your job search.**

Give it to an AI with web/browser and file tools. It asks for your CV and preferences
in conversation, reads your documents, finds real jobs, researches fit and salary,
creates tailored resumes, and handles applications within your chosen permissions.
It uses the AI and tools you already have. No separate AI service, model API key,
Python app or manually written job-data files are required.

## Install the skill

The complete skill is in **[skills/get-hired-now](skills/get-hired-now)**. Its entry
point is **[SKILL.md](skills/get-hired-now/SKILL.md)**.

Use your AI's skill installer with this repository and the path
`skills/get-hired-now`, or download the `get-hired-now.zip` asset from this
repository's Releases tab and install the extracted `get-hired-now` folder in your
host's skill directory. Keep its references, assets and scripts together.

For an AI with file tools but no skill installer, provide the full skill folder
and ask it to read SKILL.md and follow its linked references. Pasting only the short
entrypoint omits the operating instructions. See [setup](docs/setup.md).

## Talk to your AI

After installation:

> Use get-hired-now to set up my job search. Here is my current CV. Ask me about my
> targets, location, compensation and constraints before you start.

Then, for example:

- "Find suitable jobs and explain which ones fit."
- "Evaluate this job posting against my experience."
- "Tailor my resume and write a cover letter for this role."
- "Prepare these applications for my review."
- "Apply to the qualified roles in this batch under my saved authorization."
- "Resume my saved search and reconcile the application receipts."
- "Broaden my search into adjacent roles supported by my experience."
- "Run a round for the next hour, use my saved authorization, and save carryover."

The AI reads your supplied original CV using its document tools and asks only for
missing or ambiguous information. It writes structured state itself; you do not
need to fill in JSON or a terminal questionnaire. Your files and application history
stay in a separate private workspace, never inside the installed skill.

## What the skill directs the AI to do

| Capability | Execution |
| --- | --- |
| Conversational onboarding | Read your CV, collect targets and constraints, record supplied facts and permission choices. |
| Live discovery and research | Use available search, job connectors and official employer pages; verify the actual hiring geography and requirements. |
| Grounded evaluation | Map each requirement to your evidence; distinguish preferences, unknowns and real conflicts. |
| Tailored documents | Use available document tools to create actual role-specific resumes and letters, preserving the original. |
| Applications | Inspect real forms and use available browser/application tools for authorized actions; stop for human gates. |
| Durable tracking | Save explicit state, attempts, artifacts and exact employer receipts; resume without guessing from conversation history. |
| Follow-up | Draft and, only when separately authorized, send through the host's actual connected tools. |

## Run a useful application pipeline

The AI builds a search plan from your evidence and preferences, covers several
role families and sources, and rotates away from stale duplicates. It checks the
official role and form before extensive tailoring, then assigns proportionate
preparation: no packet for a known blocker, a fresh copy using verified content
when pay is unknown, or deeper tailoring when fit and economics justify it.

On hosts with authorized subagents, scouts, fit review, salary research, writing
and form inspection can work in independent slices. Completed roles move to the
submission owner while discovery continues. One owner maintains shared records.
The same workflow works sequentially when subagents are unavailable.

Your application goal is a target unless you explicitly set a cap. The AI continues
useful work within your scope and time limit, saves specific next actions, and
reports actual source/family coverage and blockers. It distinguishes final Submit
from uploads/autosaves, receipts from recruiter replies, and late reconciliation
from newly submitted roles. Measured elapsed and active time stay separate.

Freshness limits, pay floors, preferred lanes, account scope and authorization are
collected from you. No installer's policy is copied into another candidate's search.
See [rounds and carryover](skills/get-hired-now/references/rounds.md) and
[salary research](skills/get-hired-now/references/salary.md).

The AI can perform these operations only when its host supplies the needed tools
and permissions. Without a browser, it prepares the documents and reports that
submission is unavailable. Without a renderer, it provides a usable editable text
resume and discloses the format limit. It never substitutes a simulated application.

## Permissions and evidence

- **OBSERVE:** search, research and evaluate.
- **REVIEW:** also prepare documents; the person approves concrete external actions.
- **AUTONOMOUS:** act within recorded standing authorization and action scope;
  automatic submission must be explicitly enabled.

CAPTCHA/security challenges, human-only assessments, unexpected legal declarations,
missing candidate facts and material requirement conflicts remain human gates in
every mode. Existing valid authorization is respected; the AI does not repeatedly
ask for permission already given. Only observed exact-job employer acceptance counts
as a submitted application.

## State and replaceable integrations

The skill keeps a private `state.json` with candidate facts, permissions, tool
bindings, jobs, artifacts, attempts, receipts and next actions. A single record
owner updates it. An optional checkpoint helper provides atomic writes and revision
checks; native file/transaction tools can replace it.

An optional read-only round-report helper summarizes recorded milestones and exact
receipts without accessing an employer. It keeps duplicate sightings, uncertain
attempts, late receipts and unknown time denominators distinct. Neither helper
authenticates consent or evidence, and neither replaces the AI's host tools.

Job sources, application providers, candidate storage, trackers, document rendering
and notifications are capability interfaces bound to the AI's available tools.
There are no personal accounts, private integration IDs or candidate defaults.

## Documentation and validation

- [Setup and installation](docs/setup.md)
- [Architecture](docs/architecture.md)
- [Customization and integration bindings](docs/customization.md)
- [Safety and approval](docs/safety-and-approval.md)
- [Regression fixtures and behavioral evaluation](docs/evaluations.md)

The repository includes all ten requested regression scenarios, privacy scans,
skill packaging checks and tests for the optional helpers. Automated helper tests
do not prove every AI model or live website behaves correctly. The skill's host
must obey its instructions and its own tool/security boundaries.

## Optional developer material

The `get_hired_now/` Python package, old command-line onboarding and `tools/demo.py`
are retained as a **reference implementation for developers**. They are not needed
to install or use the skill. That CLI has a simulated provider and does not perform
the skill's real browser workflow. The earlier v0.1 framework alone was not the
intended product; the installable AI skill is the primary deliverable from v0.2.

The offline demo tests the optional framework, not the skill's live capabilities.
Do not use its simulated result as evidence of a real application.

MIT licensed. Keep contributions and regression fixtures fictional. Never publish
completed profiles, CVs, receipts or credentials in this repository.
