"""Atomic document refresh using the existing schema; no migrations or implicit commit.

Ported from the implementation-L027 refresh module so handoff driven
imports share one replace path. The caller owns the transaction commit.
"""
import json
from datetime import datetime
from app.models import Source, SourceDocument, ContentRecord, ContentSource, ContentVersion
from app.core.constants import CANONICAL_CATEGORIES
from app.normalization.hash import compute_content_hash


def refresh_document(db, document, *, parser_version='shared-readers-v1'):
    source=db.query(Source).filter(Source.id==document.source_id).one()
    if not source.active:
        raise ValueError('Inactive source')
    if not document.sections:
        raise ValueError('Empty extraction cannot replace accepted content')
    identities=[(s.category,s.subcategory or s.category,s.audience) for s in document.sections]
    if len(identities)!=len(set(identities)):
        raise ValueError('Ambiguous duplicate section identity')
    if any(s.category not in CANONICAL_CATEGORIES or not s.content.strip() for s in document.sections):
        raise ValueError('Unknown category or empty content')
    from app.models import Cancer
    cancer=db.query(Cancer).filter(Cancer.slug==document.cancer_slug).one()
    created=updated=retired=0
    with db.begin_nested():
        doc=db.query(SourceDocument).filter_by(source_id=source.id,original_url=document.original_url,canonical_cancer_id=cancer.id).one_or_none()
        if doc is None:
            doc=SourceDocument(source_id=source.id,original_url=document.original_url,canonical_url=document.canonical_url,title=document.title,canonical_cancer_id=cancer.id,source_cancer_name=document.source_cancer_name,language=document.language,country_code=document.country_code,jurisdiction_scope=document.jurisdiction_scope,content_hash=document.content_hash,license_status=source.license_status,processing_status='PROCESSED')
            db.add(doc);db.flush()
        doc.canonical_url=document.canonical_url;doc.title=document.title;doc.content_hash=document.content_hash;doc.last_verified_at=datetime.utcnow()
        links=db.query(ContentSource).filter_by(source_id=source.id,source_document_id=doc.id).all()
        old={}
        for link in links:
            rec=db.get(ContentRecord,link.content_record_id)
            key=(rec.category,rec.subcategory or rec.category,rec.audience)
            if key in old:raise ValueError('Legacy duplicate identity requires review')
            old[key]=(rec,link)
        touched=set()
        for section,key in zip(document.sections,identities):
            touched.add(key);pair=old.get(key)
            if pair:
                rec,link=pair
                previous=dict(url=link.source_url,source_updated_at=link.source_updated_at.isoformat() if link.source_updated_at else None,quote=link.quote_snippet,attribution=link.attribution_text)
                changed=rec.content!=section.content or link.source_url!=(section.source_url or document.canonical_url) or link.source_updated_at!=document.source_updated_at or link.quote_snippet!=section.quote_snippet or link.attribution_text!=source.attribution_text or not rec.active
                if changed:rec.version_number+=1;updated+=1
            else:
                rec=ContentRecord(canonical_cancer_id=cancer.id,category=section.category,subcategory=section.subcategory or section.category,content=section.content,country_code=document.country_code,jurisdiction_scope=document.jurisdiction_scope,language=document.language,audience=section.audience,version_number=1,active=True)
                db.add(rec);db.flush()
                link=ContentSource(content_record_id=rec.id,source_id=source.id,source_document_id=doc.id,source_url=document.canonical_url)
                db.add(link);created+=1;changed=True;previous=None
            rec.content=section.content;rec.active=True;rec.disagreement_status=section.disagreement_status
            link.source_url=section.source_url or document.canonical_url
            link.source_updated_at=document.source_updated_at
            link.quote_snippet=section.quote_snippet;link.attribution_text=source.attribution_text
            link.last_verified_at=datetime.utcnow()
            if changed:
                snapshot=dict(parser_version=parser_version,url=link.source_url,source_id=source.id,document_id=doc.id,source_locator=section.source_locator,source_updated_at=document.source_updated_at.isoformat() if document.source_updated_at else None,quote=link.quote_snippet,attribution=link.attribution_text,previous_provenance=previous)
                db.add(ContentVersion(content_record_id=rec.id,version_number=rec.version_number,content=rec.content,content_hash=compute_content_hash(rec.content),change_type='NEW' if previous is None else 'UPDATED',change_reason=json.dumps(snapshot)))
        for key,(rec,link) in old.items():
            if key not in touched and rec.active:
                rec.active=False;retired+=1
        db.flush()
    return {'created':created,'updated':updated,'retired':retired}
