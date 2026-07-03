"""Merge, dedupe, and rank article search results."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

from .arxiv_client import search_arxiv
from .semantic_scholar_client import search_semantic_scholar
from .wikipedia_search_client import search_wikipedia


def search_articles(topic: str, max_results: int = 10) -> list[dict]:
    providers = [search_arxiv, search_semantic_scholar, search_wikipedia]
    merged: list[dict] = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(provider, topic, max_results) for provider in providers]
        for future in futures:
            try:
                merged.extend(future.result())
            except Exception:
                continue
    deduped = _dedupe(merged)
    deduped.sort(key=_rank_key, reverse=True)
    return deduped[:10]


def _dedupe(results: list[dict]) -> list[dict]:
    by_title: dict[str, dict] = {}
    for result in results:
        key = _normalize_title(result.get("title", ""))
        if not key:
            continue
        current = by_title.get(key)
        if current is None or _rank_key(result) > _rank_key(current):
            by_title[key] = result
    return list(by_title.values())


def _normalize_title(title: str) -> str:
    return re.sub(r"\W+", " ", title.lower()).strip()


def _rank_key(result: dict) -> tuple[int, int]:
    year = result.get("publication_year") or 0
    citations = result.get("citation_count") or 0
    return int(year), int(citations)

