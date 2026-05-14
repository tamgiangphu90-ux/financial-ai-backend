import hashlib
import math


class EmbeddingProvider:
    """Deterministic local embeddings, replaceable with hosted embeddings later."""

    def embed(self, text: str, dimensions: int = 384) -> list[float]:
        vector = [0.0] * dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 6) for value in vector]
