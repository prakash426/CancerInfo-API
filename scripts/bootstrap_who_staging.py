"""CLI: build a fresh staging database and seed the 25 approved cancers.

Creates all tables at current schema, runs the standard seeds, tops up
the cancer taxonomy from the approved register, and resolves the legacy
melanoma slug to melanoma-of-skin. Staging only; never run against live.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.ingestion.seed import seed_database
from app.ingestion.who_validate import parse_taxonomy_register
from app.models import Cancer, CancerAlias

STAGING_URL = "sqlite:////tmp/cancerinfo_staging.db"
STAGING_PATH = "/tmp/cancerinfo_staging.db"


def _alias_type(text):
    compact = text.replace(" ", "").replace("-", "")
    if len(compact) <= 6 and compact.isupper():
        return "abbreviation"
    return "common_name"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging-url", default=STAGING_URL)
    parser.add_argument("--taxonomy", default="tmp/taxonomy-updated.md")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()

    if args.fresh and os.path.exists(STAGING_PATH) and \
            args.staging_url == STAGING_URL:
        os.remove(STAGING_PATH)

    engine = create_engine(args.staging_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        seed_database(session)

        legacy = session.query(Cancer).filter(
            Cancer.slug == "melanoma").one_or_none()
        if legacy is not None:
            legacy.slug = "melanoma-of-skin"
            legacy.canonical_name = "Melanoma of skin"
            session.flush()

        register, aliases = parse_taxonomy_register(args.taxonomy)
        have = {c.slug: c for c in session.query(Cancer).all()}
        added = 0
        for cid in sorted(register):
            name, slug = register[cid]
            cancer = have.get(slug)
            if cancer is None:
                cancer = Cancer(
                    slug=slug, canonical_name=name,
                    description="Approved 25-cancer taxonomy entry; "
                                "ICD coding pending L004 resolution.",
                    taxonomy_codes={})
                session.add(cancer)
                session.flush()
                have[slug] = cancer
                added += 1
            known = {a.alias.lower() for a in session.query(CancerAlias)
                     .filter(CancerAlias.cancer_id == cancer.id).all()}
            for alias in aliases.get(cid, []):
                if alias.lower() in known:
                    continue
                session.add(CancerAlias(
                    cancer_id=cancer.id, alias=alias, language="en",
                    alias_type=_alias_type(alias), confidence=0.9,
                    review_status="APPROVED"))
                known.add(alias.lower())
        session.commit()
        slugs = sorted(c.slug for c in session.query(Cancer).all())
        print("cancers=%d added=%d" % (len(slugs), added))
        print("slugs=" + ",".join(slugs))
        missing = [slug for _cid, (_n, slug) in register.items()
                   if slug not in slugs]
        print("missing=" + (",".join(missing) if missing else "none"))
    finally:
        session.close()


if __name__ == "__main__":
    main()
