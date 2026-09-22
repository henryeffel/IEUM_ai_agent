import pytest

from ieum.demo.reindex import reindex_all
from ieum.providers.embedding.nvidia import NvidiaEmbeddingProvider


class ReadSession:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def execute(self, _):
        return self.rows


class FailingProvider:
    dimension = 2048
    model_id = "replacement-model"

    def embed_documents(self, _):
        raise RuntimeError("upstream failure")


def test_reindex_does_not_open_write_transaction_when_embedding_fails():
    calls = 0

    def session_factory():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise AssertionError("write transaction must not start")
        return ReadSession([("chunk-1", "원본 문서")])

    with pytest.raises(RuntimeError, match="upstream failure"):
        reindex_all(FailingProvider(), session_factory)
    assert calls == 1


def test_nvidia_default_model_is_current(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.delenv("NVIDIA_EMBEDDING_MODEL", raising=False)
    provider = NvidiaEmbeddingProvider()
    assert provider.model_id == "nvidia/nemotron-3-embed-1b"
    assert provider.dimension == 2048
