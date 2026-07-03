"""Wikipedia page loading from URL or search term."""

from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

import requests


def load_wikipedia_text(url_or_topic: str) -> tuple[str, str]:
    title = _title_from_input(url_or_topic)
    api_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + title
    response = requests.get(api_url, timeout=10)
    response.raise_for_status()
    payload = response.json()
    page_title = payload.get("title") or unquote(title).replace("_", " ")
    text = payload.get("extract") or ""
    if not text:
        raise ValueError(f"No summary text found for Wikipedia page: {page_title}")
    return page_title, text


def _title_from_input(value: str) -> str:
    parsed = urlparse(value)
    if parsed.netloc and "/wiki/" in parsed.path:
        return parsed.path.rsplit("/wiki/", 1)[-1]
    return re.sub(r"\s+", "_", value.strip())

