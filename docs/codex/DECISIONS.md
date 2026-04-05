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

## DCR-008: Push of the validated B1 commit is blocked by outbound GitHub connectivity
- Date: 2026-04-05
- Status: blocked
- Context:
  - `B1` has been validated locally and committed as `67fc1ce` on `codex/lightrag`.
  - Two consecutive push attempts to `origin` failed after commit creation:
    - `Recv failure: Connection was reset`
    - `Failed to connect to github.com port 443 after 21101 ms`
- Decision:
  - Leave the validated commit in local history and stop without rewriting it.
  - Resume by retrying `git push origin codex/lightrag` once outbound GitHub connectivity is available again.
- Impact:
  - The repository is left in a recoverable state with one local commit ahead of `origin/codex/lightrag`.
  - The next run does not need to re-implement `B1`; it only needs to push the existing commit if the network path is healthy.

## DCR-009: `operate.py` is now a compatibility facade over dedicated indexing and retrieval modules
- Date: 2026-04-05
- Status: accepted
- Context:
  - `lightrag/operate.py` had accumulated chunking, extraction, graph rebuild, retrieval, and query-context assembly in one large module.
  - The strongest seam is between indexing work (`chunking`, extraction, graph rebuild, merge) and retrieval work (`kg_query`, `naive_query`, query-context helpers).
  - Existing callers such as `lightrag.lightrag`, `lightrag.api.lightrag_server`, and tests still import symbols from `lightrag.operate`.
- Decision:
  - Move indexing concerns into `lightrag/indexing.py`.
  - Move retrieval concerns into `lightrag/retrieval.py`.
  - Keep `lightrag/operate.py` as a thin compatibility facade that re-exports the public functions from those new modules.
  - Point `lightrag.lightrag` directly at `lightrag.indexing` and `lightrag.retrieval` so the new boundaries are authoritative internally.
- Impact:
  - Retrieval and indexing now live in separate modules without breaking the existing `lightrag.operate` import surface.
  - Future refactors can simplify indexing and retrieval independently instead of continuing to grow a single hotspot module.

## DCR-010: Outbound GitHub connectivity recovered and the queued B1 commit was pushed
- Date: 2026-04-05
- Status: accepted
- Context:
  - DCR-008 recorded a transient transport failure while pushing `67fc1ce` to `origin`.
  - A later retry of `git push origin codex/lightrag` succeeded from the same branch and remote.
- Decision:
  - Treat DCR-008 as a historical transport incident, not an active blocker.
  - Continue follow-on task work on top of the now-pushed `codex/lightrag` branch tip.
- Impact:
  - `origin/codex/lightrag` now includes the validated B1 storage-wiring extraction.
  - Subsequent runs can proceed directly from the task queue instead of retrying the old push step.

## DCR-011: C1 standardizes workspace resolution as the first shared adapter contract
- Date: 2026-04-05
- Status: accepted
- Context:
  - The active storage baseline uses PostgreSQL, Chroma, and Neo4j adapters, but each backend had drifted into its own workspace precedence rules and normalization code.
  - PostgreSQL repeated the same `db.workspace -> self.workspace -> "default"` logic in four separate storage classes.
  - Chroma resolved its effective workspace separately from `self.workspace`, which risked logging and metadata disagreeing about which workspace was active when environment overrides were used.
  - Neo4j used the same conceptual override rule as Chroma but with its own inline implementation and a different default (`"base"`).
- Decision:
  - Introduce `lightrag/kg/storage_contracts.py` with a shared `resolve_storage_workspace(...)` helper that returns the first non-empty trimmed workspace candidate.
  - Rewire PostgreSQL, Chroma, and Neo4j to express their precedence chains through that helper instead of duplicating backend-local normalization logic.
  - Treat workspace resolution as the explicit `C1` contract boundary for the current storage refactor pass rather than broadening this run into capability or error-model unification.
- Impact:
  - Workspace precedence is now documented once, tested once, and reused across the active storage adapters.
  - Chroma now keeps the resolved workspace on `self.workspace`, which makes its collection metadata, logs, and adapter state agree when provider overrides are present.
  - Validation for `C1` stays scoped to the touched adapter seam because repo-wide Ruff still includes unrelated baseline lint debt outside this task.

## DCR-012: D1 keeps `lightrag_server.py` as the app factory and moves route composition into a registrar module
- Date: 2026-04-05
- Status: accepted
- Context:
  - `lightrag/api/lightrag_server.py` had grown into a 1300+ line hotspot that mixed startup validation, LightRAG construction, route inclusion, auth endpoints, health reporting, and static asset mounting in one function.
  - The narrowest clean seam was the route composition block after `create_app()` finished building the FastAPI instance and runtime dependencies.
  - Import-time auth/config side effects in the older API modules make broad restructuring risky without a separate config-bootstrap task.
