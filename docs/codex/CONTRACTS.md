# LightRAG External Contracts

This file freezes the current public surfaces that later refactors must either preserve or migrate deliberately.

## Python Package Surface
- Package import:
  - `from lightrag import LightRAG, QueryParam`
- Current package version:
  - `lightrag.__version__ == 1.4.9.9`
- Console scripts from `pyproject.toml`:
  - `lightrag-server`
  - `lightrag-gunicorn`
  - `lightrag-download-cache`
  - `lightrag-clean-llmqc`

## Source-Based Developer Entry Points
- Install core from source:
  - `uv sync`
  - `pip install -e .`
- Install API extras:
  - `uv sync --extra api`
  - `pip install -e ".[api]"`
- Start API server:
  - `lightrag-server`
  - `uvicorn lightrag.api.lightrag_server:app --reload`
- Build Web UI:
  - `bun install --cwd lightrag_webui --frozen-lockfile`
  - `bun run build --cwd lightrag_webui`

## HTTP API Surface
- App factory currently lives in `lightrag/api/lightrag_server.py`
- Router families currently included by the app:
  - document routes under `/documents`
  - query routes from `lightrag/api/routers/query_routes.py`
  - graph routes from `lightrag/api/routers/graph_routes.py`
  - Ollama-compatible routes under `/api`

### Query Route Family
- Main request model: `QueryRequest`
- Current route styles include:
  - standard query
  - streaming query
  - data-oriented query responses

### Graph Route Family
- Current route styles include:
  - graph listing
  - label listing and search
  - entity existence checks
  - entity and relation create/edit flows
  - entity merge flow

### Document Route Family
- Current route styles include:
  - document upload and ingestion
  - batch operations
  - listing and status inspection
  - delete and clear flows
  - pipeline control operations

### Ollama-Compatible API
- Mounted under `/api`
- Current endpoints include:
  - `/api/version`
  - `/api/tags`
  - `/api/ps`
  - `/api/generate`
  - `/api/chat`

## Configuration Surface

### Environment Variables
Current `env.example` exposes these major configuration groups:
- server and Web UI:
  - `HOST`, `PORT`, `WEBUI_TITLE`, `WEBUI_DESCRIPTION`
- runtime behavior:
  - `ENABLE_LLM_CACHE`, `ENABLE_LLM_CACHE_FOR_EXTRACT`, `SUMMARY_LANGUAGE`, `MAX_ASYNC`, `MAX_PARALLEL_INSERT`
- LLM binding:
  - `LLM_BINDING`, `LLM_MODEL`, `LLM_BINDING_HOST`, `LLM_BINDING_API_KEY`
- embedding binding:
  - `EMBEDDING_BINDING`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `EMBEDDING_BINDING_HOST`, `EMBEDDING_BINDING_API_KEY`
- storage selection:
  - `LIGHTRAG_KV_STORAGE`, `LIGHTRAG_DOC_STATUS_STORAGE`, `LIGHTRAG_GRAPH_STORAGE`, `LIGHTRAG_VECTOR_STORAGE`
- PostgreSQL:
  - `POSTGRES_*`
- Chroma:
  - `CHROMA_*`
- Neo4j:
  - `NEO4J_*`

### INI Configuration
Current `config.ini.example` has sections for:
- `[postgres]`
- `[chroma]`
- `[neo4j]`

## Web UI Surface
- Current authenticated app shell lives in `lightrag_webui/src/App.tsx`
- Current major user-visible tabs:
  - documents
  - knowledge graph
  - retrieval
  - api
- Login flow is routed through `lightrag_webui/src/AppRouter.tsx`

## Deployment Surface
- Docker-based local deployment:
  - `docker compose up`
- Supporting assets:
  - `Dockerfile`
  - `Dockerfile.lite`
  - `docker-compose.yml`

## Migration Rule
Any future breaking change to these surfaces must update this file and `docs/codex/DECISIONS.md` in the same change set.
