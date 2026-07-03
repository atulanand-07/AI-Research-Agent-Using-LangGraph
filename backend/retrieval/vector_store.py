"""Small vector-store facade with separate source and article namespaces."""

from __future__ import annotations

import hashlib
import math
import threading
from dataclasses import dataclass
from typing import Iterable


@dataclass
class StoredChunk:
    text: str
    source_name: str
    vector_ref: str
    chunk_id: str
    embedding: list[float]


class InMemoryVectorStore:
    """Dependency-light store used by API/tests; FAISS can replace internals later."""

    def __init__(self) -> None:
        self._sources: dict[str, list[StoredChunk]] = {}
        self._articles: dict[str, list[StoredChunk]] = {}
        self._lock = threading.RLock()

    def add_source_chunks(self, vector_ref: str, source_name: str, chunks: Iterable[str]) -> None:
        self._add(self._sources, vector_ref, source_name, chunks)

    def add_article_chunks(self, vector_ref: str, source_name: str, chunks: Iterable[str]) -> None:
        self._add(self._articles, vector_ref, source_name, chunks)

    def search_sources(self, query: str, vector_refs: list[str], top_k: int) -> list[dict]:
        return self._search(self._sources, query, vector_refs, top_k)

    def search_article(self, query: str, vector_ref: str, top_k: int) -> list[dict]:
        return self._search(self._articles, query, [vector_ref], top_k)

    def delete_source(self, vector_ref: str | None) -> None:
        if vector_ref:
            with self._lock:
                self._sources.pop(vector_ref, None)

    def replace_article(self, vector_ref: str, source_name: str, chunks: Iterable[str]) -> None:
        with self._lock:
            self._articles.clear()
        self.add_article_chunks(vector_ref, source_name, chunks)

    def clear_article(self) -> None:
        with self._lock:
            self._articles.clear()

    def _add(
        self,
        collection: dict[str, list[StoredChunk]],
        vector_ref: str,
        source_name: str,
        chunks: Iterable[str],
    ) -> None:
        stored: list[StoredChunk] = []
        for index, text in enumerate(chunks):
            if not text.strip():
                continue
            stored.append(
                StoredChunk(
                    text=text,
                    source_name=source_name,
                    vector_ref=vector_ref,
                    chunk_id=f"{vector_ref}:{index}",
                    embedding=_embed(text),
                )
            )
        with self._lock:
            collection[vector_ref] = stored

    def _search(
        self,
        collection: dict[str, list[StoredChunk]],
        query: str,
        vector_refs: list[str],
        top_k: int,
    ) -> list[dict]:
        query_embedding = _embed(query)
        candidates: list[tuple[float, StoredChunk]] = []
        with self._lock:
            for vector_ref in vector_refs:
                for chunk in collection.get(vector_ref, []):
                    candidates.append((_cosine(query_embedding, chunk.embedding), chunk))
        candidates.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "text": chunk.text,
                "source_name": chunk.source_name,
                "score": float(score),
                "vector_ref": chunk.vector_ref,
                "chunk_id": chunk.chunk_id,
            }
            for score, chunk in candidates[:top_k]
        ]


def _embed(text: str, dimensions: int = 256) -> list[float]:
    vector = [0.0] * dimensions
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        vector[bucket] += 1.0
    return vector


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


vector_store = InMemoryVectorStore()

