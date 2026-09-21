"""Read-only summary of stored embedding model IDs."""

from sqlalchemy import func, select

from ieum.models.knowledge import DocumentChunkModel


def get_index_status(session_factory, active_model: str) -> dict:
    statement = (
        select(DocumentChunkModel.embedding_model, func.count())
        .group_by(DocumentChunkModel.embedding_model)
    )
    with session_factory() as session:
        counts = {model or "<unlabeled>": count for model, count in session.execute(statement)}
    total = sum(counts.values())
    active = counts.get(active_model, 0)
    return {
        "active_model": active_model,
        "total_chunks": total,
        "active_chunks": active,
        "ready_for_search": total > 0 and active == total,
        "counts_by_model": counts,
    }
