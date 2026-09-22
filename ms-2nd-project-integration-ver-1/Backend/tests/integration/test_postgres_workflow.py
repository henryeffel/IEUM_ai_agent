import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text


if (
    not os.getenv("DATABASE_URL", "").startswith("postgresql")
    or os.getenv("IEUM_INTEGRATION_DATABASE") != "1"
):
    pytest.skip(
        "전용 PostgreSQL DATABASE_URL과 IEUM_INTEGRATION_DATABASE=1이 필요합니다.",
        allow_module_level=True,
    )

os.environ["APP_MODE"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["PRODUCTIVITY_PROVIDER"] = "mock"
os.environ["MOCK_PRODUCTIVITY_SCENARIO"] = "success"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["MOCK_EMBEDDING_DIMENSION"] = "2048"
os.environ["VECTOR_SEARCH_PROVIDER"] = "pgvector"

from ieum.database import get_engine, get_session_factory
from ieum.providers.embedding.factory import get_embedding_provider
from ieum.providers.embedding.mock import MockEmbeddingProvider
from ieum.providers.vector_search.pgvector import PgVectorSearchProvider
from ieum.demo.reindex import reindex_all
from ieum.schemas.knowledge import DocumentChunkInput
from ieum.providers.llm.factory import get_llm_provider
from ieum.providers.productivity.factory import get_productivity_provider
from ieum.providers.vector_search.factory import get_vector_search_provider
from ieum.services.action_workflow import get_action_workflow_service
from main import app


actor = "alfzm102435@gmail.com"


@pytest.fixture(autouse=True)
def clean_postgres_database():
    get_action_workflow_service.cache_clear()
    get_productivity_provider.cache_clear()
    get_vector_search_provider.cache_clear()
    get_embedding_provider.cache_clear()
    get_llm_provider.cache_clear()
    get_session_factory.cache_clear()
    get_engine.cache_clear()

    command.downgrade(Config("alembic.ini"), "base")
    command.upgrade(Config("alembic.ini"), "head")
    engine = get_engine()

    yield

    get_action_workflow_service.cache_clear()
    get_productivity_provider.cache_clear()
    get_vector_search_provider.cache_clear()
    get_embedding_provider.cache_clear()
    get_llm_provider.cache_clear()
    engine.dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()


def _calendar_action():
    return {
        "action_id": f"calendar-{uuid4()}",
        "payload": {
            "tool": "calendar",
            "title": "PostgreSQL 동시성 검증",
            "start_at": "2026-08-05T14:00:00+09:00",
            "end_at": "2026-08-05T15:00:00+09:00",
            "attendees": [],
        },
    }


def test_pgvector_stores_and_searches_2048_dimension_embedding():
    with TestClient(app) as client:
        indexed = client.post(
            "/api/v1/knowledge/chunks",
            json={
                "chunks": [
                    {
                        "chunk_id": "policy-1",
                        "document_id": "policy",
                        "title": "마케팅 예산 정책",
                        "content": "마케팅 광고 예산은 삼천만 원으로 승인되었습니다.",
                        "category": "reference",
                        "chunk_index": 0,
                        "source_url": "https://example.invalid/policy",
                    }
                ]
            },
        )
        assert indexed.status_code == 201

        searched = client.post(
            "/api/v1/knowledge/search",
            json={
                "query": "마케팅 광고 예산은 삼천만 원으로 승인되었습니다.",
                "top_k": 1,
                "min_score": 0.99,
            },
        )

    assert searched.status_code == 200
    body = searched.json()
    assert body["provider"] == "pgvector"
    assert body["grounded"] is True
    assert body["hits"][0]["chunk_id"] == "policy-1"

    with get_engine().connect() as connection:
        dimension = connection.execute(
            text(
                "SELECT vector_dims(embedding) "
                "FROM document_chunks WHERE chunk_id = 'policy-1'"
            )
        ).scalar_one()
    assert dimension == 2048


def test_reindex_switches_search_to_new_embedding_model():
    class VersionedEmbedding(MockEmbeddingProvider):
        def __init__(self, model_id):
            self._model_id = model_id

        @property
        def model_id(self):
            return self._model_id

    old = PgVectorSearchProvider(VersionedEmbedding("retired-model"))
    new_embedding = VersionedEmbedding("replacement-model")
    new = PgVectorSearchProvider(new_embedding)
    old.index_chunks([DocumentChunkInput(
        chunk_id="migration-check",
        document_id="migration-check",
        title="출장비 규정",
        content="출장비는 영수증을 첨부합니다.",
        category="policy",
        chunk_index=0,
    )])
    assert new.search("출장비는 영수증을 첨부합니다.", category=None, top_k=1, min_score=0) == []

    assert reindex_all(new_embedding, get_session_factory()) == 1
    hits = new.search("출장비는 영수증을 첨부합니다.", category=None, top_k=1, min_score=0)
    assert [hit.chunk_id for hit in hits] == ["migration-check"]
    with get_engine().connect() as connection:
        model = connection.execute(text(
            "SELECT embedding_model FROM document_chunks WHERE chunk_id = 'migration-check'"
        )).scalar_one()
    assert model == "replacement-model"


def test_postgres_concurrent_execution_claims_plan_once():
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/action-plans",
            json={
                "meeting_id": f"meeting-{uuid4()}",
                "actions": [_calendar_action()],
            },
        )
        assert created.status_code == 201
        plan_id = created.json()["id"]

        approved = client.post(
            f"/api/v1/action-plans/{plan_id}/approve",
            json={"actor": actor},
        )
        assert approved.status_code == 200

    def execute():
        with TestClient(app) as concurrent_client:
            return concurrent_client.post(
                f"/api/v1/action-plans/{plan_id}/execute"
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: execute(), range(2)))

    assert sorted(statuses) == [200, 409]

    with TestClient(app) as client:
        stored = client.get(f"/api/v1/action-plans/{plan_id}").json()
    assert stored["status"] == "SUCCEEDED"
    assert stored["actions"][0]["attempts"] == 1
    assert stored["actions"][0]["external_resource_id"]