- Decision:
  - Keep `create_app()` and lifecycle wiring in `lightrag/api/lightrag_server.py`.
  - Extract route assembly, auth/status endpoints, health route registration, Swagger/WebUI mounts, and related helpers into `lightrag/api/route_registry.py`.
  - Pass the auth handler and runtime context into the registrar explicitly so route composition depends on injected runtime state instead of hidden module globals.
- Impact:
  - The app factory and route registration now live in separate modules without changing externally visible route paths.
  - Auth and route dependencies are more explicit at the composition boundary, and focused tests can validate route wiring without booting the full server lifecycle.
  - Validation for `D1` stays scoped to the touched API seam because repo-wide Ruff still reports unrelated baseline lint debt in modules such as `lightrag/llm/hf.py`, `lightrag/llm/my_hf.py`, `lightrag/rerank.py`, and `lightrag/semantic_chunking.py`.

## DCR-013: Push of the validated D1 commit is blocked by outbound GitHub connectivity
- Date: 2026-04-05
- Status: blocked
- Context:
  - `D1` was validated locally and committed as `51802a7` on `codex/lightrag`.
  - Two consecutive push attempts to `origin` failed after commit creation:
    - `Recv failure: Connection was reset`
    - `Failed to connect to github.com port 443 after 22111 ms`
- Decision:
  - Leave the validated commit in local history without rewriting it.
  - Stop after documenting the transport blocker so the next run can resume by retrying `git push origin codex/lightrag` before moving on to `D2`.
- Impact:
  - The branch is locally ahead of `origin/codex/lightrag` by the validated `D1` commit.
  - The next run should treat push recovery as the immediate unblock step even though the queue's next code task is `D2`.

## DCR-014: D2 reduces the Web UI shell to one shared tab registry and one tab owner
- Date: 2026-04-05
- Status: accepted
- Context:
  - `lightrag_webui/src/App.tsx` duplicated the primary tab list while also letting Radix Tabs keep its own internal selected value via `defaultValue`.
  - A separate `TabVisibility` context and `TabContent` helper existed even though all four tabs were intentionally kept mounted, and `TabVisibilityProvider` forced every tab to `true` on each tab change.
  - `ApiSite` depended on that redundant visibility layer just to hide an iframe that Radix already hides through tab state.
- Decision:
  - Introduce a shared tab registry in `lightrag_webui/src/lib/appTabs.ts` to document the four primary user journeys in one place.
  - Make the persisted `currentTab` value in `useSettingsStore` the authoritative tab owner by wiring Radix Tabs as a controlled component.
  - Remove the unused `TabVisibility` context and `TabContent` wrapper, and let the force-mounted Radix tab shell preserve heavyweight tab content such as the API docs iframe.
  - Correct the documented Web UI build command to `bun --cwd lightrag_webui run build`, which matches Bun's CLI parsing in this environment.
- Impact:
  - The documents, knowledge graph, retrieval, and API journeys are now defined once and rendered consistently by both the header and the content shell.
  - The Web UI keeps preserved tab content without parallel visibility state or duplicate provider ownership.
  - Future UI simplification can extend the shared registry instead of copying tab definitions across files.

## DCR-015: Push of the validated D2 commit is currently timing out against origin
- Date: 2026-04-05
- Status: blocked
- Context:
  - `D2` was validated locally and committed as `3941041` on `codex/lightrag`.
  - Two direct push attempts from `D:\MyCodeX\MyRAG\LightRAG` did not return a transport result before the local timeout window expired:
    - `git push origin codex/lightrag` timed out after about 120 seconds
    - `git push --porcelain origin codex/lightrag` timed out after about 300 seconds
  - After those attempts, `git status --short --branch` still reports `codex/lightrag...origin/codex/lightrag [ahead 2]`.
- Decision:
  - Keep the validated `D2` commit in local history and stop without rewriting branch history.
  - Resume by retrying `git push origin codex/lightrag` once outbound GitHub connectivity returns a definite success or failure instead of hanging.
