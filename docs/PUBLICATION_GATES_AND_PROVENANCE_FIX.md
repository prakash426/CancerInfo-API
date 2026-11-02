# Public evidence and WHO provenance safeguards

This change addresses the three issues reproduced during review of merge commit eb2517426cced6fd155dcfc2269665d782c458cb. It does not change source permissions, grant publication eligibility, run a data transition, or deploy anything.

## Public content selection

Public content uses the existing `evaluate_publication_eligibility` authority. A record or consensus fact must be active, have at least one citation, and have every citation linked to an eligible document belonging to that citation's active source and matching its original or canonical URL. Missing documents, incomplete evidence, quarantined decisions, and mixed eligible/ineligible evidence withhold the whole assembled item. A source or country filter cannot bypass this gate.

The policy applies before pagination and counts to category content, search results and snippets, consensus items, section availability, supporting sources, source metrics and coverage. Source registry entries remain descriptive metadata and do not imply that their documents are cleared.

Public version history requires both a currently publishable record and a version-specific provenance snapshot referencing an eligible document still linked to that record. Versions without verifiable provenance remain in the internal audit history. Public history uses a neutral change description rather than returning internal JSON snapshots, which can contain earlier withdrawn quotes. No historical rows are deleted or rewritten by the public selection policy.

Rights decisions are evaluated afresh on each repository call. The policy does not automatically approve seeded or newly imported content. Public results and coverage can decrease when the stored evidence does not meet the existing eligibility requirements.

## WHO rights withdrawal

A metadata-only, rejected, missing, unsigned, or no-longer-qualifying decision withdraws previously imported content for the affected document and cancer pair. Linked records and consensus facts are deactivated. Active content records receive a new `RIGHTS_WITHDRAWN` audit version; prior content, citations, versions and WHO provenance rows remain intact. Repeated withdrawals do not append duplicate versions. Shared evidence is withheld as a whole because its text cannot safely be separated by contributor; unrelated records and documents remain untouched.

Changes stay in the caller's transaction. The importer does not commit implicitly, and the existing CLI rolls back on error or in its default dry-run mode. Reapproval can refresh staged records, but does not independently establish publication eligibility.

## Complete managed-schema verification

`app/database/model_tables.py` derives the application-managed table inventory from the registered SQLAlchemy metadata. Schema adoption, preservation manifests, foreign-key audits and bootstrap accounting share that inventory, including `who_fact_provenance`. Legacy unmanaged tables remain outside it.

Production startup now verifies physical schema parity as well as the Alembic revision. A database stamped at head but missing a managed table or index cannot pass startup. No automatic repair or migration is performed. Existing parity comparison failures remain fail-closed.

## Regression evidence

New tests exercise eligible and ineligible public evidence, missing and mismatched citations, mixed-source filters, public history, current-session revocation, importer withdrawal/idempotency/rollback, and missing or malformed WHO schema. WHO importer and public rights tests run against SQLite and migrated PostgreSQL when `POSTGRES_TEST_URL` is set. Existing recovery and startup tests now preserve populated WHO provenance rows, not just the previous 11 tables.

Legacy public-response tests make explicit test-only rights decisions in disposable databases. These fixtures are not changes to the production seed or rights inventory and do not establish source clearance.

The PostgreSQL CI step includes the new regression modules. Local test results and container evidence are recorded in the separate validation report.
