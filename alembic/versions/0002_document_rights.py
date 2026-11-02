"""document_rights_and_consensus_linkage

Revision ID: 0002_document_rights
Revises: 0001_initial_schema
Create Date: 2026-09-27 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_document_rights'
down_revision: Union[str, Sequence[str], None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend source_documents with publication decision and rights metadata fields
    with op.batch_alter_table('source_documents', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('publication_status', sa.String(length=32), nullable=False, server_default='REVIEW_REQUIRED')
        )
        batch_op.add_column(
            sa.Column('rights_evidence_url', sa.String(length=1024), nullable=True)
        )
        batch_op.add_column(
            sa.Column('rights_reviewed_at', sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('rights_reviewer', sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column('permissible_use', sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column('commercial_redistribution_allowed', sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('redistribution_allowed', sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('full_text_storage_allowed', sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('derived_summary_allowed', sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('attribution_required', sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('attribution_text', sa.String(length=512), nullable=True)
        )
        batch_op.add_column(
            sa.Column('reuse_restrictions', sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('quarantine_reason', sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('third_party_permission_status', sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column('third_party_permission_notes', sa.Text(), nullable=True)
        )
        batch_op.create_index(batch_op.f('ix_source_documents_publication_status'), ['publication_status'], unique=False)

    # 2. Add source_document_id linkage to consensus_fact_sources
    with op.batch_alter_table('consensus_fact_sources', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('source_document_id', sa.String(length=36), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_consensus_fact_sources_source_document_id',
            'source_documents',
            ['source_document_id'],
            ['id'],
        )
        batch_op.create_index(
            batch_op.f('ix_consensus_fact_sources_source_document_id'),
            ['source_document_id'],
            unique=False,
        )


def downgrade() -> None:
    # 1. Remove source_document_id from consensus_fact_sources
    with op.batch_alter_table('consensus_fact_sources', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_consensus_fact_sources_source_document_id'))
        batch_op.drop_constraint('fk_consensus_fact_sources_source_document_id', type_='foreignkey')
        batch_op.drop_column('source_document_id')

    # 2. Remove rights and publication fields from source_documents
    with op.batch_alter_table('source_documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_source_documents_publication_status'))
        batch_op.drop_column('third_party_permission_notes')
        batch_op.drop_column('third_party_permission_status')
        batch_op.drop_column('quarantine_reason')
        batch_op.drop_column('reuse_restrictions')
        batch_op.drop_column('attribution_text')
        batch_op.drop_column('attribution_required')
        batch_op.drop_column('derived_summary_allowed')
        batch_op.drop_column('full_text_storage_allowed')
        batch_op.drop_column('redistribution_allowed')
        batch_op.drop_column('commercial_redistribution_allowed')
        batch_op.drop_column('permissible_use')
        batch_op.drop_column('rights_reviewer')
        batch_op.drop_column('rights_reviewed_at')
        batch_op.drop_column('rights_evidence_url')
        batch_op.drop_column('publication_status')
