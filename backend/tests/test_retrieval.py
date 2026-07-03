from backend.retrieval.article_retriever import retrieve_from_article
from backend.retrieval.sources_retriever import retrieve_from_sources
from backend.retrieval.vector_store import vector_store


def test_source_retrieval_scopes_to_passed_refs():
    vector_store.add_source_chunks("source:a", "A.pdf", ["alpha beta"])
    vector_store.add_source_chunks("source:b", "B.pdf", ["gamma delta"])
    chunks = retrieve_from_sources(
        "gamma",
        [{"vector_ref": "source:b", "filename": "B.pdf"}],
        top_k=5,
    )
    assert chunks
    assert {chunk["source_name"] for chunk in chunks} == {"B.pdf"}


def test_article_retrieval_scopes_to_selected_ref():
    vector_store.replace_article("article:a", "Article A", ["neural ranking"])
    chunks = retrieve_from_article("neural", {"vector_ref": "article:a"}, top_k=5)
    assert chunks
    assert chunks[0]["source_name"] == "Article A"