- Impact:
  - The repository is left in a recoverable state with the D2 Web UI simplification committed locally but not confirmed on `origin`.
  - The next run should treat push recovery as the immediate unblock step before taking the next queued task (`E1`).
  - Additional retries later on 2026-04-05 still failed before any remote update:
    - `git push origin codex/lightrag` -> `Recv failure: Connection was reset`
    - `git push --porcelain origin codex/lightrag` -> `Recv failure: Connection was reset`
  - The branch now remains `ahead 3`, so `E1` should not start until the queued local commits are durable on `origin`.
  - Root-cause checks in a later continuation show the failure happens before auth or branch negotiation:
    - `git ls-remote --heads origin` -> `Failed to connect to github.com port 443 after 21113 ms: Could not connect to server`
    - `git remote show origin` -> `Recv failure: Connection was reset`
    - `git push --porcelain origin codex/lightrag` -> `Failed to connect to github.com port 443 after 21135 ms: Could not connect to server`
  - `credential.helper` is still `manager`, so the present blocker is outbound HTTPS connectivity to GitHub rather than missing local credentials.
  - Additional transport checks in a later continuation narrow the fallback story:
    - `Test-NetConnection github.com -Port 443` -> `TcpTestSucceeded : False`
    - `Test-NetConnection github.com -Port 22` -> `TcpTestSucceeded : True`
    - `ssh -i ~/.ssh/id_rsa -o IdentitiesOnly=yes -T git@github.com` -> `Permission denied (publickey)`
  - The local machine can reach GitHub over SSH, but the existing `~/.ssh/id_rsa` key is not authorized for the `Shar-pei` account, so there is still no viable push path from this environment.
  - The repo remote has now been switched from HTTPS to SSH:
    - `remote.origin.url` -> `git@github.com:Shar-pei/Codex-RAG.git`
    - `git push --porcelain origin codex/lightrag` still fails immediately with `Permission denied (publickey)`
  - The remaining unblock step is no longer transport selection; it is authorizing the existing public key on GitHub or loading a different authorized SSH identity.

## DCR-016: E1 closes Phase A with generated benchmark artifacts and an acceptance report
- Date: 2026-04-05
- Status: accepted
- Context:
  - `scripts/quality_gate.py --profile phase-a` already executed the baseline validation commands, but it behaved like a fire-and-forget runner.
  - `E1` required durable benchmark commands, comparable performance results across iterations, and final acceptance notes in-repo.
  - Without generated artifacts, successful validation runs left no stable output for later comparisons or release sign-off.
- Decision:
  - Extend `scripts/quality_gate.py` so the `phase-a` profile times each existing baseline command instead of introducing a separate benchmark command surface.
  - Write the latest timed result to `docs/codex/benchmarks/phase_a_latest.json`, append historical runs to `docs/codex/benchmarks/phase_a_history.jsonl`, and regenerate `docs/codex/ACCEPTANCE_REPORT.md` from the same data.
  - Keep the `python` and `frontend` profiles unchanged so the narrowest new behavior only affects the final acceptance profile.
- Impact:
  - Phase A validation now leaves behind a reproducible acceptance note plus machine-readable benchmark history.
  - Later runs can compare command timings directly from the repository instead of reconstructing them from terminal logs.
  - `E1` can close without widening scope beyond the already accepted Phase A validation commands.

## DCR-017: F1 freezes the supported runtime storage stack to Postgres + Chroma + Neo4j
- Date: 2026-04-05
- Status: accepted
- Context:
  - The active branch baseline had already moved runtime defaults, deployment assets, and docs toward `PGKVStorage + PGDocStatusStorage + ChromaVectorDBStorage + Neo4JStorage`, but the task queue did not yet describe that work as a first-class task.
  - Storage verification still used open-ended registries even though the intended production contract had narrowed, which left conflicting defaults and stale migration guidance in tests and translated docs.
  - `lightrag/kg/postgres_impl.py` still contained optional pgvector bootstrap behavior that should only run when PostgreSQL is actually selected as the vector backend.
- Decision:
  - Treat the storage-stack convergence as its own closed-loop task (`F1`) and record it in `docs/codex/TASK_QUEUE.yaml`.
  - Freeze the supported runtime storage selection contract to `PGKVStorage`, `PGDocStatusStorage`, `ChromaVectorDBStorage`, and `Neo4JStorage`.
  - Keep legacy adapters in the repository for migration and maintenance tooling, but remove them from the documented runtime selection surface and from storage verification.
  - Make `PostgreSQLDB` manage pgvector-specific tables, extensions, and migrations only when `LIGHTRAG_VECTOR_STORAGE=PGVectorStorage`, so the default Chroma path does not bootstrap unused PostgreSQL vector artifacts.
- Impact:
  - Runtime defaults, deployment examples, and storage verification now describe one explicit production stack instead of several conflicting defaults.
  - The new migration tool `python -m lightrag.tools.migrate_to_pg_chroma_neo4j` becomes the deliberate bridge from the legacy local stack into the supported runtime contract.
  - Focused regression tests now protect the default stack contract and the PostgreSQL table-management boundary without widening the task into unrelated adapter cleanup.

## DCR-018: G1 centralizes pipmaster fallback for the supported runtime surface
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `F1`, the only remaining local worktree artifact was an untracked repo-root `pipmaster.py` shim.
  - The supported runtime surface still imported `pipmaster` independently in `lightrag/api/lightrag_server.py`, `lightrag/api/run_with_gunicorn.py`, `lightrag/kg/chroma_impl.py`, `lightrag/kg/neo4j_impl.py`, and `lightrag/kg/postgres_impl.py`.
  - Chroma already carried an inline fallback loader while the other active modules hard-imported `pipmaster`, so the import boundary for optional dependency bootstrap had drifted across the very modules that define the supported runtime stack.
