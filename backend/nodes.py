"""Node functions for the AI Research Agent LangGraph."""

from __future__ import annotations

import os
from dotenv import load_dotenv
from dataclasses import dataclass

from .retrieval.article_retriever import retrieve_from_article
from .retrieval.sources_retriever import retrieve_from_sources
from .state import ResearchState, SourceStatus

load_dotenv()


@dataclass
class _LocalResponse:
    content: str


class _FallbackLLM:
    def invoke(self, prompt: str) -> _LocalResponse:
        return _LocalResponse(
            "I can help with that. Configure GOOGLE_API_KEY to enable Gemini-backed answers."
        )


def _make_llm():
    if not os.getenv("GOOGLE_API_KEY"):
        return _FallbackLLM()
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        return _FallbackLLM()
    return ChatGoogleGenerativeAI(
        model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash-lite"),
        request_timeout=float(os.getenv("GOOGLE_REQUEST_TIMEOUT", "12")),
        retries=int(os.getenv("GOOGLE_RETRIES", "1")),
    )


llm = _make_llm()


def _invoke_llm(prompt: str) -> _LocalResponse:
    try:
        return llm.invoke(prompt)
    except Exception as exc:
        print(f"LLM invocation failed: {exc}")
        return _LocalResponse(
            "I could not reach the configured Gemini model quickly enough. "
            "Please try again, or check the backend model configuration."
        )


def supervisor_node(state: ResearchState) -> ResearchState:
    state["uploaded_sources"] = [
        s for s in state["uploaded_sources"] if s["status"] == SourceStatus.READY
    ]

    if state["selected_article"] and state["selected_article"]["status"] != SourceStatus.READY:
        state["selected_article"] = None

    mode = state["knowledge_mode"]
    has_sources = len(state["uploaded_sources"]) > 0
    has_article = state["selected_article"] is not None
    if (
        (mode == "sources" and not has_sources)
        or (mode == "article" and not has_article)
        or (mode == "hybrid" and not (has_sources and has_article))
    ):
        state["knowledge_mode"] = "general"

    return state


def route_by_mode(state: ResearchState) -> str:
    mode = state["knowledge_mode"]
    has_sources = len(state["uploaded_sources"]) > 0
    has_article = state["selected_article"] is not None

    if mode == "hybrid" and has_sources and has_article:
        return "hybrid_context"
    if mode == "sources" and has_sources:
        return "retrieval"
    if mode == "article" and has_article:
        return "article_retrieval"

    state["knowledge_mode"] = "general"
    return "general_chat"


def _build_general_prompt(state: ResearchState) -> str:
    history_str = "\n".join(
        f"{t['role']}: {t['content']}" for t in state["chat_history"][-6:]
    )
    return f"Conversation history:\n{history_str}\n\nQuestion: {state['query']}"


def general_chat_node(state: ResearchState) -> ResearchState:
    prompt = _build_general_prompt(state)
    response = _invoke_llm(prompt)
    state["answer"] = response.content
    state["retrieved_chunks"] = []
    state["article_chunks"] = []
    state["merged_context"] = []
    state["active_sources_used"] = []
    return state


def retrieval_node(state: ResearchState) -> ResearchState:
    chunks = retrieve_from_sources(state["query"], state["uploaded_sources"], top_k=5)
    state["retrieved_chunks"] = chunks
    state["article_chunks"] = []
    state["merged_context"] = chunks
    state["active_sources_used"] = sorted({c["source_name"] for c in chunks})
    return state


def article_retrieval_node(state: ResearchState) -> ResearchState:
    chunks = retrieve_from_article(state["query"], state["selected_article"], top_k=5)
    state["retrieved_chunks"] = []
    state["article_chunks"] = chunks
    state["merged_context"] = chunks
    state["active_sources_used"] = sorted({c["source_name"] for c in chunks})
    return state


def hybrid_context_node(state: ResearchState) -> ResearchState:
    source_chunks = retrieve_from_sources(state["query"], state["uploaded_sources"], top_k=3)
    article_chunks = retrieve_from_article(state["query"], state["selected_article"], top_k=3)
    state["retrieved_chunks"] = source_chunks
    state["article_chunks"] = article_chunks
    state["merged_context"] = source_chunks + article_chunks
    state["active_sources_used"] = sorted(
        {c["source_name"] for c in source_chunks + article_chunks}
    )
    return state


def response_generator_node(state: ResearchState) -> ResearchState:
    if state["merged_context"]:
        prompt = _build_prompt(state, context=state["merged_context"])
        response = _invoke_llm(prompt)
        state["answer"] = response.content

    state["chat_history"].append(
        {
            "role": "assistant",
            "content": state["answer"],
            "mode": state["knowledge_mode"],
            "grounded_in": state["active_sources_used"],
        }
    )
    return state


def followup_generator_node(state: ResearchState) -> ResearchState:
    prompt = f"""Based on this answer, generate exactly 3-5 short, distinct follow-up questions.
Mode: {state['knowledge_mode']}
Answer: {state['answer']}

Return only the questions, one per line, no numbering."""
    response = _invoke_llm(prompt)
    questions = _clean_followups(response.content)
    fallback = [
        "What evidence supports this?",
        "Can you summarize the key tradeoffs?",
        "What should I read next?",
        "How does this compare with related work?",
        "What are the open questions?",
    ]
    for question in fallback:
        if len(questions) >= 3:
            break
        if question not in questions:
            questions.append(question)
    state["followup_questions"] = questions[:5]
    return state


def _clean_followups(content: str) -> list[str]:
    questions: list[str] = []
    for line in content.splitlines():
        cleaned = line.strip().lstrip("-*0123456789. )").strip()
        if cleaned.startswith("I could not reach the configured Gemini model"):
            continue
        if cleaned and cleaned not in questions:
            questions.append(cleaned)
    return questions[:5]


def _build_prompt(state: ResearchState, context: list[dict] | None) -> str:
    history_str = "\n".join(
        f"[{t['mode'] or 'n/a'}"
        f"{' - grounded: ' + ', '.join(t['grounded_in']) if t.get('grounded_in') else ' - ungrounded'}] "
        f"{t['role']}: {t['content']}"
        for t in state["chat_history"][-6:]
    )
    context_str = "\n\n".join(c["text"] for c in context) if context else "No retrieved context."
    return f"""Conversation history:
{history_str}

Retrieved context:
{context_str}

Current question: {state['query']}

Answer using the retrieved context when available. If context is provided but doesn't
contain the answer, say so explicitly rather than guessing."""







