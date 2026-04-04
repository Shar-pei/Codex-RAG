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
