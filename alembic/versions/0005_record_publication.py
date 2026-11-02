"""Bind published source excerpts to exact reviewed records and citations."""
from alembic import op
import sqlalchemy as sa
revision = "0005_record_publication"
down_revision = "0004_publication_use"
branch_labels = depends_on = None


def upgrade():
    op.add_column("source_documents", sa.Column("publication_record_reviews", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("source_documents", "publication_record_reviews")
