"""In-memory session persistence for v1."""

from __future__ import annotations

import threading
from copy import deepcopy

from .state import ResearchState


def _empty_session() -> dict:
    return {
        "chat_history": [],
        "uploaded_sources": [],
        "selected_article": None,
        "article_results": [],
    }


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}
        self._lock = threading.RLock()

    def get(self, session_id: str) -> dict:
        with self._lock:
            session = self._sessions.setdefault(session_id, _empty_session())
            return deepcopy(session)

    def update(self, session_id: str, **values) -> dict:
        with self._lock:
            session = self._sessions.setdefault(session_id, _empty_session())
            session.update(values)
            return deepcopy(session)

    def build_state(self, session_id: str, query: str, knowledge_mode: str) -> ResearchState:
        session = self.get(session_id)
        return {
            "query": query,
            "knowledge_mode": knowledge_mode,
            "chat_history": session["chat_history"],
            "uploaded_sources": session["uploaded_sources"],
            "selected_article": session["selected_article"],
            "article_results": session["article_results"],
            "retrieved_chunks": [],
            "article_chunks": [],
            "merged_context": [],
            "answer": "",
            "followup_questions": [],
            "active_sources_used": [],
        }

    def mutate_source(self, session_id: str, source_id: str, **values) -> dict | None:
        with self._lock:
            session = self._sessions.setdefault(session_id, _empty_session())
            for source in session["uploaded_sources"]:
                if source["id"] == source_id:
                    source.update(values)
                    return deepcopy(source)
        return None


session_store = SessionStore()

