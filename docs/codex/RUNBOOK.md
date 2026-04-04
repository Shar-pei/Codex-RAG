# Codex Runbook

## Manual Run Prompt
Use this prompt to continue work in a new Codex thread:

`Please follow AGENTS.md and docs/codex, continue the highest-priority task in docs/codex/TASK_QUEUE.yaml, perform root-cause analysis first, then make the smallest complete refactor, validate it, update the Codex docs, and push the current codex branch.`

## Short New-Thread Prompt
If you want the shortest possible restart instruction, use:

`In D:\MyCodeX\MyRAG\LightRAG, read AGENTS.md and docs/codex, inspect git status and the task queue, then continue the highest-priority unblocked task, validate it, and push the current codex branch.`

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

## Interruption Recovery

### If Codex quota runs out
1. Open a new thread in `D:\MyCodeX\MyRAG\LightRAG`.
2. Re-read `AGENTS.md` and all files in `docs/codex/`.
3. Run:
   - `git branch --show-current`
   - `git status --short --branch`
   - `git log --oneline -5`
4. Read `docs/codex/TASK_QUEUE.yaml` and `docs/codex/DECISIONS.md`.
5. Continue the highest-priority unblocked task, or document the blocker first if the worktree is ambiguous.

### If the computer was shut down
1. Reopen the repo in a new thread.
2. Assume only committed and pushed work is guaranteed durable.
3. Check whether there are local uncommitted changes before doing anything else.
4. If local changes exist, understand them before editing.
5. If the worktree is clean, continue from the queue normally.

### Recovery Goal
Every run should leave enough repo state behind that a brand-new thread can continue without needing the old chat transcript.
