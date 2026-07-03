"""Source retrieval scoped to ready uploaded source vector refs."""

from .vector_store import vector_store


def retrieve_from_sources(query: str, sources: list[dict], top_k: int) -> list[dict]:
    vector_refs = [source["vector_ref"] for source in sources if source.get("vector_ref")]
    if not vector_refs:
        return []
    return vector_store.search_sources(query, vector_refs, top_k)

