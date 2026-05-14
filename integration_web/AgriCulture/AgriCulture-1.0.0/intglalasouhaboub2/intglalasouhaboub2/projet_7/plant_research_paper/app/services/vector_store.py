from __future__ import annotations

import logging
import os
from typing import Any

import chromadb

from app.config import settings
from app.services.embeddings import TextEmbedder
from app.utils.text import stable_hash

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self) -> None:
        os.environ.setdefault("ANONYMIZED_TELEMETRY", "FALSE")
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.client = None
        self._fallback_memory: dict[str, list[dict[str, Any]]] = {}
        self.text_embedder = TextEmbedder()
        try:
            self.client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        except Exception as exc:  # noqa: BLE001
            logger.warning("ChromaDB initialization failed, using in-memory fallback: %s", exc)
            self.client = None

    def add_documents(self, collection_name: str, docs: list[dict[str, Any]]) -> None:
        if not docs:
            return
        if self.client is None:
            self._add_documents_fallback(collection_name, docs)
            return
        try:
            collection = self.client.get_or_create_collection(collection_name)
            ids = [doc.get("id", stable_hash(doc["text"])) for doc in docs]
            texts = [doc["text"] for doc in docs]
            metadatas = [doc.get("metadata", {}) for doc in docs]
            embeddings = [self.text_embedder.embed(text) for text in texts]
            collection.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ChromaDB add_documents failed, switching to in-memory fallback: %s", exc)
            self.client = None
            self._add_documents_fallback(collection_name, docs)

    def query(self, collection_name: str, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        if self.client is None:
            return self._query_fallback(collection_name, query, n_results)
        try:
            collection = self.client.get_or_create_collection(collection_name)
            result = collection.query(query_embeddings=[self.text_embedder.embed(query)], n_results=n_results)
            docs = result.get("documents", [[]])[0]
            metas = result.get("metadatas", [[]])[0]
            return [{"text": doc, "metadata": meta} for doc, meta in zip(docs, metas, strict=False)]
        except Exception as exc:  # noqa: BLE001
            logger.warning("ChromaDB query failed, switching to in-memory fallback: %s", exc)
            self.client = None
            return self._query_fallback(collection_name, query, n_results)

    def _add_documents_fallback(self, collection_name: str, docs: list[dict[str, Any]]) -> None:
        bucket = self._fallback_memory.setdefault(collection_name, [])
        for doc in docs:
            bucket.append(
                {
                    "id": doc.get("id", stable_hash(str(doc.get("text", "")))),
                    "text": str(doc.get("text", "")),
                    "metadata": doc.get("metadata", {}),
                }
            )

    def _query_fallback(self, collection_name: str, query: str, n_results: int) -> list[dict[str, Any]]:
        docs = self._fallback_memory.get(collection_name, [])
        if not docs:
            return []
        q = query.lower()
        ranked = sorted(
            docs,
            key=lambda item: item["text"].lower().count(q),
            reverse=True,
        )
        top = ranked[:n_results]
        return [{"text": item["text"], "metadata": item["metadata"]} for item in top]
