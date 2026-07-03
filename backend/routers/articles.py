"""Article search and selection endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Header, Query

from ..ingestion.source_processor import process_selected_article
from ..retrieval.vector_store import vector_store
from ..search.article_ranker import search_articles
from ..session_store import session_store
from ..state import SourceStatus
from .schemas import SelectArticleRequest, SelectArticleResponse

router = APIRouter()


def _session_id(value: str | None) -> str:
    return value or "default"


@router.get("/articles")
def articles(topic: str = Query(min_length=1), x_session_id: str | None = Header(default=None)):
    results = search_articles(topic)
    session_store.update(_session_id(x_session_id), article_results=results)
    return {"articles": results}


@router.post("/select-article", response_model=SelectArticleResponse)
def select_article(
    request: SelectArticleRequest,
    background_tasks: BackgroundTasks,
    x_session_id: str | None = Header(default=None),
):
    session_id = _session_id(x_session_id)
    vector_store.clear_article()
    article = request.article
    article_id = article.get("id") or uuid4().hex
    selected = {
        "id": article_id,
        "title": article.get("title", "Untitled article"),
        "authors": article.get("authors", []),
        "status": SourceStatus.PENDING,
        "vector_ref": None,
    }
    session_store.update(session_id, selected_article=selected)
    selected["status"] = SourceStatus.PROCESSING
    session_store.update(session_id, selected_article=selected)
    background_tasks.add_task(process_selected_article, session_id, article)
    return {"article_id": article_id, "status": SourceStatus.PENDING}

