import asyncio
import os
import re
import time
from dataclasses import dataclass
from typing import Any, final

import numpy as np

from lightrag._pipmaster import import_or_install
from lightrag.base import BaseVectorStorage
from lightrag.kg.storage_contracts import resolve_storage_workspace
from lightrag.utils import compute_mdhash_id, logger

_chromadb = import_or_install("chromadb")
_chromadb_config = import_or_install("chromadb.config", package_name="chromadb")
HttpClient = _chromadb.HttpClient
PersistentClient = _chromadb.PersistentClient
Settings = _chromadb_config.Settings


@final
@dataclass
class ChromaVectorDBStorage(BaseVectorStorage):
    """ChromaDB vector storage implementation for entities, relationships and chunks."""

    def __post_init__(self):
        config = self.global_config.get("vector_db_storage_cls_kwargs", {})
        cosine_threshold = config.get("cosine_better_than_threshold")
        if cosine_threshold is None:
            raise ValueError(
                "cosine_better_than_threshold must be specified in vector_db_storage_cls_kwargs"
            )

        self.cosine_better_than_threshold = cosine_threshold
        self._client = None
        self._collection = None
        self._client_mode = self._get_config_value("mode", "CHROMA_MODE", "persistent")
        self.workspace = resolve_storage_workspace(
            os.getenv("CHROMA_WORKSPACE"),
            self.workspace,
            os.getenv("WORKSPACE"),
            default="default",
        )
        self._workspace_name = self.workspace
        self._collection_name = self._build_collection_name(
            self._workspace_name, self.namespace
        )
        self._collection_settings = self._get_collection_settings(config)
        self._max_batch_size = int(
            self.global_config.get(
                "embedding_batch_num",
                self._collection_settings.get("hnsw:batch_size", 32),
            )
        )

    async def initialize(self):
        self._client = self._create_client()
        self._collection = self._get_or_create_collection()

    async def finalize(self):
        self._collection = None
        self._client = None

    def _get_config_value(
        self, key: str, env_key: str, default: Any, config: dict[str, Any] | None = None
    ) -> Any:
        config = config or self.global_config.get("vector_db_storage_cls_kwargs", {})
        return config.get(key, os.getenv(env_key, default))

    def _build_collection_name(self, workspace: str, namespace: str) -> str:
        raw_name = f"{workspace}__{namespace}".lower()
        sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", raw_name)
        sanitized = sanitized.strip("._-")
        if len(sanitized) < 3:
            sanitized = f"lr_{sanitized}"
        return sanitized[:63]

    def _get_collection_settings(self, config: dict[str, Any]) -> dict[str, Any]:
        default_collection_settings = {
            "hnsw:space": "cosine",
            "hnsw:construction_ef": 128,
            "hnsw:search_ef": 128,
            "hnsw:M": 16,
            "hnsw:batch_size": 100,
            "hnsw:sync_threshold": 1000,
        }
        user_settings = config.get("collection_settings", {})
        return {**default_collection_settings, **user_settings}

    def _create_client(self):
        config = self.global_config.get("vector_db_storage_cls_kwargs", {})
        if self._client_mode == "http":
            headers = {}
            auth_provider = self._get_config_value(
                "auth_provider",
                "CHROMA_AUTH_PROVIDER",
                "",
                config,
            )
            auth_credentials = self._get_config_value(
                "auth_credentials",
                "CHROMA_AUTH_CREDENTIALS",
                "",
                config,
            )
            header_name = self._get_config_value(
                "auth_header_name",
                "CHROMA_AUTH_HEADER_NAME",
                "X-Chroma-Token",
                config,
            )
            if auth_credentials and "token_authn" in auth_provider:
                headers[header_name] = auth_credentials

            ssl = str(self._get_config_value("ssl", "CHROMA_SSL", "false", config)).lower()
            host = self._get_config_value("host", "CHROMA_HOST", "localhost", config)
            port = int(self._get_config_value("port", "CHROMA_PORT", 8000, config))
            settings_kwargs = {
                "anonymized_telemetry": False,
                "allow_reset": True,
            }
            if auth_provider:
                settings_kwargs["chroma_client_auth_provider"] = auth_provider
            if auth_credentials:
                settings_kwargs["chroma_client_auth_credentials"] = auth_credentials
            return HttpClient(
                host=host,
                port=port,
                ssl=ssl in {"1", "true", "yes", "on"},
                headers=headers or None,
                settings=Settings(**settings_kwargs),
            )

        chroma_path = self._get_config_value("local_path", "CHROMA_PATH", None, config)
        if not chroma_path:
            chroma_path = os.path.join(
                self.global_config["working_dir"], self._workspace_name, "chroma"
            )
        os.makedirs(chroma_path, exist_ok=True)
        return PersistentClient(
            path=chroma_path,
            settings=Settings(allow_reset=True, anonymized_telemetry=False),
        )

    def _get_or_create_collection(self):
        return self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={
                **self._collection_settings,
                "dimension": self.embedding_func.embedding_dim,
                "workspace": self._workspace_name,
                "namespace": self.namespace,
            },
        )

    def _ensure_collection(self):
        if self._collection is None:
            raise RuntimeError("Chroma collection is not initialized")
        return self._collection

    def _metadata_from_item(self, item: dict[str, Any], default_created_at: int) -> dict[str, Any]:
        metadata = {k: item[k] for k in self.meta_fields if k in item}
        metadata["created_at"] = item.get("created_at", default_created_at)
        return metadata or {"created_at": default_created_at, "_default": "true"}

    @staticmethod
    def _normalize_embedding(embedding: Any) -> list[float]:
        if isinstance(embedding, np.ndarray):
            return embedding.astype(np.float32).tolist()
        return [float(value) for value in embedding]

    async def _batch_embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        batches = [
            texts[i : i + self._max_batch_size]
            for i in range(0, len(texts), self._max_batch_size)
        ]
        embeddings = await asyncio.gather(
            *(self.embedding_func(batch) for batch in batches)
        )
        merged = np.concatenate(embeddings) if embeddings else np.array([])
        return [self._normalize_embedding(row) for row in merged]

    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
        if not data:
            return

        collection = self._ensure_collection()
        current_time = int(time.time())
        ids = list(data.keys())
        documents = [item.get("content", "") for item in data.values()]
        metadatas = [
            self._metadata_from_item(item, current_time) for item in data.values()
        ]

        embeddings_by_id: dict[str, list[float]] = {}
        texts_to_embed: list[str] = []
        ids_to_embed: list[str] = []

        for item_id, item in data.items():
            precomputed = item.get("__vector__")
            if precomputed is None:
                precomputed = item.get("vector")
            if precomputed is not None:
                embeddings_by_id[item_id] = self._normalize_embedding(precomputed)
            else:
                ids_to_embed.append(item_id)
                texts_to_embed.append(item.get("content", ""))

        if texts_to_embed:
            embedded = await self._batch_embed(texts_to_embed)
            embeddings_by_id.update(dict(zip(ids_to_embed, embedded)))

        embeddings = [embeddings_by_id[item_id] for item_id in ids]

        for start in range(0, len(ids), self._max_batch_size):
            end = start + self._max_batch_size
            collection.upsert(
                ids=ids[start:end],
                embeddings=embeddings[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )

    async def query(
        self, query: str, top_k: int, query_embedding: list[float] = None
    ) -> list[dict[str, Any]]:
        collection = self._ensure_collection()
        if query_embedding is None:
            embedded = await self.embedding_func([query], _priority=5)
            query_embedding = embedded[0]

        result = collection.query(
            query_embeddings=[self._normalize_embedding(query_embedding)],
            n_results=max(top_k * 2, top_k),
            include=["metadatas", "distances", "documents"],
        )

        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]

        formatted: list[dict[str, Any]] = []
        for idx, item_id in enumerate(ids):
            metadata = metadatas[idx] or {}
            similarity = 1 - float(distances[idx])
            if similarity < self.cosine_better_than_threshold:
                continue
            formatted.append(
                {
                    "id": item_id,
                    "distance": similarity,
                    "content": documents[idx],
                    "created_at": metadata.get("created_at"),
                    **metadata,
                }
            )
            if len(formatted) >= top_k:
                break
        return formatted

    async def index_done_callback(self) -> None:
        return None

    async def delete_entity(self, entity_name: str) -> None:
        collection = self._ensure_collection()
        entity_id = compute_mdhash_id(entity_name, prefix="ent-")
        collection.delete(ids=[entity_id])

    async def delete_entity_relation(self, entity_name: str) -> None:
        collection = self._ensure_collection()
        try:
            result = collection.get(include=["metadatas"])
        except Exception as exc:
            logger.error(
                f"Failed to inspect Chroma relations for entity {entity_name}: {exc}"
            )
            raise

        ids_to_delete: list[str] = []
        for idx, item_id in enumerate(result.get("ids", [])):
            metadata = (result.get("metadatas") or [None] * len(result.get("ids", [])))[
                idx
            ] or {}
            if metadata.get("src_id") == entity_name or metadata.get("tgt_id") == entity_name:
                ids_to_delete.append(item_id)

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)

    async def delete(self, ids: list[str]):
        if not ids:
            return
        collection = self._ensure_collection()
        collection.delete(ids=ids)

    async def get_by_id(self, id: str) -> dict[str, Any] | None:
        results = await self.get_by_ids([id])
        return results[0] if results else None

    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        if not ids:
            return []

        collection = self._ensure_collection()
        result = collection.get(
            ids=ids, include=["metadatas", "embeddings", "documents"]
        )
        result_ids = result.get("ids", [])
        metadatas = result.get("metadatas", [])
        embeddings = result.get("embeddings", [])
        documents = result.get("documents", [])

        items_by_id: dict[str, dict[str, Any]] = {}
        for idx, item_id in enumerate(result_ids):
            metadata = metadatas[idx] or {}
            items_by_id[str(item_id)] = {
                "id": item_id,
                "vector": embeddings[idx],
                "content": documents[idx],
                "created_at": metadata.get("created_at"),
                **metadata,
            }

        return [items_by_id.get(str(item_id)) for item_id in ids]

    async def get_vectors_by_ids(self, ids: list[str]) -> dict[str, list[float]]:
        if not ids:
            return {}

        collection = self._ensure_collection()
        result = collection.get(ids=ids, include=["embeddings"])
        embeddings = result.get("embeddings", [])
        result_ids = result.get("ids", [])
        return {
            str(item_id): self._normalize_embedding(embeddings[idx])
            for idx, item_id in enumerate(result_ids)
            if embeddings[idx] is not None
        }

    async def drop(self) -> dict[str, str]:
        if self._client is None:
            return {"status": "error", "message": "client not initialized"}

        try:
            self._client.delete_collection(self._collection_name)
        except Exception:
            # Missing collection is fine during cleanup.
            pass

        try:
            self._collection = self._get_or_create_collection()
            logger.info(
                f"[{self._workspace_name}] Dropped Chroma collection {self._collection_name}"
            )
            return {"status": "success", "message": "data dropped"}
        except Exception as exc:
            logger.error(
                f"[{self._workspace_name}] Failed to recreate Chroma collection {self._collection_name}: {exc}"
            )
            return {"status": "error", "message": str(exc)}
