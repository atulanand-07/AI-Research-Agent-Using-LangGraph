"""Pydantic API models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..state import SourceStatus


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    knowledge_mode: str = Field(pattern="^(general|sources|article|hybrid)$")


class ChatResponse(BaseModel):
    answer: str
    followup_questions: list[str]
    active_sources_used: list[str]
    knowledge_mode: str


class WikiRequest(BaseModel):
    url_or_topic: str = Field(min_length=1)


class SourceResponse(BaseModel):
    source_id: str
    status: SourceStatus


class SelectArticleRequest(BaseModel):
    article: dict


class SelectArticleResponse(BaseModel):
    article_id: str
    status: SourceStatus

