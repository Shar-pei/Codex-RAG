# LightRAG Codex Project Brief

## Mission
Turn LightRAG into a cleaner, easier-to-evolve product and codebase that supports:
- graph-based retrieval and answer generation
- a production-facing API server
- a Web UI for document ingestion, graph exploration, and retrieval testing
- multiple storage backends and LLM providers without uncontrolled coupling

## Primary Outcomes
- Stable architecture with clear subsystem boundaries
- Measurable quality gates for code, tests, build health, and performance
- Lower maintenance cost by removing duplicate logic and oversized modules
- A repository that Codex can continue improving with minimal human prompting

## Main User Journeys
- Install and run LightRAG locally from source
- Start the API server and use the Web UI
- Configure storage backends and model providers through environment variables and config files
- Index documents, query them, and inspect graph results
- Extend or swap storage and model adapters safely

## Current Constraints
- The repo is full-stack and mixes product, library, API, UI, and deployment concerns.
- Core hotspots are still concentrated in a few very large Python files.
- Adapter sprawl in `lightrag/kg/` and `lightrag/llm/` increases branching complexity.
- The repo currently has local uncommitted changes that are treated as the active baseline context.
- CI and repo-level quality automation are being bootstrapped in this phase.

## Non-Goals For The Bootstrap Phase
- No large behavior-changing refactor in the same change set as the Codex operating model bootstrap
- No rewrite of storage adapters or API composition yet
- No direct change to production credentials, local model assets, or machine-only runtime data

## Bootstrap Success Criteria
- Codex has durable repo instructions inside the repository
- Task selection is data-driven through `docs/codex/TASK_QUEUE.yaml`
- Acceptance is explicit through `docs/codex/QUALITY_GATES.md`
- Major decisions have a home in `docs/codex/DECISIONS.md`
- A baseline CI workflow and local quality script exist