- Decision:
  - Introduce `lightrag/_pipmaster.py` as the shared helper that either imports the installed `pipmaster` package or falls back to a minimal local implementation.
  - Expose `import_or_install(...)` from that helper so supported runtime modules can avoid repeating the `is_installed -> install -> import` sequence and stop triggering module-order lint exceptions while doing dynamic bootstrap.
  - Rewire only the supported runtime surface to use this helper in `G1`; leave broader legacy-adapter cleanup for a later queue item instead of widening scope here.
- Impact:
  - The active API and storage modules now share one dependency-bootstrap boundary instead of duplicating `pipmaster` import logic.
  - Source checkouts no longer need a tracked repo-root shim to explain how the supported runtime surface handles a missing `pipmaster` package.
  - Focused tests in `tests/test_pipmaster_fallback.py` now lock the helper behavior for both installed and fallback paths.

## DCR-019: H1 treats the repo-root pipmaster shim as a local artifact, not pending product work
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `G1`, `git status --short --branch` still reported a single untracked file: `pipmaster.py` at the repository root.
  - The supported runtime surface now uses `lightrag/_pipmaster.py`, so the root-level shim is no longer part of the product path Codex just validated.
  - Deleting an untracked local file would be a destructive workspace action, while leaving it unignored would keep every follow-on thread starting from a misleading dirty worktree.
- Decision:
  - Add an explicit ignore rule for the repo-root `pipmaster.py` shim.
  - Treat that file as a local runtime-recovery artifact rather than a pending source change that belongs in version control.
- Impact:
  - Standard `git status` output returns to a clean baseline after `G1` without deleting anything from the user's machine.
  - Future Codex runs can trust that a dirty worktree signals real pending work instead of a leftover local shim.

## DCR-020: I1 moves document status and pagination schemas behind a dedicated API-model seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - `lightrag/api/routers/document_routes.py` remained the largest active API Python module after `D1`, combining route handlers, `DocumentManager`, file extraction helpers, background pipeline functions, and a long block of Pydantic status/pagination models.
  - The status-facing schemas (`DocStatusResponse`, `DocsStatusesResponse`, `TrackStatusResponse`, `DocumentsRequest`, `PaginationInfo`, `PaginatedDocsResponse`, `StatusCountsResponse`, `PipelineStatusResponse`) form a self-contained seam because they depend mainly on `DocStatus` plus datetime normalization.
  - Pulling that seam out reduces the router's mixed responsibilities without changing external paths or the `create_document_routes(...)` composition contract.
- Decision:
  - Introduce `lightrag/api/routers/document_status_models.py` for the document status and pagination request/response schemas plus shared datetime formatting.
  - Import those schemas back into `lightrag/api/routers/document_routes.py` so existing imports from `document_routes` continue to work.
  - Leave upload, deletion, and graph-edit request models in `document_routes.py` for now instead of widening the task into a full router rewrite.
- Impact:
  - `document_routes.py` now has a clearer boundary between API schemas and routing/pipeline orchestration.
  - Follow-on document API cleanup can extract additional seams incrementally rather than editing one monolithic file each time.
  - Focused tests now protect the extracted schema module and the compatibility re-export path.

## DCR-021: J1 moves document write/delete schemas behind a second API-model seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `I1`, `lightrag/api/routers/document_routes.py` still opened with a second block of request/response models for scan, insert, clear, and delete operations before the `DocumentManager` implementation began.
  - Those models (`ScanResponse`, `ReprocessResponse`, `CancelPipelineResponse`, `InsertTextRequest`, `InsertTextsRequest`, `InsertResponse`, `ClearDocumentsResponse`, `ClearCacheRequest`, `ClearCacheResponse`, `DeleteDocRequest`, `DeleteEntityRequest`, `DeleteRelationRequest`) depend only on Pydantic field validation plus simple string/list normalization.
  - Keeping them inline would leave the router hotspot responsible for two separate API-model seams even after the status/pagination extraction.
- Decision:
  - Introduce `lightrag/api/routers/document_operation_models.py` for the document write/delete request and response schemas.
  - Import those schemas back into `lightrag/api/routers/document_routes.py` so existing imports from `document_routes` remain stable.
  - Keep `DocumentManager`, file sanitization, and route handlers in `document_routes.py` for now instead of widening the task into behavior changes.
- Impact:
  - `document_routes.py` sheds another large schema block and keeps a tighter focus on document management and route execution.
  - Document API contract models are now split along two clearer seams: status/pagination and write/delete operations.
  - Focused tests now lock the extracted validator behavior and the compatibility re-export path.

