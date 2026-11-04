"""Add shared operational rate limits without changing corpus rows."""
from alembic import op
import sqlalchemy as sa

revision = "0006_shared_rate_limits"
down_revision = "0005_record_publication"
branch_labels = depends_on = None


def upgrade():
    op.create_table("rate_limit_buckets",
                    sa.Column("id", sa.String(64), primary_key=True),
                    sa.Column("events", sa.JSON(), nullable=False),
                    sa.Column("expires_at", sa.Float(), nullable=False))
    op.create_index("ix_rate_limit_buckets_expires_at", "rate_limit_buckets", ["expires_at"])


def downgrade():
    # Only short-lived request accounting is removed; no content or rights change.
    op.drop_index("ix_rate_limit_buckets_expires_at", table_name="rate_limit_buckets")
    op.drop_table("rate_limit_buckets")
