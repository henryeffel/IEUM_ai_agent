"""Read-only check of the configured embedding endpoint."""

import math


PROBE_TEXT = "출장비가 10만 원 이상이면 팀장 승인이 필요합니다."


def probe_embedding(provider) -> dict[str, str | int]:
    passage = provider.embed_documents([PROBE_TEXT])
    query = provider.embed_query("출장비 10만 원 이상 승인 규정")
    if len(passage) != 1:
        raise RuntimeError("Embedding API returned an unexpected passage count")
    if len(passage[0]) != provider.dimension or len(query) != provider.dimension:
        raise RuntimeError("Embedding API returned an unexpected dimension")
    if not all(math.isfinite(value) for value in passage[0] + query):
        raise RuntimeError("Embedding API returned non-finite values")
    return {
        "provider": provider.provider_name,
        "model": provider.model_id,
        "dimension": provider.dimension,
        "passage_count": len(passage),
        "query_count": 1,
    }
