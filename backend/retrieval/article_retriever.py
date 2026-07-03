"""Article retrieval scoped to the selected article vector ref."""

from .vector_store import vector_store


def retrieve_from_article(query: str, article: dict | None, top_k: int) -> list[dict]:
    if not article or not article.get("vector_ref"):
        return []
    return vector_store.search_article(query, article["vector_ref"], top_k)

