"""Re-embed every stored knowledge chunk before switching models."""

from sqlalchemy import select

from ieum.models.knowledge import DocumentChunkModel


def reindex_all(embedding_provider, session_factory, *, batch_size: int = 32) -> int:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    with session_factory() as session:
        rows = list(session.execute(select(DocumentChunkModel.chunk_id, DocumentChunkModel.content)))
    if not rows:
        return 0

    # Complete every external request before changing the database. Any API error
    # leaves the existing index intact.
    replacements = []
    for offset in range(0, len(rows), batch_size):
        batch = rows[offset : offset + batch_size]
        vectors = embedding_provider.embed_documents([content for _, content in batch])
        if len(vectors) != len(batch):
            raise RuntimeError("Embedding API returned an unexpected vector count")
        if any(len(vector) != embedding_provider.dimension for vector in vectors):
            raise RuntimeError("Embedding API returned an unexpected vector dimension")
        replacements.extend(zip((chunk_id for chunk_id, _ in batch), vectors, strict=True))

    with session_factory() as session:
        with session.begin():
            # Prevent concurrent seed or indexing writes during the replacement.
            current_rows = list(session.execute(
                select(DocumentChunkModel.chunk_id, DocumentChunkModel.content).with_for_update()
            ))
            if dict(current_rows) != dict(rows):
                raise RuntimeError("Knowledge chunks changed during reindex; retry")
            for chunk_id, vector in replacements:
                chunk = session.get(DocumentChunkModel, chunk_id)
                chunk.embedding = vector
                chunk.embedding_model = embedding_provider.model_id
    return len(rows)
