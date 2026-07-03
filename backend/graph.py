"""Graph assembly for the AI Research Agent."""

from __future__ import annotations

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - exercised only without dependencies
    END = "__end__"
    StateGraph = None

from .nodes import (
    article_retrieval_node,
    followup_generator_node,
    general_chat_node,
    hybrid_context_node,
    response_generator_node,
    retrieval_node,
    route_by_mode,
    supervisor_node,
)
from .state import ResearchState


class _LinearFallbackGraph:
    def invoke(self, state: ResearchState) -> ResearchState:
        state = supervisor_node(state)
        branch = route_by_mode(state)
        if branch == "retrieval":
            state = retrieval_node(state)
        elif branch == "article_retrieval":
            state = article_retrieval_node(state)
        elif branch == "hybrid_context":
            state = hybrid_context_node(state)
        else:
            state = general_chat_node(state)
        state = response_generator_node(state)
        return followup_generator_node(state)


def build_research_graph():
    if StateGraph is None:
        return _LinearFallbackGraph()

    graph = StateGraph(ResearchState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("general_chat", general_chat_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("article_retrieval", article_retrieval_node)
    graph.add_node("hybrid_context", hybrid_context_node)
    graph.add_node("response_generator", response_generator_node)
    graph.add_node("followup_generator", followup_generator_node)
    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_by_mode,
        {
            "general_chat": "general_chat",
            "retrieval": "retrieval",
            "article_retrieval": "article_retrieval",
            "hybrid_context": "hybrid_context",
        },
    )
    graph.add_edge("general_chat", "response_generator")
    graph.add_edge("retrieval", "response_generator")
    graph.add_edge("article_retrieval", "response_generator")
    graph.add_edge("hybrid_context", "response_generator")
    graph.add_edge("response_generator", "followup_generator")
    graph.add_edge("followup_generator", END)
    return graph.compile()


research_graph = build_research_graph()

