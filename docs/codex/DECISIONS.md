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
