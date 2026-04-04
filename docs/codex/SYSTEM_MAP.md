# LightRAG System Map

## Core Subsystems

### Core Engine
- Path: `lightrag/`
- Purpose: document ingestion, chunking, entity extraction, graph build, retrieval, and answer orchestration
- Current hotspots:
  - `lightrag/lightrag.py`
  - `lightrag/operate.py`
- Long-term direction: split orchestration, retrieval, indexing, chunking, config, and error handling into smaller modules

### API Service
- Path: `lightrag/api/`
- Purpose: compose the FastAPI app, auth, config, upload/query/graph routes, and Ollama-compatible endpoints
- Current hotspot:
  - `lightrag/api/lightrag_server.py`
- Long-term direction: separate app factory, dependency wiring, lifecycle handling, and route registration

### Storage Adapters
- Path: `lightrag/kg/`
- Purpose: graph, vector, key-value, and document-status storage implementations
- Current shape: many provider-specific modules with overlapping concerns
- Long-term direction: explicit adapter contracts, shared initialization patterns, and contract tests

### LLM And Embedding Adapters
- Path: `lightrag/llm/`
- Purpose: model provider bindings for chat, embeddings, reranking, and related integrations
- Current shape: many provider-specific modules with repeated patterns
- Long-term direction: reduce divergence through shared interfaces and common helper layers

### Web UI
- Path: `lightrag_webui/`
- Purpose: authenticated UI for document management, graph viewing, retrieval testing, and API guidance
- Current primary feature surfaces:
  - `DocumentManager`
  - `GraphViewer`
  - `RetrievalTesting`
  - `ApiSite`
- Long-term direction: reduce duplicate state handling and keep only high-value user flows

### Test Layer
- Paths:
  - `tests/`
  - root-level `test_*.py`
- Purpose: offline unit tests, integration tests, storage tests, and legacy test entrypoints
- Long-term direction: move toward clearer test tiers and contract-focused coverage

### Deployment And Runtime Assets
- Paths:
  - `docker-compose.yml`
  - `Dockerfile*`
  - `.env`, `env.example`
  - `config.ini.example`
- Purpose: local service boot, deployment, and environment-driven configuration
- Long-term direction: converge configuration sources and make deployment flows consistent

## Cross-Cutting Concerns
- Configuration currently spans `.env`, `config.ini`, runtime args, and code defaults.
- Logging and error behavior should be made more uniform across engine, API, and adapters.
- Runtime artifacts currently live close to source directories and need clearer boundaries.

## Refactor Order
1. Baseline docs, quality gates, and automation
2. Core engine split and dependency reduction
3. Adapter contracts for storage and LLM integrations
4. API assembly cleanup
5. Web UI cleanup
6. Performance, artifact cleanup, and release hardening
