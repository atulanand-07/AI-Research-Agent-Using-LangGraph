"""Wikipedia search client using the common article result schema."""

from __future__ import annotations

import requests

WIKIPEDIA_SEARCH_URL = "https://en.wikipedia.org/w/api.php"


def search_wikipedia(topic: str, max_results: int = 10) -> list[dict]:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": topic,
        "format": "json",
        "srlimit": max_results,
    }
    response = requests.get(WIKIPEDIA_SEARCH_URL, params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()
    results = []
    for item in payload.get("query", {}).get("search", []):
        page_id = str(item.get("pageid", ""))
        title = item.get("title") or ""
        results.append(
            {
                "id": page_id,
                "title": title,
                "authors": [],
                "abstract": _strip_html(item.get("snippet", "")),
                "publication_year": None,
                "source": "Wikipedia",
                "pdf_link": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                "citation_count": None,
            }
        )
    return results


def _strip_html(value: str) -> str:
    return value.replace("<span class=\"searchmatch\">", "").replace("</span>", "")

