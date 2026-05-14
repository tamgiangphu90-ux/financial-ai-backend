from typing import Any

from utils.config import get_settings
from vector_store.embeddings import EmbeddingProvider


class VectorIndex:
    def __init__(self, collection_name: str = "financial_memory") -> None:
        self.collection_name = collection_name
        self.embedding_provider = EmbeddingProvider()
        self._fallback: list[dict[str, Any]] = []
        self._collection = None
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(get_settings().chroma_persist_dir))
            self._collection = client.get_or_create_collection(collection_name)
        except Exception:
            self._collection = None

    def add_text(self, document_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        embedding = self.embedding_provider.embed(text)
        if self._collection is not None:
            self._collection.upsert(
                ids=[document_id],
                documents=[text],
                metadatas=[metadata or {}],
                embeddings=[embedding],
            )
            return
        self._fallback.append({"id": document_id, "text": text, "metadata": metadata or {}, "embedding": embedding})

    def query(self, text: str, limit: int = 5) -> list[dict[str, Any]]:
        embedding = self.embedding_provider.embed(text)
        if self._collection is not None:
            result = self._collection.query(query_embeddings=[embedding], n_results=limit)
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]
            ids = result.get("ids", [[]])[0]
            return [
                {"id": item_id, "text": doc, "metadata": meta or {}, "distance": distance}
                for item_id, doc, meta, distance in zip(ids, documents, metadatas, distances)
            ]
        return sorted(
            (
                {
                    "id": item["id"],
                    "text": item["text"],
                    "metadata": item["metadata"],
                    "score": self._cosine(embedding, item["embedding"]),
                }
                for item in self._fallback
            ),
            key=lambda item: item["score"],
            reverse=True,
        )[:limit]

    def _cosine(self, a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))
