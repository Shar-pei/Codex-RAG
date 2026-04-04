# Repository Guidelines

LightRAG is a graph-based Retrieval-Augmented Generation system with three major surfaces:
- `lightrag/`: core Python package and retrieval pipeline
- `lightrag/api/`: FastAPI service and API composition layer
- `lightrag_webui/`: Bun + React Web UI

This repository is in active root-cause optimization. Treat it as an evolving product plus platform, not as a patch-only maintenance branch.

## Source Of Truth
- Read this file first.
- Then read every file in `docs/codex/` before choosing work.
- `docs/codex/TASK_QUEUE.yaml` is the single source of truth for what to do next.
- `docs/codex/QUALITY_GATES.md` is the single source of truth for acceptance.
- `docs/codex/DECISIONS.md` is the single source of truth for major refactor decisions and migration notes.

## Branch And Git Workflow
- Work only on `codex/*` branches.
- Never commit directly to `main`.
- Before editing, check the current branch with `git branch --show-current`.
- Before choosing work, check `git status --short --branch`.
- Each run should complete at most one closed-loop task from `docs/codex/TASK_QUEUE.yaml`.
- After finishing a task, run the required validation commands, update the Codex docs, commit only the intended files, and push the current branch.
- Never rewrite history or delete branches unless explicitly requested.

## Working Principles
- Optimize for root-cause fixes, not surface patches.
- Prefer structural simplification over local workarounds.
- Keep modules single-purpose and reduce hidden coupling.
- Preserve user changes you did not make.
- Do not revert unrelated local edits.
- Document breaking changes, migrations, and architecture shifts in `docs/codex/DECISIONS.md`.
- If a task definition is incomplete, improve the task docs first instead of making blind code changes.

## Standard Codex Loop
1. Read `AGENTS.md` and every file in `docs/codex/`.
2. Inspect branch, remote tracking, and worktree status.
3. Select the highest-priority task in `docs/codex/TASK_QUEUE.yaml` that is not blocked.
4. Perform root-cause analysis before editing code.
5. Make the smallest complete structural change that closes the task.
6. Run the task's validation commands.
7. Update `docs/codex/TASK_QUEUE.yaml`, `docs/codex/DECISIONS.md`, and any impacted contract docs.
8. Commit and push the current `codex/*` branch.

## Project Structure
- `lightrag/lightrag.py` and `lightrag/operate.py` are current refactor hotspots due to size and responsibility overlap.
- `lightrag/kg/` and `lightrag/llm/` contain adapter implementations that should converge on explicit contracts over time.
- `lightrag/api/lightrag_server.py` is the main API composition hotspot.
- `tests/` contains the main pytest suite. Root-level `test_*.py` files are legacy helpers and should be rationalized over time.
- `docs/` contains product and deployment documentation.
- `scripts/` is reserved for repo maintenance, validation, and automation helpers.

## Build And Validation Commands
- Python environment: `pip install -e .` or `pip install -e ".[api]"`
- API server: `lightrag-server`
- Python tests: `python -m pytest tests`
- Bootstrap Python gate: `python scripts/quality_gate.py --profile python`
- Future full-repo lint target: `python -m ruff check lightrag tests scripts`
- Web UI install: `bun install --cwd lightrag_webui --frozen-lockfile`
- Web UI build: `bun run build --cwd lightrag_webui`
- Phase A quality baseline: `python scripts/quality_gate.py --profile phase-a`

## Editing Constraints
- Use ASCII unless a file already depends on Unicode content.
- Use `apply_patch` for manual edits.
- Add comments only when they explain non-obvious logic.
- Prefer targeted edits that clarify architecture boundaries.
- Never add temporary compatibility layers without documenting removal criteria.

## Safety Rules
- Do not commit secrets, `.env`, local logs, or private model assets.
- Do not change production credentials or machine-specific paths unless the task explicitly requires it.
- Do not bypass validation before commit.
- Do not perform destructive git commands such as `git reset --hard` or `git checkout --` unless explicitly requested.

## Automation Rules
- Automation runs must behave exactly like manual runs.
- One automation run should complete one task, not a grab bag of fixes.
- Automation may perform breaking refactors only if it also updates `docs/codex/DECISIONS.md` and the affected contract docs.
- If a required tool is missing or validation cannot run, record the blocker in `docs/codex/DECISIONS.md` and stop after leaving the repo in a clean, explainable state.
