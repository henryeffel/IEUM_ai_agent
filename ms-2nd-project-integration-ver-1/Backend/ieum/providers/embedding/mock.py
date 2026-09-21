import hashlib
import math
import os

from ieum.providers.embedding.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    @property
    def provider_name(self) -> str:
        return "mock_embedding"

    @property
    def model_id(self) -> str:
        return f"mock_embedding_{self.dimension}"

    @property
    def dimension(self) -> int:
        return int(os.getenv("MOCK_EMBEDDING_DIMENSION", "64"))

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        normalized = " ".join(text.lower().split())
        for token in normalized.split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for offset in range(0, len(digest), 2):
                index = int.from_bytes(digest[offset : offset + 2], "big")
                vector[index % self.dimension] += 1.0
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]
