# Codex Runbook

## Manual Run Prompt
Use this prompt to continue work in a new Codex thread:

`Please follow AGENTS.md and docs/codex, continue the highest-priority task in docs/codex/TASK_QUEUE.yaml, perform root-cause analysis first, then make the smallest complete refactor, validate it, update the Codex docs, and push the current codex branch.`

## Standard Run Steps
1. Confirm the workdir is `D:\MyCodeX\MyRAG\LightRAG`.
2. Read `AGENTS.md` and every file in `docs/codex/`.
3. Run:
   - `git branch --show-current`
   - `git status --short --branch`
   - `git remote -v`
4. Select the highest-priority pending task with all dependencies satisfied.
5. Perform root-cause analysis before making edits.
6. Make the smallest complete change that closes the task.
7. Run the task's validation commands.
8. Update:
   - `docs/codex/TASK_QUEUE.yaml`
   - `docs/codex/DECISIONS.md`
   - `docs/codex/CONTRACTS.md` when external surfaces change
9. Commit only the intended files.
10. Push the current `codex/*` branch.

## What Automation May Do
- refactor code
- split modules
- tighten contracts
- add or improve tests
- update docs and task metadata
- commit and push the current `codex/*` branch

## What Automation Must Not Do
- push directly to `main`
- rewrite history
- delete branches
- commit secrets or local machine artifacts
- skip validation before commit
- perform breaking refactors without updating `DECISIONS.md` and `CONTRACTS.md`

## Handling High-Risk Work
- High-risk work is allowed when the task queue calls for it.
- The run must record:
  - why the change is necessary
  - what external contract changed
  - what migration is required
  - what validation was run

## Blocking Conditions
Stop and document the blocker if:
- required tools are missing
- the task definition is too vague to execute safely
- unrelated local changes make the intended edit ambiguous
- validation cannot run and the reason is not obvious
