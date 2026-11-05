# Owner-directed WHO noncommercial publication metadata

The owner reviewed all 48 WHO document entries and instructed the exact noncommercial values on November 3, 2026. A follow-up instruction confirmed that only WHO-owned text is used and third-party components are excluded for the 16 previously pending component reviews. The plans record those owner decisions; they do not claim a new WHO permission or a third-party grant.

## Current applied state

All 48 WHO documents are ELIGIBLE, with redistribution and noncommercial redistribution true, commercial redistribution false, and STRUCTURED_EXTRACTION in their approved content-type array. All 48 third-party statuses are now NOT_APPLICABLE. The specified 16 have the note: Owner confirmed that only WHO-owned text is used and third-party components are excluded.

All 60 active WHO records pass the existing noncommercial publication gate. The three inactive historical WHO records remain inactive. The exact commercial/default manifest remains 264 records and contains no WHO content. The approved noncommercial manifest is 324 records, including 60 WHO records. A reviewed key configured through NONCOMMERCIAL_API_KEY_SHA256 is required for noncommercial access. No key is issued or approved by these plans; the admin key grants no publication access.

Attribution flags/text, evidence URLs, permissible-use text, storage/derivative decisions and all other non-requested fields remain unchanged by the follow-up. The existing evidence URL and Creative Commons attribution wording are retained on the owner's explicit instruction. No third-party permission request is sent and no third-party receipt is fabricated. Earlier review CSVs remain unchanged historical artifacts; separate private applied-values CSVs record each resulting state.

## Exact plans and sequence

1. `policies/who-noncommercial-20261103.json` records the original 48-document update. It initially moved 16 REQUIRED_NOT_SUBMITTED states to SUBMITTED, with 24 WHO records eligible for noncommercial delivery.
2. `policies/who-text-only-20261103.json` records the follow-up: exactly those 16 SUBMITTED states become NOT_APPLICABLE and receive the owner-confirmed exclusion note. This changes 32 field values and enables the remaining 36 active WHO records for approved noncommercial delivery.

The plans check document ID, source, exact URL, source hash and expected prior values. Separate commercial and noncommercial manifests are verified. The CLI is dry-run by default and commits only on explicit application. The follow-up is repeat-safe. Replaying the older plan after the follow-up intentionally refuses to restore the superseded SUBMITTED decisions.

SUBMITTED remains a valid pending state in the enum and is still withheld by the unchanged public gate. Only NOT_APPLICABLE or GRANTED passes the third-party check. The notes field is now supported by the exact policy-plan tool. No publication predicate was weakened.

## Preserving local synchronization

`scripts/sync_local_from_live.py` explicitly selects an existing local SQLite file and a new backup path. It reads PostgreSQL through a read-only, repeatable-read snapshot, backs up the local file and prepares a migrated working copy. It imports or updates source rows by primary key and verifies every source value, schema and foreign key. Local-only rows/tables are retained.

The known recovered SQLite NOT NULL country constraint is reconciled to the current nullable model only in the working copy. Unknown incompatible schemas fail without replacing the original. Before replacing destination pages, an exclusive SQLite lock and initial-digest comparison prevent overwriting intervening local edits. SQLite's backup API updates the existing database inode; original recovery backups remain private.

The main local `cancerinfo.db` is synchronized with live, including the newer noncommercial and content-type columns and the follow-up notes. Staging databases and research files remain untouched. Local schema head includes 0006 and its empty operational rate-limit table. Live remains at 0005 until a separately authorized application release. No production schema migration is performed by either metadata plan.

## Validation and preservation

The follow-up passed 398 full SQLite/PostgreSQL tests with one existing Starlette/httpx warning, plus container packaging, ports, migrations, bootstrap/repeat refusal, API endpoints and persistence. A restored-production HTTP rehearsal verified 264 anonymous/commercial records, 324 approved-noncommercial records, withholding from anonymous WHO requests and retrieval of newly eligible WHO records with a temporary approved test key. The test key is not issued or configured in production.

The exact live follow-up and replay were verified. All 365 records, 365 citations, 365 versions, 60 WHO provenance rows and 5,628 legacy rows are unchanged. Only the requested 16 statuses and 16 notes changed. Every other live value matched the baseline. Main-local synchronization passed source-value comparisons; 81 other local database/research files matched their previous fingerprints.

Private production/local backups, before/after snapshots, applied 48-row CSVs and preservation evidence are retained outside Git. No content is re-ingested, reseeded, deleted or reactivated, and commercial WHO access remains blocked.
