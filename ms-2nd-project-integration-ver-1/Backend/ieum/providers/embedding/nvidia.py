import os

from openai import OpenAI

from ieum.providers.embedding.base import EmbeddingProvider


class NvidiaEmbeddingProvider(EmbeddingProvider):
    _dimension = 2048

    def __init__(self):
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY 환경변수가 필요합니다.")
        self._model = os.getenv(
            "NVIDIA_EMBEDDING_MODEL",
            "nvidia/nemotron-3-embed-1b",
        )
        self._client = OpenAI(
            base_url=os.getenv(
                "NVIDIA_BASE_URL",
                "https://integrate.api.nvidia.com/v1",
            ),
            api_key=api_key,
            timeout=float(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "60")),
            max_retries=1,
        )

    @property
    def provider_name(self) -> str:
        return "nvidia_embedding"

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(
            model=self._model,
            input=texts,
            encoding_format="float",
            extra_body={"input_type": "passage", "truncate": "END"},
        )
        vectors = [item.embedding for item in response.data]
        self._validate_dimensions(vectors)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        response = self._client.embeddings.create(
            model=self._model,
            input=[text],
            encoding_format="float",
            extra_body={"input_type": "query", "truncate": "END"},
        )
        vector = response.data[0].embedding
        self._validate_dimensions([vector])
        return vector

    def _validate_dimensions(self, vectors: list[list[float]]):
        if any(len(vector) != self.dimension for vector in vectors):
            raise RuntimeError("NVIDIA 임베딩 벡터 차원이 예상과 다릅니다.")