def test_meeting_to_grounded_action_executes_end_to_end():
    meeting_id = f"meeting-e2e-{uuid4()}"
    transcript = (
        "신제품 마케팅 광고 예산을 검토했고 후속 작업을 "
        "할 일 목록으로 관리하기로 결정했습니다."
    )

    with TestClient(app) as client:
        indexed = client.post(
            "/api/v1/knowledge/chunks",
            json={
                "chunks": [
                    {
                        "chunk_id": "marketing-policy-e2e",
                        "document_id": "marketing-policy",
                        "title": "마케팅 예산 후속 작업 정책",
                        "content": (
                            "신제품 마케팅 광고 예산 검토 후 후속 작업은 "
                            "Microsoft To Do에서 관리합니다."
                        ),
                        "category": "history",
                        "chunk_index": 0,
                        "source_url": "https://example.invalid/marketing-policy",
                    }
                ]
            },
        )
        assert indexed.status_code == 201

        planned = client.post(
            "/api/v1/action-plans/grounded",
            json={
                "meeting_id": meeting_id,
                "transcript": transcript,
                "category": "history",
                "top_k": 3,
                "min_score": -1.0,
            },
        )
        assert planned.status_code == 201
        plan = planned.json()
        plan_id = plan["id"]
        assert plan["status"] == "PENDING_APPROVAL"
        assert plan["evidence_chunk_ids"] == ["marketing-policy-e2e"]
        assert plan["actions"][0]["tool"] == "todo"
        assert "marketing-policy-e2e" in (
            plan["actions"][0]["payload"]["description"]
        )

        approved = client.post(
            f"/api/v1/action-plans/{plan_id}/approve",
            json={"actor": actor},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "APPROVED"

        executed = client.post(f"/api/v1/action-plans/{plan_id}/execute")
        assert executed.status_code == 200
        result = executed.json()

        stored = client.get(f"/api/v1/action-plans/{plan_id}")
        assert stored.status_code == 200

    assert result["meeting_id"] == meeting_id
    assert result["status"] == "SUCCEEDED"
    assert result["evidence_chunk_ids"] == ["marketing-policy-e2e"]
    assert result["actions"][0]["status"] == "SUCCEEDED"
    assert result["actions"][0]["attempts"] == 1
    assert result["actions"][0]["provider"] == "mock_microsoft_365"
    assert result["actions"][0]["external_resource_id"].startswith(
        "mock-todo-"
    )
    assert stored.json() == result
