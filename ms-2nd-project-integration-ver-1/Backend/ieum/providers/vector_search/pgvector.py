from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from ieum.database import get_engine, get_session_factory
from ieum.models.knowledge import DocumentChunkModel
from ieum.providers.embedding.base import EmbeddingProvider
from ieum.providers.vector_search.base import VectorSearchProvider
from ieum.schemas.knowledge import DocumentChunkInput, KnowledgeSearchHit


class PgVectorSearchProvider(VectorSearchProvider):
    def __init__(self, embedding_provider: EmbeddingProvider):
        if embedding_provider.dimension != 2048:
            raise RuntimeError("pgvector Provider는 2048차원 임베딩이 필요합니다.")
        self.embedding_provider = embedding_provider
        if get_engine().dialect.name != "postgresql":
            raise RuntimeError(
                "VECTOR_SEARCH_PROVIDER=pgvector는 PostgreSQL DATABASE_URL이 필요합니다."
            )

    @property
    def provider_name(self) -> str:
        return "pgvector"

    def index_chunks(self, chunks: list[DocumentChunkInput]) -> int:
        vectors = self.embedding_provider.embed_documents(
            [chunk.content for chunk in chunks]
        )
        rows = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            rows.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "title": chunk.title,
                    "content": chunk.content,
                    "category": chunk.category,
                    "chunk_index": chunk.chunk_index,
                    "section": chunk.section,
                    "source_url": chunk.source_url,
                    "document_created_at": chunk.created_at,
                    "document_updated_at": chunk.updated_at,
                    "embedding": vector,
                    "embedding_model": self.embedding_provider.model_id,
                }
            )
        statement = insert(DocumentChunkModel).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=[DocumentChunkModel.chunk_id],
            set_={
                key: getattr(statement.excluded, key)
                for key in rows[0]
                if key != "chunk_id"
            },
        )
        with get_session_factory()() as session:
            session.execute(statement)
            session.commit()
        return len(rows)

    def search(
        self,
        query: str,
        *,
        category: str | None,
        top_k: int,
        min_score: float,
    ) -> list[KnowledgeSearchHit]:
        vector = self.embedding_provider.embed_query(query)
        distance = DocumentChunkModel.embedding.cosine_distance(vector)
        statement = select(
            DocumentChunkModel,
            distance.label("distance"),
        ).where(DocumentChunkModel.embedding_model == self.embedding_provider.model_id)
        if category:
            statement = statement.where(
                DocumentChunkModel.category == category
            )
        statement = statement.order_by(distance).limit(top_k)

        hits = []
        with get_session_factory()() as session:
            for chunk, cosine_distance in session.execute(statement):
                score = 1.0 - float(cosine_distance)
                if score < min_score:
                    continue
                hits.append(
                    KnowledgeSearchHit(
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        title=chunk.title,
                        content=chunk.content,
                        category=chunk.category,
                        chunk_index=chunk.chunk_index,
                        section=chunk.section,
                        source_url=chunk.source_url,
                        created_at=chunk.document_created_at,
                        updated_at=chunk.document_updated_at,
                        score=score,
                    )
                )
        return hits
