import os

os.environ["APP_MODE"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_ready_reports_mock_provider():
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["llm_provider"] == "mock"
    assert response.json()["embedding_provider"] == "mock_embedding"
    assert response.json()["embedding_model"] == "mock_embedding_64"
    assert response.json()["azure_providers_loaded"] is False


def test_analyze_meeting_returns_validated_structure():
    response = client.post(
        "/api/v1/meetings/analyze",
        json={
            "transcript": (
                "김대리는 다음 주까지 제안서를 작성합니다. "
                "박팀장은 완료된 제안서를 검토합니다."
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["provider"] == "mock"
    assert body["data"]["summary"]
    assert isinstance(body["data"]["decisions"], list)
    assert isinstance(body["data"]["action_items"], list)
    assert isinstance(body["data"]["open_issues"], list)


def test_analyze_meeting_rejects_short_transcript():
    response = client.post(
        "/api/v1/meetings/analyze",
        json={"transcript": "짧음"},
    )

    assert response.status_code == 422