## DCR-022: K1 moves DocumentManager and file-path helpers behind a document-ingestion seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `J1`, `lightrag/api/routers/document_routes.py` still owned `DocumentManager`, upload filename sanitization, deletion path validation, and unique `__enqueued__` filename generation before the extraction pipeline helpers even began.
  - That code does not depend on FastAPI route state; it only depends on filesystem paths, simple workspace rules, and logging.
  - `lightrag/api/lightrag_server.py` already imports `DocumentManager` from `document_routes`, so the current import surface needed to stay stable while the seam moved.
- Decision:
  - Introduce `lightrag/api/routers/document_manager.py` for `DocumentManager`, `sanitize_filename(...)`, `validate_file_path_security(...)`, and `get_unique_filename_in_enqueued(...)`.
  - Import those symbols back into `lightrag/api/routers/document_routes.py` so existing imports from `document_routes` continue to work.
  - Leave file extraction and pipeline orchestration helpers in `document_routes.py` for now instead of widening the task into a broader ingestion-pipeline split.
- Impact:
  - `document_routes.py` now starts closer to route and pipeline behavior rather than path-safety and directory-management primitives.
  - The document API now has a clearer ingestion-support seam that can be tested directly without importing the full routing module.
  - Focused tests now lock workspace-scoped input directories, supported-file scanning, path sanitization, and the compatibility re-export path.

## DCR-023: L1 moves document content extraction behind a file-format seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `K1`, `lightrag/api/routers/document_routes.py` still began with a long block of file-format extraction helpers before the enqueue pipeline functions.
  - `_is_docling_available()`, `_convert_with_docling()`, `_extract_pdf_pypdf()`, `_extract_docx()`, `_extract_pptx()`, and `_extract_xlsx()` depend on file bytes, optional provider libraries, and text-formatting rules, but they do not depend on FastAPI route state.
  - Keeping those helpers inline would leave `document_routes.py` responsible for three separate support seams even after schema and document-manager extraction.
- Decision:
  - Introduce `lightrag/api/routers/document_content_extraction.py` for docling availability checks and the PDF/DOCX/PPTX/XLSX extraction helpers.
  - Keep the tabular escaping logic as explicit helper functions inside that new module so extraction-specific formatting rules can be tested directly.
  - Import the extracted helpers back into `lightrag/api/routers/document_routes.py` so existing imports from `document_routes` continue to work.
- Impact:
  - `document_routes.py` now starts closer to queue orchestration and route behavior instead of file-format parsing details.
  - Document content extraction rules now have a dedicated module and direct regression tests for their text-escaping behavior.
  - Follow-on cleanup can target enqueue/pipeline orchestration separately from file-format conversion logic.

## DCR-024: M1 moves document indexing orchestration behind a pipeline seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `L1`, `lightrag/api/routers/document_routes.py` still contained the full indexing pipeline: file enqueueing, single-file indexing, sequential multi-file indexing, text indexing, and scan-trigger orchestration.
  - Those helpers depend on `LightRAG`, document-manager helpers, content extraction helpers, and config, but they do not depend on FastAPI route state or response models.
  - Keeping them inline would leave `document_routes.py` responsible for route handlers plus both indexing and deletion background workflows.
- Decision:
  - Introduce `lightrag/api/routers/document_indexing_pipeline.py` for `pipeline_enqueue_file(...)`, `pipeline_index_file(...)`, `pipeline_index_files(...)`, `pipeline_index_texts(...)`, and `run_scanning_process(...)`.
  - Keep the temporary-file cleanup rule and the enqueue-time file-format branching inside that new module so indexing behavior is owned in one place.
  - Import the extracted helpers back into `lightrag/api/routers/document_routes.py` so existing imports from `document_routes` remain stable.
- Impact:
  - `document_routes.py` now starts closer to route composition plus the remaining deletion workflow instead of the full document indexing lifecycle.
  - The document indexing pipeline can now be tested directly for source-padding, ordering, and scan filtering without importing the full route module.
  - Follow-on cleanup can target the remaining deletion background workflow as its own seam rather than continuing to edit one monolithic router.

## DCR-025: N1 moves batch deletion orchestration behind a deletion-pipeline seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `M1`, the last major non-route workflow still embedded in `lightrag/api/routers/document_routes.py` was `background_delete_documents(...)`.
  - That worker coordinates shared pipeline status, per-document deletion calls, optional filesystem cleanup, and pending-request handoff, but it does not depend on FastAPI route state or response models.
  - Keeping it inline would leave the router responsible for both the route layer and one long-running background pipeline implementation.
- Decision:
  - Introduce `lightrag/api/routers/document_deletion_pipeline.py` for `background_delete_documents(...)`.
  - Keep the shared-storage coordination and optional file cleanup inside that new module so deletion orchestration is owned in one place.
  - Import the helper back into `lightrag/api/routers/document_routes.py` so existing imports from `document_routes` remain stable.
