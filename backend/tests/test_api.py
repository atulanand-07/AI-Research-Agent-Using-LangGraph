import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from backend.main import app
from backend.session_store import session_store
from backend.state import SourceStatus


def test_history_persists_chat(monkeypatch):
    from backend import nodes

    class Response:
        def __init__(self, content):
            self.content = content

    class LLM:
        def invoke(self, prompt):
            if "follow-up" in prompt.lower():
                return Response("What changed?\nWhy?\nWhat next?")
            return Response("Answer")

    monkeypatch.setattr(nodes, "llm", LLM())
    client = TestClient(app)
    response = client.post(
        "/chat",
        headers={"x-session-id": "api-test"},
        json={"query": "Hello", "knowledge_mode": "general"},
    )
    assert response.status_code == 200
    history = client.get("/history", headers={"x-session-id": "api-test"}).json()
    assert len(history["chat_history"]) == 2


def test_select_article_replaces_previous():
    client = TestClient(app)
    first = {"id": "a", "title": "First", "authors": [], "abstract": "One"}
    second = {"id": "b", "title": "Second", "authors": [], "abstract": "Two"}
    client.post("/select-article", headers={"x-session-id": "article-test"}, json={"article": first})
    client.post("/select-article", headers={"x-session-id": "article-test"}, json={"article": second})
    selected = session_store.get("article-test")["selected_article"]
    assert selected["id"] == "b"
    assert selected["status"] in {SourceStatus.PENDING, SourceStatus.PROCESSING, SourceStatus.READY}

