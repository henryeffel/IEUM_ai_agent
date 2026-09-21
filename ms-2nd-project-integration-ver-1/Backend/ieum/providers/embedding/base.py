from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return a stable provider identifier."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding vector dimension."""

    @property
    def model_id(self) -> str:
        """Identify the vector space used by this provider."""
        return self.provider_name

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document chunks."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a search query."""