- Impact:
  - `document_routes.py` now focuses much more tightly on route composition and endpoint behavior instead of long-running background workflows.
  - The deletion pipeline can be tested directly for status transitions and pending-request handoff without importing the full route module.
  - Follow-on cleanup can target the remaining route-local clear/status/cancel logic as smaller seams instead of editing a mixed router-and-worker file.

## DCR-026: O1 moves the clear-documents workflow behind a clear-pipeline seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `N1`, the largest remaining non-route block in `lightrag/api/routers/document_routes.py` was `clear_documents()`, which coordinated shared pipeline status, storage `drop()` calls, and input-directory cleanup inline with the route definition.
  - That workflow does not depend on FastAPI request state or response shaping; it depends on `LightRAG`, the document manager, and shared storage coordination.
  - The inline implementation also tracked async `drop()` results separately from the original storage list, which made success logging fragile whenever some storage slots were `None`.
- Decision:
  - Introduce `lightrag/api/routers/document_clear_pipeline.py` for `clear_documents_pipeline(...)`.
  - Import that helper back into `lightrag/api/routers/document_routes.py` so existing imports from `document_routes` remain stable.
  - Pair `drop()` results with only the active storages inside the extracted helper so optional `None` storage slots do not misalign logging and result handling.
- Impact:
  - `document_routes.py` moves closer to a pure route-composition layer instead of embedding another storage lifecycle workflow.
  - The clear-documents behavior can now be tested directly for active-storage handling and top-level-only file cleanup without importing the full routing module.
  - Follow-on API cleanup can focus on route-local status and query endpoints instead of storage-clearing internals.

## DCR-027: P1 moves pipeline control behavior behind a pipeline-control seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `O1`, `lightrag/api/routers/document_routes.py` still embedded three pipeline-control behaviors: shared pipeline status reads, failed-document reprocessing startup, and cancellation flag updates.
  - Those code paths depend on `LightRAG`, shared storage state, and FastAPI background task scheduling, but they do not depend on route-local request parsing or response wiring.
  - The status endpoint also owned two normalization rules that are easy to regress when left inline: converting update flags to plain booleans and truncating long history logs to the latest 1000 messages.
- Decision:
  - Introduce `lightrag/api/routers/document_pipeline_control.py` for `get_pipeline_status_response(...)`, `start_failed_document_reprocessing(...)`, and `request_pipeline_cancellation(...)`.
  - Import those helpers back into `lightrag/api/routers/document_routes.py` so the router stays the compatibility surface for extracted document helpers.
  - Keep the remaining document listing and status-query endpoints in `document_routes.py` for now instead of widening this run into every read-only document query path.
- Impact:
  - `document_routes.py` sheds another cluster of shared-state orchestration and moves closer to pure endpoint composition.
  - Pipeline-control behavior now has direct regression tests for history truncation, background-task startup, and cancellation flag updates without importing the full router.
  - A later follow-on task can target the remaining read-only document status/query endpoints as a separate seam.

## DCR-028: Q1 moves read-only document status queries behind a status-query seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `P1`, the main non-route cluster left in `lightrag/api/routers/document_routes.py` was the set of read-only status endpoints: grouped status listing, track-id lookup, paginated listing, and aggregated status counts.
  - Those handlers repeated the same `DocStatusResponse` field mapping several times while also owning query-specific rules such as the 1000-document round-robin cap for the deprecated grouped listing.
  - The behavior depends on `LightRAG` document-status reads and response normalization, not on FastAPI route state.
- Decision:
  - Introduce `lightrag/api/routers/document_status_queries.py` for `build_doc_status_response(...)`, `get_documents_statuses_response(...)`, `get_track_status_response(...)`, `get_paginated_documents_response(...)`, and `get_document_status_counts_response(...)`.
  - Import those helpers back into `lightrag/api/routers/document_routes.py` so the router remains the compatibility surface for extracted document helpers.
  - Keep mutation-oriented endpoints such as delete, clear-cache, and graph deletion in `document_routes.py` for now instead of widening this run into a broader command/query split.
- Impact:
  - `document_routes.py` drops another block of response-assembly logic and moves closer to a route-only composition layer.
  - Shared `DocStatusResponse` construction now lives in one place for the extracted query paths, which reduces mapping drift across grouped, tracked, and paginated reads.
  - Follow-on cleanup can focus on the remaining mutation endpoints as a separate seam instead of mixing them with read-only status queries.

## DCR-029: R1 moves mutation command behavior behind a mutation-command seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `Q1`, the main non-route block left in `lightrag/api/routers/document_routes.py` was the set of mutation command endpoints: document deletion scheduling, cache clearing, entity deletion, and relation deletion.
  - Those handlers owned shared pipeline busy checks, background task wiring, and API-facing error normalization for `DeletionResult`, but they did not depend on route-local request parsing beyond the already-validated request models.
  - Keeping that logic inline would leave the router responsible for both endpoint composition and command orchestration after the read-side extraction work.
