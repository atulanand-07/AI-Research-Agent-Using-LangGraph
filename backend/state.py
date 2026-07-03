"""ResearchState - the single state object passed between every node."""

from enum import Enum
from typing import Literal, TypedDict


class SourceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class UploadedSource(TypedDict):
    id: str
    filename: str
    source_type: Literal["pdf", "wikipedia"]
    status: SourceStatus
    vector_ref: str | None


class SelectedArticle(TypedDict):
    id: str
    title: str
    authors: list[str]
    status: SourceStatus
    vector_ref: str | None


class ChatTurn(TypedDict):
    role: Literal["user", "assistant"]
    content: str
    mode: str | None
    grounded_in: list[str]


class ResearchState(TypedDict):
    query: str
    knowledge_mode: Literal["general", "sources", "article", "hybrid"]
    chat_history: list[ChatTurn]
    uploaded_sources: list[UploadedSource]
    selected_article: SelectedArticle | None
    article_results: list[dict]
    retrieved_chunks: list[dict]
    article_chunks: list[dict]
    merged_context: list[dict]
    answer: str
    followup_questions: list[str]
    active_sources_used: list[str]

