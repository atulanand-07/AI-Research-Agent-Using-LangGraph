"""Semantic Scholar search client."""

from __future__ import annotations

import requests

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def search_semantic_scholar(topic: str, max_results: int = 10) -> list[dict]:
    params = {
        "query": topic,
        "limit": max_results,
        "fields": "title,authors,abstract,year,citationCount,openAccessPdf",
    }
    response = requests.get(SEMANTIC_SCHOLAR_URL, params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()
    results = []
    for item in payload.get("data", []):
        pdf = item.get("openAccessPdf") or {}
        results.append(
            {
                "id": item.get("paperId") or "",
                "title": item.get("title") or "",
                "authors": [author.get("name", "") for author in item.get("authors", [])],
                "abstract": item.get("abstract") or "",
                "publication_year": item.get("year"),
                "source": "Semantic Scholar",
                "pdf_link": pdf.get("url"),
                "citation_count": item.get("citationCount"),
            }
        )
    return results

