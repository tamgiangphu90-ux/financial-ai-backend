from typing import Any

from vector_store.vector_index import VectorIndex


class SemanticSearch:
    def __init__(self) -> None:
        self.index = VectorIndex()

    def remember(self, document_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        self.index.add_text(document_id, text, metadata)

    def similar(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return self.index.query(query, limit=limit)
