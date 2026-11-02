"""Public evidence selection using the existing document rights authority.

Records and consensus text can combine multiple citations. They are public only
when every citation is linked to an eligible document from an active source.
No decision is cached across calls: revocation takes effect on the next read.
"""
import json

from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from app.core.rights_validation import evaluate_publication_eligibility
from app.models import ContentRecord, ContentSource, ConsensusFact, ConsensusFactSource, SourceDocument


class PublicEvidence:
    def __init__(self, db):
        self.documents = {
            doc.id: doc
            for doc in db.query(SourceDocument).options(joinedload(SourceDocument.source))
            if doc.source is not None and doc.source.active
            and evaluate_publication_eligibility(doc)[0]
        }

    def citation(self, model):
        # A null or dangling document must fail closed rather than evaluate to
        # SQL UNKNOWN under NOT EXISTS. Also reject a mismatched source link.
        return model.source_document.has(and_(
            SourceDocument.id.in_(self.documents),
            SourceDocument.source_id == model.source_id,
            or_(SourceDocument.original_url == model.source_url,
                SourceDocument.canonical_url == model.source_url),
        ))

    def records(self):
        return and_(
            ContentRecord.active.is_(True),
            ContentRecord.sources.any(),
            ~ContentRecord.sources.any(~self.citation(ContentSource)),
        )

    def consensus(self):
        return and_(
            ConsensusFact.active.is_(True),
            ConsensusFact.corroborating_sources.any(),
            ~ConsensusFact.corroborating_sources.any(~self.citation(ConsensusFactSource)),
        )

    def version(self, version):
        """Require version-specific provenance, not just current record rights.

        Older free-text audit reasons cannot establish the source of historical
        text. Retain those versions internally without publishing them.
        """
        try:
            snapshot = json.loads(version.change_reason or "")
        except (TypeError, ValueError):
            return False
        if not isinstance(snapshot, dict):
            return False
        document_id = snapshot.get("document_id")
        if not isinstance(document_id, str):
            return False
        doc = self.documents.get(document_id)
        if doc is None or snapshot.get("source_id") != doc.source_id:
            return False
        return any(
            link.source_document_id == doc.id and link.source_id == doc.source_id
            and snapshot.get("url") == link.source_url
            for link in version.content_record.sources
        )
