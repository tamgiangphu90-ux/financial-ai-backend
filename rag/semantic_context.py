from typing import Any

from rag.retriever import SemanticContextRetriever


def build_semantic_context(query: str) -> dict[str, Any]:
    matches = SemanticContextRetriever().retrieve_context(query)
    return {"matches": matches, "count": len(matches)}