- Decision:
  - Introduce `lightrag/api/routers/document_mutation_commands.py` for `initiate_document_deletion(...)`, `clear_cache_response(...)`, `delete_entity_response(...)`, and `delete_relation_response(...)`.
  - Import those helpers back into `lightrag/api/routers/document_routes.py` so the router remains the compatibility surface for extracted document helpers.
  - Leave upload/text insertion entrypoints in `document_routes.py` for now because they still combine route-local validation with ingestion scheduling and are better handled as a separate seam.
- Impact:
  - `document_routes.py` sheds another cluster of command orchestration and moves closer to a route-only layer.
  - Mutation behavior now has direct regression tests for busy-state deletion refusal, cache clearing, and deletion error mapping without importing the full router.
  - Follow-on cleanup can target the remaining upload/text insertion entrypoints as a separate seam instead of mixing them with delete and cache commands.

## DCR-030: S1 moves ingestion command behavior behind an ingestion-command seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `R1`, the main non-route block left in `lightrag/api/routers/document_routes.py` was the ingestion entrypoint cluster: scan startup, file upload, single-text insertion, and multi-text insertion.
  - Those handlers owned duplicate-source checks, track-id generation, file persistence, and background task scheduling, but they did not depend on route-local composition beyond the existing request models and file parameter binding.
  - Keeping that logic inline would leave the router mixing endpoint composition with ingestion orchestration even after the command/query cleanup work.
- Decision:
  - Introduce `lightrag/api/routers/document_ingest_commands.py` for `start_scan_for_new_documents(...)`, `upload_file_to_input_dir(...)`, `insert_single_text(...)`, and `insert_multiple_texts(...)`.
  - Import those helpers back into `lightrag/api/routers/document_routes.py` so the router remains the compatibility surface for extracted document helpers.
  - Keep the remaining router file as the route composition surface rather than widening this run into a broader package move.
- Impact:
  - `document_routes.py` sheds the last large ingestion orchestration block and moves close to a pure route-composition layer.
  - Ingestion behavior now has direct regression tests for scan scheduling, duplicate detection, and text enqueue startup without importing the full router.
  - Follow-on API work can shift away from document_routes splitting and target broader route composition or other hotspots.

## DCR-031: T1 moves query API models behind a query-model seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After the document-route cleanup series, `lightrag/api/routers/query_routes.py` became the largest active API router module and still opened with a long block of Pydantic request/response models before any route definitions.
  - `QueryRequest`, `ReferenceItem`, `QueryResponse`, `QueryDataResponse`, and `StreamChunkResponse` define the query API contract and include validation/conversion rules such as `conversation_history` role checks and `to_query_params(...)`.
  - Those models do not depend on FastAPI route state, so keeping them inline makes the router responsible for both API contracts and route execution.
- Decision:
  - Introduce `lightrag/api/routers/query_models.py` for the query request/response models and `QueryRequest.to_query_params(...)`.
  - Import those models back into `lightrag/api/routers/query_routes.py` so existing imports from `query_routes` remain stable.
  - Keep route handlers and OpenAPI response examples in `query_routes.py` for now instead of widening this run into a full router decomposition.
- Impact:
  - `query_routes.py` sheds a self-contained contract block and moves toward a clearer routing focus.
  - Query model validation and conversion rules now have focused regression coverage without importing the full query router.
  - A follow-on task can target route helper extraction or response-example cleanup separately from the query API contracts.

## DCR-032: U1 moves shared query response formatting behind a response-helper seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `T1`, `lightrag/api/routers/query_routes.py` still duplicated the same result-shaping logic in both `/query` and `/query/stream`: extracting references from the unified `aquery_llm` result, optionally enriching them with chunk content, and building final non-stream response payloads.
  - That logic depends on the unified query result shape, not on FastAPI route state.
  - Keeping it inline risks format drift between non-stream and stream fallbacks whenever one handler changes its reference-enrichment rules.
- Decision:
  - Introduce `lightrag/api/routers/query_response_helpers.py` for `prepare_query_references(...)`, `get_query_response_content(...)`, `build_query_response_model(...)`, and `build_stream_complete_payload(...)`.
  - Import those helpers back into `lightrag/api/routers/query_routes.py` so existing imports from `query_routes` remain stable.
  - Leave the route handlers and their OpenAPI examples in `query_routes.py` for now instead of widening this run into a full route-helper extraction.
- Impact:
  - `query_routes.py` drops another duplicated internal seam and keeps one place for reference enrichment and non-stream payload rules.
  - Focused tests now protect chunk-content enrichment, fallback response text, and stream-fallback payload shaping without importing the full router.
  - A follow-on task can target route-helper extraction or example-cleanup separately from the shared response formatting logic.

