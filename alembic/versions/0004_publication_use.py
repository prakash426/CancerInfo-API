"""Add explicit use and output approvals without changing any rights decisions."""
from alembic import op
import sqlalchemy as sa

revision = "0004_publication_use"
down_revision = "0003_who_provenance"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("source_documents", sa.Column("noncommercial_redistribution_allowed", sa.Boolean(), nullable=True))
    op.add_column("source_documents", sa.Column("approved_publication_content_types", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("source_documents", "approved_publication_content_types")
    op.drop_column("source_documents", "noncommercial_redistribution_allowed")
