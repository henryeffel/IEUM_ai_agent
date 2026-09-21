import pytest

from ieum.demo.embedding_probe import probe_embedding


class Provider:
    provider_name = "test"
    model_id = "new-model"
    dimension = 2

    def embed_documents(self, _):
        return [[0.5, 0.5]]

    def embed_query(self, _):
        return [0.5, 0.5]


def test_probe_checks_both_embedding_modes():
    assert probe_embedding(Provider()) == {
        "provider": "test",
        "model": "new-model",
        "dimension": 2,
        "passage_count": 1,
        "query_count": 1,
    }


def test_probe_rejects_wrong_query_dimension():
    class BadProvider(Provider):
        def embed_query(self, _):
            return [0.5]

    with pytest.raises(RuntimeError, match="dimension"):
        probe_embedding(BadProvider())
