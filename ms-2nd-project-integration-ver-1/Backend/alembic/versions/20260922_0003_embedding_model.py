"""Track the model that produced each knowledge embedding."""

from alembic import op
import sqlalchemy as sa

revision = "20260922_0003"
down_revision = "20260807_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("document_chunks", sa.Column("embedding_model", sa.String(200), nullable=True))


def downgrade():
    op.drop_column("document_chunks", "embedding_model")
