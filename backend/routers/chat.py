"""Chat, history, and session endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Header

from ..graph import research_graph
from ..session_store import session_store
from .schemas import ChatRequest, ChatResponse

router = APIRouter()


def _session_id(value: str | None) -> str:
    return value or "default"


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, x_session_id: str | None = Header(default=None)):
    session_id = _session_id(x_session_id)
    state = session_store.build_state(session_id, request.query, request.knowledge_mode)
    state["chat_history"].append(
        {
            "role": "user",
            "content": request.query,
            "mode": request.knowledge_mode,
            "grounded_in": [],
        }
    )
    result = research_graph.invoke(state)
    session_store.update(
        session_id,
        chat_history=result["chat_history"],
        article_results=result["article_results"],
    )
    return {
        "answer": result["answer"],
        "followup_questions": result["followup_questions"],
        "active_sources_used": result["active_sources_used"],
        "knowledge_mode": result["knowledge_mode"],
    }


@router.get("/history")
def history(x_session_id: str | None = Header(default=None)):
    return {"chat_history": session_store.get(_session_id(x_session_id))["chat_history"]}


@router.get("/session")
def session(x_session_id: str | None = Header(default=None)):
    current = session_store.get(_session_id(x_session_id))
    return {
        "chat_history": current["chat_history"],
        "uploaded_sources": current["uploaded_sources"],
        "selected_article": current["selected_article"],
        "article_results": current["article_results"],
    }
