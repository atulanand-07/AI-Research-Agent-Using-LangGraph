from backend.search import arxiv_client, semantic_scholar_client, wikipedia_search_client
from backend.search.article_ranker import _dedupe


EXPECTED_KEYS = {
    "id",
    "title",
    "authors",
    "abstract",
    "publication_year",
    "source",
    "pdf_link",
    "citation_count",
}


def test_search_client_schema_parsers(monkeypatch):
    arxiv_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/1</id>
        <title>Test Paper</title>
        <summary>Abstract</summary>
        <published>2024-01-01T00:00:00Z</published>
        <author><name>Ada</name></author>
        <link type="application/pdf" href="http://arxiv.org/pdf/1"/>
      </entry>
    </feed>"""

    class Response:
        ok = True
        text = arxiv_xml

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {
                        "paperId": "s1",
                        "title": "Semantic Paper",
                        "authors": [{"name": "Ada"}],
                        "abstract": "Abstract",
                        "year": 2024,
                        "citationCount": 2,
                        "openAccessPdf": {"url": "https://example.com/p.pdf"},
                    }
                ],
                "query": {
                    "search": [
                        {
                            "pageid": 1,
                            "title": "Wiki Paper",
                            "snippet": "Abstract",
                        }
                    ]
                },
            }

    monkeypatch.setattr(arxiv_client.requests, "get", lambda *a, **k: Response())
    monkeypatch.setattr(semantic_scholar_client.requests, "get", lambda *a, **k: Response())
    monkeypatch.setattr(wikipedia_search_client.requests, "get", lambda *a, **k: Response())

    results = [
        arxiv_client.search_arxiv("test", 1)[0],
        semantic_scholar_client.search_semantic_scholar("test", 1)[0],
        wikipedia_search_client.search_wikipedia("test", 1)[0],
    ]
    assert all(set(result.keys()) == EXPECTED_KEYS for result in results)


def test_ranker_dedupes_normalized_titles():
    results = _dedupe(
        [
            {"title": "Same: Title!", "publication_year": 2020, "citation_count": 1},
            {"title": "same title", "publication_year": 2024, "citation_count": 1},
        ]
    )
    assert len(results) == 1
    assert results[0]["publication_year"] == 2024

