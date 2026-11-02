"""
Search Repository
"""
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
from app.core.constants import CANONICAL_CATEGORIES, CATEGORY_ALIASES
from app.models import (
    Cancer,
    CancerAlias,
    ConsensusFact,
    ConsensusFactSource,
    ContentRecord,
    ContentSource,
    Source,
)


class SearchRepository:
    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        query_str: str,
        category: Optional[str] = None,
        country: Optional[str] = None,
        source_id: Optional[str] = None,
        audience: Optional[str] = None,
        limit: Optional[int] = 20,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        query_clean = query_str.strip()
        tokens = [t.lower() for t in query_clean.split() if t]
        results: List[Dict[str, Any]] = []

        # 1. Check if any token matches a canonical category
        detected_category = category
        if not detected_category:
            for t in tokens:
                if t in CANONICAL_CATEGORIES:
                    detected_category = t
                    break
                elif t in CATEGORY_ALIASES:
                    detected_category = CATEGORY_ALIASES[t]
                    break

        # 2. Direct Cancer entity matching (canonical name & aliases)
        # e.g. "bowel cancer", "CRC", "breast", "pancreatic"
        cancer_query = self.db.query(Cancer).options(joinedload(Cancer.aliases))
        search_filter = or_(
            func.lower(Cancer.canonical_name).contains(query_clean.lower()),
            func.lower(Cancer.slug).contains(query_clean.lower()),
        )
        for t in tokens:
            search_filter = or_(
                search_filter,
                func.lower(Cancer.canonical_name).contains(t),
            )

        matched_cancers = cancer_query.filter(search_filter).all()

        # Also search aliases table
        alias_matches = (
            self.db.query(CancerAlias)
            .filter(
                CancerAlias.review_status == "APPROVED",
                or_(
                    func.lower(CancerAlias.alias).contains(query_clean.lower()),
                    *[func.lower(CancerAlias.alias).contains(t) for t in tokens]
                )
            )
            .all()
        )
        for am in alias_matches:
            c = self.db.query(Cancer).filter(Cancer.id == am.cancer_id).first()
            if c and c not in matched_cancers:
                matched_cancers.append(c)

        for c in matched_cancers:
            # Calculate match score
            score = 1.0
            if query_clean.lower() == c.canonical_name.lower() or query_clean.lower() == c.slug.lower():
                score = 3.0
            elif any(query_clean.lower() == a.alias.lower() for a in c.aliases if a.review_status == "APPROVED"):
                score = 2.5
            elif c.canonical_name.lower().startswith(query_clean.lower()):
                score = 2.0

            results.append({
                "match_type": "cancer",
                "score": score,
                "cancer": c,
                "category": None,
                "snippet": c.description,
                "record": None,
                "matched_terms": [t for t in tokens if t in c.canonical_name.lower() or any(t in a.alias.lower() for a in c.aliases if a.review_status == "APPROVED")],
            })

        # 3. Consensus Fact search (e.g. "cough with blood", "lump", "dimpling", "jaundice")
        consensus_query = (
            self.db.query(ConsensusFact)
            .options(
                joinedload(ConsensusFact.cancer).joinedload(Cancer.aliases),
                joinedload(ConsensusFact.corroborating_sources).joinedload(ConsensusFactSource.source),
            )
            .filter(ConsensusFact.active == True)
        )

        if detected_category:
            consensus_query = consensus_query.filter(ConsensusFact.category == detected_category)
        if source_id:
            consensus_query = consensus_query.filter(ConsensusFact.corroborating_sources.any(
                ConsensusFactSource.source_id == source_id
            ))
        # Country personalizes citations on universal consensus; it does not
        # exclude facts. Audience-specific searches exclude untyped consensus.
        if audience:
            consensus_query = consensus_query.filter(False)

        cf_matches = []
        # Check full query match
        full_matches = consensus_query.filter(
            or_(
                func.lower(ConsensusFact.title).contains(query_clean.lower()),
                func.lower(ConsensusFact.clinical_detail).contains(query_clean.lower()),
            )
        ).all()
        for cf in full_matches:
            cf_matches.append((cf, 3.8))

        # Check token matches
        stop_words = {"with", "and", "the", "for", "from", "in", "of", "to", "a", "an"}
        meaningful_tokens = [t for t in tokens if len(t) > 2 and t not in stop_words]
        if meaningful_tokens:
            token_conditions = [
                or_(
                    func.lower(ConsensusFact.title).contains(t),
                    func.lower(ConsensusFact.clinical_detail).contains(t),
                )
                for t in meaningful_tokens
            ]
            token_results = consensus_query.filter(or_(*token_conditions)).all()
            for cf in token_results:
                if not any(existing[0].id == cf.id for existing in cf_matches):
                    matched_count = sum(
                        1
                        for t in meaningful_tokens
                        if t in cf.title.lower() or (cf.clinical_detail and t in cf.clinical_detail.lower())
                    )
                    score = 2.0 + (matched_count * 0.5)
                    cf_matches.append((cf, score))

        for cf, score in cf_matches:
            matched_terms = [
                t
                for t in tokens
                if t in cf.title.lower() or (cf.clinical_detail and t in cf.clinical_detail.lower())
            ]
            results.append({
                "match_type": "consensus_item",
                "score": score,
                "cancer": cf.cancer,
                "category": cf.category,
                "snippet": f"{cf.title}: {cf.clinical_detail or ''}".strip(),
                "consensus_item": cf,
                "record": None,
                "matched_terms": matched_terms,
            })

        # 4. Content record search
        content_query = (
            self.db.query(ContentRecord)
            .options(
                joinedload(ContentRecord.cancer),
                joinedload(ContentRecord.sources).joinedload(ContentSource.source),
            )
            .filter(ContentRecord.active == True)
        )

        if detected_category:
            content_query = content_query.filter(ContentRecord.category == detected_category)

        if country:
            country_clean = country.strip().upper()
            content_query = content_query.filter(
                (ContentRecord.country_code == country_clean) | (ContentRecord.country_code == "GLOBAL")
            )

        if audience:
            content_query = content_query.filter(ContentRecord.audience == audience.strip().lower())

        if source_id:
            content_query = content_query.filter(ContentRecord.sources.any(ContentSource.source_id == source_id))

        # Content keyword filter
        for t in tokens:
            # Avoid filtering content strictly by words that were already used as category tokens
            if t != detected_category and t not in CATEGORY_ALIASES:
                content_query = content_query.filter(func.lower(ContentRecord.content).contains(t))

        content_matches = content_query.all()

        for rec in content_matches:
            # Create snippet
            snippet = rec.content
            if len(snippet) > 280:
                snippet = snippet[:280].rsplit(" ", 1)[0] + "..."

            results.append({
                "match_type": "content_record",
                "score": 1.5,
                "cancer": rec.cancer,
                "category": rec.category,
                "snippet": snippet,
                "consensus_item": None,
                "record": rec,
                "matched_terms": [t for t in tokens if t in rec.content.lower()],
            })

        # Filtered searches describe evidence rather than untyped taxonomy hits.
        if category or country or source_id or audience:
            results = [r for r in results if r["match_type"] != "cancer"]
        def order(r):
            entity = r.get("record") or r.get("consensus_item") or r["cancer"]
            country_rank = 0
            if country and r.get("record"):
                country_rank = int(r["record"].country_code != country.strip().upper())
            return (-r["score"], country_rank, r["match_type"], r["cancer"].id, entity.id)
        results.sort(key=order)
        return results[skip:] if limit is None else results[skip:skip + limit]
