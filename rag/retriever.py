from typing import Any

from vector_store.semantic_search import SemanticSearch


class SemanticContextRetriever:
    def __init__(self) -> None:
        self.search = SemanticSearch()

    def retrieve_context(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return self.search.similar(query, limit=limit)
