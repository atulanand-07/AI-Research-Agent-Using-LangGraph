from backend import nodes
from backend.graph import build_research_graph
from backend.retrieval.vector_store import vector_store
from backend.state import SourceStatus


class DummyResponse:
    def __init__(self, content):
        self.content = content


class DummyLLM:
    def invoke(self, prompt):
        if "follow-up" in prompt.lower():
            return DummyResponse("What supports this?\nWhat are the limits?\nWhat next?")
        return DummyResponse("Test answer")


def base_state(mode):
    return {
        "query": "What is attention?",
        "knowledge_mode": mode,
        "chat_history": [],
        "uploaded_sources": [],
        "selected_article": None,
        "article_results": [],
        "retrieved_chunks": [],
        "article_chunks": [],
        "merged_context": [],
        "answer": "",
        "followup_questions": [],
        "active_sources_used": [],
    }


def test_general_mode_invokes(monkeypatch):
    monkeypatch.setattr(nodes, "llm", DummyLLM())
    result = build_research_graph().invoke(base_state("general"))
    assert result["knowledge_mode"] == "general"
    assert len(result["followup_questions"]) == 3
    assert result["active_sources_used"] == result["chat_history"][-1]["grounded_in"]


def test_sources_mode_falls_back_without_ready_sources(monkeypatch):
    monkeypatch.setattr(nodes, "llm", DummyLLM())
    state = base_state("sources")
    result = build_research_graph().invoke(state)
    assert result["knowledge_mode"] == "general"
    assert result["active_sources_used"] == []


def test_all_grounded_modes_invoke(monkeypatch):
    monkeypatch.setattr(nodes, "llm", DummyLLM())
    vector_store.add_source_chunks("source:one", "LangGraph.pdf", ["attention uses queries"])
    vector_store.replace_article("article:one", "Attention Paper", ["attention paper text"])

    for mode in ("sources", "article", "hybrid"):
        state = base_state(mode)
        state["uploaded_sources"] = [
            {
                "id": "one",
                "filename": "LangGraph.pdf",
                "source_type": "pdf",
                "status": SourceStatus.READY,
                "vector_ref": "source:one",
            }
        ]
        state["selected_article"] = {
            "id": "article-one",
            "title": "Attention Paper",
            "authors": [],
            "status": SourceStatus.READY,
            "vector_ref": "article:one",
        }
        result = build_research_graph().invoke(state)
        assert result["knowledge_mode"] == mode
        assert result["active_sources_used"] == result["chat_history"][-1]["grounded_in"]
        assert 3 <= len(result["followup_questions"]) <= 5


def test_general_mode_prompt_does_not_mention_context(monkeypatch):
    prompts_received = []

    class CapturingLLM:
        def invoke(self, prompt):
            prompts_received.append(prompt)
            if "follow-up" in prompt.lower():
                return DummyResponse("What supports this?\nWhat are the limits?\nWhat next?")
            return DummyResponse("Test answer")

    monkeypatch.setattr(nodes, "llm", CapturingLLM())
    state = base_state("general")
    build_research_graph().invoke(state)
    
    # Assert that the prompt sent to LLM for general chat did not mention retrieved context
    general_chat_prompt = prompts_received[0]
    assert "retrieved context" not in general_chat_prompt.lower()
    assert "no retrieved context" not in general_chat_prompt.lower()
    assert "conversation history:" in general_chat_prompt.lower()

