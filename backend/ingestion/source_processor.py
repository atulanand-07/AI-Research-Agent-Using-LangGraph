"""Background processing for uploaded and Wikipedia sources."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from ..retrieval.vector_store import vector_store
from ..session_store import session_store
from ..state import SourceStatus
from .chunker import chunk_text
from .pdf_loader import load_pdf_text
from .wikipedia_loader import load_wikipedia_text


def process_pdf_source(session_id: str, source_id: str, path: str) -> None:
    session_store.mutate_source(session_id, source_id, status=SourceStatus.PROCESSING)
    try:
        text = load_pdf_text(path)
        chunks = chunk_text(text)
        vector_ref = f"source:{source_id}"
        source = session_store.mutate_source(session_id, source_id)
        source_name = source["filename"] if source else Path(path).name
        vector_store.add_source_chunks(vector_ref, source_name, chunks)
        session_store.mutate_source(
            session_id,
            source_id,
            status=SourceStatus.READY,
            vector_ref=vector_ref,
        )
    except Exception:
        session_store.mutate_source(session_id, source_id, status=SourceStatus.ERROR)


def process_wikipedia_source(session_id: str, source_id: str, url_or_topic: str) -> None:
    session_store.mutate_source(session_id, source_id, status=SourceStatus.PROCESSING)
    try:
        title, text = load_wikipedia_text(url_or_topic)
        chunks = chunk_text(text)
        vector_ref = f"source:{source_id}"
        vector_store.add_source_chunks(vector_ref, title, chunks)
        session_store.mutate_source(
            session_id,
            source_id,
            filename=title,
            status=SourceStatus.READY,
            vector_ref=vector_ref,
        )
    except Exception:
        session_store.mutate_source(session_id, source_id, status=SourceStatus.ERROR)


def process_selected_article(session_id: str, article: dict) -> None:
    vector_ref = f"article:{uuid4().hex}"
    title = article["title"]
    text = _article_text(article)
    chunks = chunk_text(text)
    vector_store.replace_article(vector_ref, title, chunks)
    session = session_store.get(session_id)
    selected = session["selected_article"]
    if selected:
        selected["status"] = SourceStatus.READY
        selected["vector_ref"] = vector_ref
        session_store.update(session_id, selected_article=selected)


def _article_text(article: dict) -> str:
    parts = [article.get("title", ""), article.get("abstract", "")]
    return "\n\n".join(part for part in parts if part)

