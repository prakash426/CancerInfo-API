"""Public evidence selection using the existing document rights authority.

Records and consensus text can combine multiple citations. They are public only
when every citation is linked to an eligible document from an active source.
No decision is cached across calls: revocation takes effect on the next read.
"""
import json

from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from app.core.rights_validation import evaluate_publication_eligibility
from app.core.constants import ContentType
from app.core.publication_access import publication_use
from app.models import ContentRecord, ContentSource, ConsensusFact, ConsensusFactSource, SourceDocument


class PublicEvidence:
    def __init__(self, db):
        self.use = publication_use.get()
        candidates = list(db.query(SourceDocument).options(joinedload(SourceDocument.source)))
        self.by_type = {
            kind.value: {
                doc.id: doc for doc in candidates
                if doc.source is not None and doc.source.active
                and evaluate_publication_eligibility(
                    doc, content_type=kind.value, publication_use=self.use)[0]
            }
            for kind in ContentType
        }
        self.documents = {key: doc for docs in self.by_type.values() for key, doc in docs.items()}

    def citation(self, model, content_type):
        # A null or dangling document must fail closed rather than evaluate to
        # SQL UNKNOWN under NOT EXISTS. Also reject a mismatched source link.
        return model.source_document.has(and_(
            SourceDocument.id.in_(self.by_type.get(content_type, {})),
            SourceDocument.source_id == model.source_id,
            or_(SourceDocument.original_url == model.source_url,
                SourceDocument.canonical_url == model.source_url),
        ))

    def records(self):
        return and_(
            ContentRecord.active.is_(True),
            ContentRecord.sources.any(),
            or_(*[
                and_(ContentRecord.content_type == kind,
                     ~ContentRecord.sources.any(~self.citation(ContentSource, kind)))
                for kind in self.by_type
            ]),
        )

    def consensus(self):
        return and_(
            ConsensusFact.active.is_(True),
            ConsensusFact.corroborating_sources.any(),
            ~ConsensusFact.corroborating_sources.any(~self.citation(ConsensusFactSource, "DERIVED_SUMMARY")),
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
        # A current record's type cannot establish the type of historical text.
        kind = snapshot.get("content_type")
        if self.use == "NONCOMMERCIAL" and kind is None:
            return False
        if not evaluate_publication_eligibility(
                doc, content_type=kind, publication_use=self.use)[0]:
            return False
        return any(
            link.source_document_id == doc.id and link.source_id == doc.source_id
            and snapshot.get("url") == link.source_url
            for link in version.content_record.sources
        )