## DCR-033: V1 moves query route OpenAPI response metadata behind a docs seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `U1`, `lightrag/api/routers/query_routes.py` still spent most of its remaining size budget on three large inline `responses={...}` dictionaries for `/query`, `/query/stream`, and `/query/data`.
  - Those dictionaries encode static OpenAPI schemas and examples; they do not depend on `rag`, request state, or route-local control flow.
  - Keeping them inline makes the router harder to scan and raises the risk that documentation-only edits get tangled with behavior changes in the same hotspot module.
- Decision:
  - Introduce `lightrag/api/routers/query_route_docs.py` for the query route OpenAPI response constants.
  - Reuse those constants from `lightrag/api/routers/query_routes.py` and re-export them there so the router remains the compatibility surface for extracted query helpers.
  - Keep route handlers and docstrings in `query_routes.py` for now instead of widening this run into a full query route registration split.
- Impact:
  - `query_routes.py` sheds its largest remaining static documentation block and moves closer to a route-focused module.
  - Query response examples and schemas now have a dedicated home that can be updated and tested without editing runtime query logic.
  - A follow-on task can target handler extraction or shared docstring cleanup separately from the OpenAPI response metadata.

## DCR-034: W1 moves query streaming assembly behind a streaming seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `V1`, the largest remaining non-route runtime seam in `lightrag/api/routers/query_routes.py` was the nested `/query/stream` async generator plus `StreamingResponse` assembly.
  - That block owns NDJSON line shaping, reference-first emission, empty-chunk filtering, non-stream fallback payload shaping, and stream-error conversion into `{"error": ...}` lines.
  - Those behaviors depend on the unified `aquery_llm` result format, not on FastAPI route registration.
- Decision:
  - Introduce `lightrag/api/routers/query_streaming.py` for `iter_query_stream_payloads(...)` and `build_query_streaming_response(...)`.
  - Reuse and re-export those helpers from `lightrag/api/routers/query_routes.py` so the router remains the compatibility surface for extracted query helpers.
  - Leave non-stream query execution and `query_data` normalization in `query_routes.py` for now instead of widening this run into a broader handler extraction.
- Impact:
  - `query_routes.py` sheds its remaining inline NDJSON orchestration and moves closer to a route-only module.
  - Streaming behavior now has focused regression coverage for reference emission, empty-chunk filtering, stream error lines, and non-stream fallback payloads.
  - A follow-on task can target the remaining non-stream query execution or data-response normalization as separate seams.

## DCR-035: X1 moves non-stream query execution behind a query-execution seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `W1`, `lightrag/api/routers/query_routes.py` still owned the non-stream `/query` execution path and `/query/data` response normalization.
  - Those blocks handled request-to-param conversion, direct `rag` calls, and public response shaping, but they did not depend on route registration.
  - Root-cause checks also exposed a latent bug in the `/query/data` fallback path: it tried to instantiate `QueryDataResponse` without the required `metadata` field, which raises a Pydantic validation error instead of returning the intended failure payload.
- Decision:
  - Introduce `lightrag/api/routers/query_execution.py` for non-stream `/query` execution, `/query/data` param building, and response normalization helpers.
  - Reuse and re-export those helpers from `lightrag/api/routers/query_routes.py` so the router remains the compatibility surface for extracted query helpers.
  - Fix the invalid `/query/data` fallback by returning `metadata={}` in the normalized failure response.
- Impact:
  - `query_routes.py` sheds its remaining non-stream runtime orchestration and moves closer to a route-only module.
  - The `/query/data` fallback path is now a valid `QueryDataResponse` instead of a second-order validation failure.
  - Focused tests now protect stream=False enforcement, query helper re-exports, and the corrected failure normalization path.

## DCR-036: Y1 moves long-form query route descriptions behind a description seam
- Date: 2026-04-05
- Status: accepted
- Context:
  - After `X1`, most of the remaining bulk in `lightrag/api/routers/query_routes.py` was no longer runtime logic; it was the three long-form route descriptions for `/query`, `/query/stream`, and `/query/data`.
  - That text is static documentation and does not depend on route-local control flow or runtime state.
  - Keeping it in handler docstrings made the route module harder to scan and mixed documentation maintenance with endpoint wiring edits.
- Decision:
  - Introduce `lightrag/api/routers/query_route_descriptions.py` for the long-form query route description constants.
  - Reuse those constants through the FastAPI decorator `description=` parameter and re-export them from `lightrag/api/routers/query_routes.py` so the router remains the compatibility surface for extracted query documentation.
  - Keep the short route handlers in `query_routes.py` for now instead of widening this run into a full route-factory split.
- Impact:
  - `query_routes.py` sheds its remaining static documentation bulk and moves closer to a route-wiring module.
  - Query route descriptions now have a dedicated home and focused regression coverage without requiring edits to runtime query logic.
  - A follow-on task can target route-factory extraction or other API routers instead of continuing to peel static text out of `query_routes.py`.
