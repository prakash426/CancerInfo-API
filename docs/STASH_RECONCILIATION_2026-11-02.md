# Stash reconciliation review: 2026-11-02

All 89 files restored in the local working directory were reviewed individually and preserved. Sixteen stashed application/migration/test source files were also compared with launch_blockers: 11 match byte-for-byte and five are superseded by the newer rights and provenance implementation. No stashed application feature is missing upstream. The obsolete tmp model module is not part of the serving architecture.

## Resulting code changes

- Fix the restored live report's remaining CORS finding: anonymous public access does not grant browser credentials; credentialed access requires an explicit origin allowlist. JSON and comma-separated origin configuration are supported.
- Untrack the old committed cancerinfo.db without deleting any local database. Add ignore rules and a read-only CI index check to prevent local database, research and credential files entering future commits.
- Exclude restored private data and scratch research from the Docker build context.
- Correct development instructions: migrations and bootstrap are deliberate operations on an empty development database, never automatic startup or a way to restore a corpus.

The restored report's PostgreSQL JSON DISTINCT failure and unknown-category fallback are already corrected by the earlier L010/publication work. The report is historical evidence, not verification of the current live service. Private permission documents and saved decisions are not new publication clearance. Corpus eligibility and local schema compatibility findings from the preceding review remain separate from this code reconciliation.

## Source reconciliation

| Source path | Decision |
| :--- | :--- |
| `alembic/versions/0003_who_provenance.py` | Already integrated unchanged |
| `app/database/adoption.py` | Retain newer upstream implementation and tests |
| `app/database/transition.py` | Already integrated unchanged |
| `app/ingestion/refresh.py` | Already integrated unchanged |
| `app/ingestion/who_import.py` | Retain newer upstream implementation and tests |
| `app/ingestion/who_validate.py` | Already integrated unchanged |
| `app/models/__init__.py` | Already integrated unchanged |
| `app/sources/base.py` | Already integrated unchanged |
| `scripts/bootstrap_who_staging.py` | Already integrated unchanged |
| `scripts/import_who_package.py` | Already integrated unchanged |
| `scripts/make_who_decision_sheet.py` | Already integrated unchanged |
| `scripts/validate_who_package.py` | Already integrated unchanged |
| `scripts/verify_who_staging.py` | Already integrated unchanged |
| `tests/test_document_rights.py` | Retain newer upstream implementation and tests |
| `tests/test_migrations.py` | Retain newer upstream implementation and tests |
| `tests/test_who_importer.py` | Retain newer upstream implementation and tests; old status-exposure test replaced by public-withholding regressions |

## Restored working-file decisions

Every listed file remains local and has an exact preserved backup outside the Git working tree. Databases were checked read-only, structured research files were parsed, helper source was inspected without running benchmark jobs, images were decoded, and PDF pages were extracted for identification. Private values, raw research text and file hashes are excluded from this public index. The local evidence inventory retains per-file hashes and details. Branding assets have no current API/UI reference and are retained for deliberate future integration.

