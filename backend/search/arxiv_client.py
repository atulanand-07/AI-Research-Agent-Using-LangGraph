"""arXiv search client returning the standard article schema."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

ARXIV_API_URL = "http://export.arxiv.org/api/query"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def search_arxiv(topic: str, max_results: int = 10) -> list[dict]:
    query = _sanitize_query(topic)
    url = (
        f"{ARXIV_API_URL}?search_query=all:{query}"
        f"&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    )
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return _parse_arxiv_xml(response.text)


def _sanitize_query(topic: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", topic.lower())
    words = cleaned.split()
    if not words:
        raise ValueError(f"Query has no searchable terms after sanitizing: '{topic}'")
    return "+".join(words)


def _parse_arxiv_xml(xml_content: str) -> list[dict]:
    root = ET.fromstring(xml_content)
    results = []
    for entry in root.findall("atom:entry", NS):
        authors = [
            author.findtext("atom:name", namespaces=NS)
            for author in entry.findall("atom:author", NS)
        ]
        pdf_link = None
        for link in entry.findall("atom:link", NS):
            if link.attrib.get("type") == "application/pdf":
                pdf_link = link.attrib.get("href")
                break
        published = entry.findtext("atom:published", namespaces=NS, default="")
        publication_year = None
        if published:
            try:
                publication_year = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ").year
            except ValueError:
                publication_year = None
        results.append(
            {
                "id": entry.findtext("atom:id", namespaces=NS, default=""),
                "title": (entry.findtext("atom:title", namespaces=NS) or "").strip(),
                "authors": [author for author in authors if author],
                "abstract": entry.findtext("atom:summary", namespaces=NS, default="").strip(),
                "publication_year": publication_year,
                "source": "arXiv",
                "pdf_link": pdf_link,
                "citation_count": None,
            }
        )
    return results

