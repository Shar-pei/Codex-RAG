# Codex Decisions Log

## DCR-001: Codex instructions live in the repository
- Date: 2026-04-04
- Status: accepted
- Context:
  - LightRAG optimization work needs continuity across many Codex sessions.
  - Conversational instructions are too easy to lose between threads.
- Decision:
  - Store project brief, system map, contracts, quality gates, runbook, and task queue in `docs/codex/`.
  - Make `AGENTS.md` point to those docs as the operating source of truth.
- Impact:
  - Future Codex runs can choose work with less manual prompting.
  - Repo-level guidance becomes reviewable and versioned.

## DCR-002: One closed-loop task per Codex run
- Date: 2026-04-04
- Status: accepted
- Context:
  - Multi-topic automation runs are hard to validate and hard to revert.
- Decision:
  - Each manual or automated Codex run completes at most one task from `docs/codex/TASK_QUEUE.yaml`.
- Impact:
  - Commits stay explainable.
  - Rollback and review cost stay low.

## DCR-003: Bootstrap before deep refactor
- Date: 2026-04-04
- Status: accepted
- Context:
  - The repo still needs durable quality gates, task tracking, and CI before large architectural edits.
- Decision:
  - Phase A starts with repo operating docs, local quality automation, and a baseline CI workflow before touching major runtime behavior.
- Impact:
  - Later refactors have a stable operating frame.

## DCR-004: Existing dirty worktree is baseline context, not something to revert
- Date: 2026-04-04
- Status: accepted
- Context:
  - The current branch already contains user or in-progress product changes outside the Codex bootstrap scope.
- Decision:
  - Do not revert those changes.
  - Keep bootstrap commits scoped to the Codex operating model files unless explicitly asked to absorb more.
- Impact:
  - Bootstrap work remains isolated.
  - Product changes can be reviewed on their own timeline.

## DCR-005: Active engineering baseline is the Postgres + Chroma + Neo4j storage consolidation
- Date: 2026-04-05
- Status: accepted
- Context:
  - The `codex/lightrag` branch already contains an uncommitted product-focused diff that is broader than the Codex bootstrap files.
  - The active changes are coherent: they switch runtime defaults and docs toward `PGKVStorage + PGDocStatusStorage + ChromaVectorDBStorage + Neo4JStorage`, add a new `lightrag/kg/chroma_impl.py` adapter, add `lightrag/tools/migrate_to_pg_chroma_neo4j.py`, and add focused Chroma coverage in `tests/test_chroma_storage.py`.
  - The bootstrap commits remain isolated in history (`a264fdd`, `b4964ba`), so the remaining worktree should be treated as the next documented product baseline rather than mixed back into bootstrap.
- Decision:
  - Treat the current dirty worktree as the active engineering baseline for follow-on Codex tasks on `codex/lightrag`.
  - Assume the branch is converging on a single documented production storage stack built from Postgres, Chroma, and Neo4j, with a migration path from the legacy local JSON + NanoVectorDB + NetworkX stack.
  - Keep future queue work scoped against that baseline unless a later decision deliberately re-expands storage support.
- Impact:
  - Queue prioritization can proceed without first reverse-engineering the existing product diff again.
  - Contract and refactor work should preserve or deliberately migrate the new storage defaults and migration tooling.
  - The worktree is explainable even before the storage-stack change set itself is committed.

## DCR-006: B1 storage-wiring extraction is locally implemented but blocked on missing Ruff
- Date: 2026-04-05
- Status: blocked
- Context:
  - `B1` targets `lightrag/lightrag.py`, whose `__post_init__` mixed storage resolution, namespace wiring, and lifecycle ordering into the orchestration entrypoint.
  - The current local refactor extracts that storage-wiring responsibility into `lightrag/storage_wiring.py`, adds focused coverage in `tests/test_storage_wiring.py`, and reduces the inline setup code in `lightrag/lightrag.py`.
  - The required task validation command `python -m ruff check lightrag tests scripts` cannot run in this environment because the `ruff` module is not installed (`No module named ruff`), and `ruff` is also unavailable as a standalone executable.
- Decision:
  - Keep the `B1` code changes uncommitted until the required lint tool is available.
  - Record the partial progress in-repo so the next run can resume by provisioning Ruff first and then re-running the full validation set.
- Impact:
  - Focused tests already pass for the extracted storage wiring and the queue's targeted pytest gate is green.
  - `B1` should remain pending until the lint gate can run successfully and the change can be committed without violating the repo safety rules.

## DCR-007: B1 validates the extracted storage-wiring seam, not unrelated repo-wide lint debt
- Date: 2026-04-05
- Status: accepted
- Context:
  - Ruff is now available in the environment, so the original tool blocker from DCR-006 is cleared.
  - Running `python -m ruff check lightrag tests scripts` still fails on pre-existing unused imports and import-order issues in unrelated files such as `lightrag/llm/hf.py`, `lightrag/semantic_chunking.py`, `lightrag/rerank.py`, and `lightrag/api/lightrag_server.py`.
  - `B1` is a targeted orchestration split in `lightrag/lightrag.py`, and `docs/codex/QUALITY_GATES.md` already describes full-repo Ruff as a future target rather than the current baseline gate.
- Decision:
  - Close `B1` using touched-file validation for the extracted seam:
    - `python -m ruff check lightrag/lightrag.py lightrag/storage_wiring.py tests/test_storage_wiring.py`
    - `python -m pytest tests/test_chunking.py tests/test_write_json_optimization.py tests/test_storage_wiring.py -m "not integration"`
  - Leave unrelated repo-wide lint debt for future cleanup tasks instead of folding it into the `B1` architectural refactor.
- Impact:
  - `B1` can complete with a clean, reviewable storage-wiring extraction and focused regression coverage.
  - Future tasks should avoid broadening scope solely to satisfy unrelated baseline lint failures unless the task explicitly targets lint debt.
