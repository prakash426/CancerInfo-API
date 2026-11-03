# Owner-directed WHO noncommercial publication metadata

The owner reviewed all 48 WHO document entries and instructed the exact values in `policies/who-noncommercial-20261103.json` on November 3, 2026. This plan records that decision; it does not claim a new WHO permission or a third-party grant.

For all 48 documents, the plan sets ELIGIBLE, redistribution and noncommercial redistribution true, commercial redistribution false, and the approved content-type array to STRUCTURED_EXTRACTION. It records the owner's exact permissible-use statement. Existing attribution flags/text and evidence URLs stay unchanged. The 16 REQUIRED_NOT_SUBMITTED values become SUBMITTED as requested. Other fields and all content remain unchanged.

## Access outcome

SUBMITTED is a recognized pending state, not GRANTED. The public gate continues to accept only NOT_APPLICABLE or GRANTED third-party decisions. On the reviewed corpus, 32 WHO documents pass the noncommercial document gate; 16 SUBMITTED documents remain withheld. There are 24 active WHO records eligible for approved noncommercial delivery, and 36 active WHO records still withheld. The three inactive historical WHO records remain inactive.

The exact commercial/default manifest remains 264 records and contains no WHO records. The approved noncommercial manifest is 288 records, including 24 WHO records. These are access-specific counts, not a promise that anonymous callers can retrieve the noncommercial material. No developer key is created or approved by this plan. A key already reviewed and configured through NONCOMMERCIAL_API_KEY_SHA256 is required for noncommercial access. The admin key does not provide that access.

The existing evidence URL and Creative Commons attribution wording are retained on the owner's explicit instruction. They are not independently expanded or reinterpreted by this implementation. No third-party permission request is sent and no third-party receipt is fabricated. The earlier WHO review CSV remains an unchanged pre-update review artifact.

## Exact update tool

The policy tool checks document ID, source, exact URL, source hash and every changed field's expected prior value. It checks separate commercial and noncommercial record manifests and restores the caller's original use context. A mismatch aborts the operation. The CLI is dry-run by default and commits only on explicit application. Replay is a no-op. The new SUBMITTED enum does not weaken the publication gate; the previously deployed code also withholds that state.

## Local synchronization

`scripts/sync_local_from_live.py` explicitly selects an existing local SQLite file and a new backup path. It reads PostgreSQL through a read-only, repeatable-read snapshot. The source is never written by synchronization.

It backs up the local database, prepares a working copy, upgrades that copy through Alembic head, imports or updates each source row by primary key and checks every source value across supported types. It does not delete local-only rows or tables. The known recovered SQLite NOT NULL country constraint is reconciled to the current nullable model only in the working copy. Unknown incompatible schemas fail without replacing the original file.

The prepared copy must pass schema parity and foreign-key checks. Before replacing destination pages, the tool holds an exclusive SQLite lock and compares the local database with its initial digest. Intervening local edits cause refusal. SQLite's backup API updates the existing database inode; original recovery backups remain separate and private. The tool is a deliberate local operation, never an automatic startup task.

The main local `cancerinfo.db` is the requested sync target. Staging databases and research files are not modified. Local schema head includes migration 0006 and its empty operational rate-limit table. Live remains at 0005 until a separately authorized application release. All live corpus and legacy rows are compared, regardless of that operational schema difference.

## Release boundary

Live metadata application and local synchronization are explicitly authorized in this task. Code is proposed into launch_blockers for review. Do not merge into main or deploy. No content is re-ingested, reseeded, deleted or reactivated; no consent, commercial access, or caller approval is inferred.

## Applied and verified, November 3, 2026

The exact live plan committed 256 changed field values across the 48 WHO documents. All content, citations, versions, WHO provenance, legacy data and other document fields remained exact. Attribution and evidence URLs were not changed. Replay reported zero changes.

The main local database now contains all 365 live records, 365 citations, 365 versions, 60 WHO provenance rows, 5,628 legacy rows, 83 documents and 25 cancers, with the new noncommercial and content-type columns. Source values were compared field by field. No local-only rows required deletion. Original local backups remain private; 81 other local database/research artifacts matched their previous fingerprints.

Validation: 396 local SQLite/PostgreSQL tests passed with one existing Starlette/httpx warning. The container suite passed packaging, ports, migrations, bootstrap/repeat refusal, API endpoints and persistence. The restored-production API rehearsal confirmed 264 anonymous/commercial records, 288 approved-noncommercial records, unapproved-key denial and withholding of SUBMITTED documents. Live anonymous coverage stayed at 264 and WHO source-filtered search stayed empty. No noncommercial developer key was issued. Dependency and private-artifact guards passed.

Private backups, full before/after preservation evidence and the applied 48-row CSV are retained outside Git under the project outputs directory. The PR and its exact-head CI results provide the code review boundary. No merge into main, application deployment or production schema migration was performed.
