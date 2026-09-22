# Install and use the AI skill

## Installation

Install the self-contained folder `skills/get-hired-now`, not the Python package.
Use the host's normal skill installer with this GitHub repository and that folder
path. Alternatively, download `get-hired-now.zip` from Releases, extract it, and
place the resulting `get-hired-now` folder in the host's supported skill directory.

The folder contains SKILL.md, progressively loaded references, a blank state asset,
optional checkpoint script, UI metadata and license in the release bundle. Keep
them together. There is no requirement to install Python or run a service.

A host without native skill discovery can read the provided SKILL.md and linked
references through file tools. This loads the instructions for that session; it
does not automatically create a permanent installation. Follow the host's own
documentation for permanent discovery rather than assuming a universal slash command.

## First conversation

Ask: "Use get-hired-now to set up my job search," and attach your current original
CV or give the AI its readable path. The AI reads it, extracts evidenced facts and
asks about target roles, location/authorization, salary expectations and units,
constraints, availability and writing preferences. It asks about genuine ambiguity
instead of requiring you to transcribe your resume or edit configuration files.

Choose a private candidate workspace outside the skill and outside Git. The AI
persists only supplied facts and sources, permissions and subsequent work there.
Keep each candidate in a separate workspace. Do not upload candidate data to a
remote store unless you have authorized that destination.

Default mode is REVIEW. OBSERVE limits work to research/evaluation. AUTONOMOUS needs
explicit action categories, scope and an automatic-submission choice. The AI records
your actual instruction and respects it on later turns until changed or expired.

## Normal requests

"Find jobs matching my profile" uses the host's actual available web/job tools.
"Evaluate this URL" evaluates the live or supplied posting without automatically
rewriting your CV. "Prepare these roles" creates actual documents using available
document tools. "Apply to these qualified roles" executes through available browser
or application tools once authorized. State and receipt evidence persist after
each material action so a later session can resume.

No live web tool means no live discovery. No submission tool means no submission.
The AI must state the specific missing capability and continue useful supported
work. You should not be asked to build a custom adapter when an available browser
already supports the operation.

## Optional local helper

The AI may use `scripts/checkpoint.py` inside the installed skill for atomic state
writes. It needs Python 3.10+ only for that optional helper. The AI prepares its
input and runs it; the person does not need to use a terminal. Native durable file
tools can replace it. Do not confuse this helper with the repository's separate
legacy Python CLI, which has a simulated application provider.

Private state and CV files are plaintext unless the chosen host/storage encrypts
them. Use a private destination and suitable OS/storage access controls.
