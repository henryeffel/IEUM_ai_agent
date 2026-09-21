"""Measure bundled demo retrieval without connecting to the database."""

import json
import math
from pathlib import Path

from ieum.providers.embedding.nvidia import NvidiaEmbeddingProvider
from ieum.ingestion import DocumentMetadata, chunk_document


SAMPLE_TRANSCRIPT = (
    "다음 주 수요일 고객사 부산 방문을 진행하기로 했습니다. "
    "교통편 예약과 출장비 정산 준비는 금요일까지 완료합니다. "
    "예상 출장비가 10만 원 이상이므로 사내 규정에 따른 팀장 승인도 요청하기로 했습니다."
)


def cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    denominator = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
    return numerator / denominator


def main() -> None:
    path = Path(__file__).resolve().parents[1] / "ieum" / "demo" / "seed_knowledge.json"
    documents = json.loads(path.read_text(encoding="utf-8"))
    provider = NvidiaEmbeddingProvider()
    chunks = [
        chunk
        for document in documents
        for chunk in chunk_document(
            document["content"],
            DocumentMetadata(
                document_id=document["document_id"],
                title=document["title"],
                category=document["category"],
                source_url=document.get("source_url"),
                updated_at=document.get("updated_at"),
            ),
            max_chars=800,
        )
    ]
    vectors = provider.embed_documents([chunk.content for chunk in chunks])
    query = provider.embed_query(SAMPLE_TRANSCRIPT)
    results = sorted(
        (
            (cosine(query, vector), chunk.chunk_id, chunk.title, chunk.category)
            for chunk, vector in zip(chunks, vectors, strict=True)
        ),
        reverse=True,
    )
    print(f"model={provider.model_id} chunks={len(chunks)} dimension={provider.dimension}")
    for rank, (score, chunk_id, title, category) in enumerate(results[:5], start=1):
        print(f"rank={rank} score={score:.4f} category={category} chunk_id={chunk_id} title={title}")


if __name__ == "__main__":
    main()