| Restored path | Classification | Action |
| :--- | :--- | :--- |
| `cancerinfo.db` | database | Preserve locally; do not publish in code PR |
| `cancerinfo.db.before-20261101-live-merge` | database | Preserve locally; do not publish in code PR |
| `cancerinfo.db.before-cancer-australia-removal` | database | Preserve locally; do not publish in code PR |
| `database/cancerinfo_staging.backup-20261101.db` | database | Preserve locally; do not publish in code PR |
| `database/cancerinfo_staging.db` | database | Preserve locally; do not publish in code PR |
| `database/l027-candidate.backup-20261101.db` | database | Preserve locally; do not publish in code PR |
| `database/l027-candidate.db` | database | Preserve locally; do not publish in code PR |
| `database/ovarian_staging.db` | database | Preserve locally; do not publish in code PR |
| `database/publication-review-20261101.md` | publication review | Preserve locally; do not publish in code PR |
| `docs/LIVE_API_TEST_REPORT.md` | live API report | Preserve locally; do not publish in code PR |
| `logo/CancerInfoAPI_FullLogo_2048.png` | branding asset | Preserve locally; do not publish in code PR |
| `logo/CancerInfoAPI_FullLogo_512_NATIVE.png` | branding asset | Preserve locally; do not publish in code PR |
| `logo/CancerInfoAPI_Icon_512.png` | branding asset | Preserve locally; do not publish in code PR |
| `logo/CancerInfoAPI_Logo.pdf` | branding asset | Preserve locally; do not publish in code PR |
| `logo/CancerInfoAPI_Transparent_1024.png` | branding asset | Preserve locally; do not publish in code PR |
| `logo/favicon.ico` | branding asset | Preserve locally; do not publish in code PR |
| `permissions/WHO License & Agreement.pdf` | private permission document | Preserve locally; do not publish in code PR |
| `permissions/WHO Request Communication.pdf` | private permission document | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/CancerLens_Competitor_Benchmark_Report.md` | CancerLens research | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/build_audit_manual.py` | CancerLens benchmark helper | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/build_dataset.py` | CancerLens benchmark helper | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/build_results.py` | CancerLens benchmark helper | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/cancerlens_test_claims.csv` | CancerLens research | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/cancerlens_test_claims.json` | CancerLens research | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/cancerlens_url_tests.csv` | CancerLens research | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/competitor_test_results.csv` | CancerLens research | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_A3_breakdown.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_A3_card.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_A3_goodtoknow.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_A3_input.jpg` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_A3_sources.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_A3_stuck_spinner_402.jpg` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_B3_breakdown.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_B3_card.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_B3_goodtoknow.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_B3_sources.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_E1_melatonin_breakdown.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_E1_melatonin_card.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_E1_melatonin_goodtoknow.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_E1_melatonin_sources.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_E2_greentea_card.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_E2_greentea_goodtoknow.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidencecheck_E2_greentea_sources.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidentia_A3_text.jpg` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidentia_B3_rerun_82_strongly_supported.jpg` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/evidence_screenshots/evidentia_D3_insufficient.jpg` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/make_images.py` | CancerLens benchmark helper | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/manual_testing_required.csv` | CancerLens research | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/cancerfactfinder_A2_search.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/cancerfactfinder_all_searches.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/evidencecheck_A3_B3_E1_E2_userrun.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/evidencecheck_A3_text.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/evidencecheck_site_profile.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/evidencelens_access_and_library_B3.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/evidentia_A1_text.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/evidentia_A2_text.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/evidentia_A3_text.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/evidentia_B1_text.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/evidentia_B2_text.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/evidentia_B3_text.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/evidentia_C1_C2_C3_D3_text.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/raw_responses/evidentia_D1_D2_text.txt` | CancerLens raw evidence | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/reference_evidence_audit.csv` | CancerLens research | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/test_images/claim_A2.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/test_images/claim_A3.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/test_images/claim_B1.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tests/Competitor-Analysis/cancerlens_benchmark/test_images/claim_D3.png` | CancerLens evidence image | Preserve locally; do not publish in code PR |
| `tmp/WHO_DATA_PROCESSING_INSTRUCTIONS.md` | WHO research | Preserve locally; do not publish in code PR |
| `tmp/__init__.py` | old duplicate model module | Preserve locally; do not publish in code PR |
| `tmp/cancerinfo-neon-url.txt` | private credential | Preserve locally; do not publish in code PR |
| `tmp/proving_full.db` | database | Preserve locally; do not publish in code PR |
| `tmp/taxonomy-updated.md` | WHO research | Preserve locally; do not publish in code PR |
| `tmp/who_coverage.csv` | WHO research | Preserve locally; do not publish in code PR |
| `tmp/who_facts.ndjson` | WHO research | Preserve locally; do not publish in code PR |
| `tmp/who_live_manifest.json` | WHO load evidence | Preserve locally; do not publish in code PR |
| `tmp/who_load_manifest.json` | WHO load evidence | Preserve locally; do not publish in code PR |
| `tmp/who_pages.csv` | WHO research | Preserve locally; do not publish in code PR |
| `tmp/who_review_notes.md` | WHO research | Preserve locally; do not publish in code PR |
| `tmp/who_rights_decisions.csv` | WHO research | Preserve locally; do not publish in code PR |
| `tmp/who_sections.csv` | WHO research | Preserve locally; do not publish in code PR |
| `tmp/who_validation_report.md` | WHO research | Preserve locally; do not publish in code PR |
| `who_coverage.csv` | WHO research | Preserve locally; do not publish in code PR |
| `who_facts.ndjson` | WHO research | Preserve locally; do not publish in code PR |
| `who_load_manifest.json` | WHO load evidence | Preserve locally; do not publish in code PR |
| `who_pages.csv` | WHO research | Preserve locally; do not publish in code PR |
| `who_review_notes.md` | WHO research | Preserve locally; do not publish in code PR |
| `who_rights_decisions.csv` | WHO research | Preserve locally; do not publish in code PR |
| `who_sections.csv` | WHO research | Preserve locally; do not publish in code PR |
| `who_validation_report.md` | WHO research | Preserve locally; do not publish in code PR |

## Preservation and merge boundary

No database or research content is added, imported, reseeded, repaired or deleted by this change. The old tracked database is removed from version control only; working copies and backups are retained. The existing stash is retained as an additional recovery point. No private connection values or permission attachments enter the PR.

The confirmed target is launch_blockers. Main and deployment remain unchanged. Local and CI test outcomes are recorded in the PR after execution.
