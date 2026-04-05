# LightRAG Quality Gates

## Purpose
These gates define when a task, stage, or final delivery is acceptable. If a gate cannot run, the blocker must be recorded in `docs/codex/DECISIONS.md`.

## Phase A Bootstrap Gates
The Codex operating model bootstrap is complete when all of the following are true:
- `AGENTS.md` points Codex to `docs/codex/*`
- `docs/codex/TASK_QUEUE.yaml` exists and is the next-task source of truth
- `docs/codex/DECISIONS.md` exists and records the bootstrap decisions
- `docs/codex/CONTRACTS.md` freezes the current public surfaces
- `scripts/quality_gate.py --profile phase-a` exists and runs the baseline checks
- a GitHub Actions workflow exists for baseline quality automation

## Closed-Loop Task Gates
Every task selected from the task queue must satisfy all applicable rules:
- scope is limited to one root-cause problem or one structural target
- validation commands are defined before code changes start
- docs are updated when contracts, decisions, or task status change
- worktree is explainable at the end of the task
- commit and push happen only after validation

## Current Baseline Commands
- Bootstrap Python gate:
  - `python scripts/quality_gate.py --profile python`
- Targeted offline tests inside the bootstrap gate:
  - `python -m pytest tests/test_chunking.py tests/test_write_json_optimization.py -m "not integration"`
- Web UI build:
  - `bun install --cwd lightrag_webui --frozen-lockfile`
  - `bun --cwd lightrag_webui run build`
- Combined Phase A baseline:
  - `python scripts/quality_gate.py --profile phase-a`

## Future Full-Repo Target
These are not yet the bootstrap gate, but they are the direction for later phases:
- `python -m ruff check lightrag tests scripts`
- broader pytest coverage for the touched subsystems
- API smoke coverage for app startup and key routes

## Stage Completion Gates

### Core Refactor Stage
- oversized modules are reduced in responsibility and file size
- duplicated logic is removed or centralized
- touched behavior is covered by focused tests
- migration notes are recorded for any breaking contract change

### Adapter Governance Stage
- storage and model adapters use explicit contracts
- provider-specific branches are reduced
- adapter contract tests exist for touched backends

### API And UI Stage
- API app assembly is separated from route logic
- Web UI primary flows build and remain navigable
- configuration docs match runtime behavior

### Final Release Gate
- CI is green
- the agreed test matrix passes
- no runtime artifacts that should be ignored are committed
- critical module boundaries are understandable without archaeology
- there is no obvious duplicate implementation for the same responsibility
- migration notes, architecture notes, and acceptance notes are present
