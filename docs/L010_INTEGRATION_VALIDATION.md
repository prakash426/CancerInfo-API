# L010 integration reconciliation

Verified 8 October 2026 against the transferred repository [prakash426/CancerInfo-API](https://github.com/prakash426/CancerInfo-API). The repository ID remains 1378010717. The GitHub connector can read it and reports repository push permission; no write operation was attempted through the connector. The local origin URL now uses the new account.

## Integration state

L003 and L016 are both ancestors of `launch_blockers` at `3995f9981a4c342ff5e385a5e5c2d223fd1cb290`. The integration history records the owner's merges in #8 and #9. Main remains at `7ae049310198b62d0b1812cad453471d403c65d3`. Main has zero unique commits; launch_blockers has thirteen unique commits. The branches are not synchronized. No main or integration branch was changed in this work.

## Implementation

The original L010 candidate `9471f0454b93bf1b1a41ecb1b932fc8b22ef7634` conflicts with current launch_blockers in app/main.py. A fresh local branch, `task-CIAPI-L010-integration-reconciliation`, starts from the exact integration head above. Its first commit reapplies L010 while resolving that conflict.

The resolution keeps L003's production migration check and explicit initialization behavior. It adds L010's error models and handlers without restoring startup schema creation or automatic seeding. The rest of L010 retains reviewed alias resolution, explicit category validation, country/GLOBAL ordering, combined pagination and sanitized errors. No schema migration or medical content was added.

The public-contract suite now runs its database-backed cases against both SQLite and independently migrated, seeded, disposable PostgreSQL databases when POSTGRES_TEST_URL is configured before collection. Existing migration/adoption, bootstrap, backup/restore and startup safety checks remain in the full suite.

## Executed local validation

- Python 3.11 using the committed dependency lock.
- Initial reconciled SQLite suite: 92 passed, one dependency deprecation warning, 3.60 seconds.
- Final combined SQLite/PostgreSQL 15 suite: 138 passed, one dependency deprecation warning, 15.00 seconds.
- Dependency graph consistency: no broken requirements.
- Container validation: passed. Image runtime, OpenAPI, default/custom ports, root HTML/JSON, health, API endpoints, migration/CLI packaging, controlled bootstrap/refusal and durability across container recreation were checked. Temporary containers and volumes were cleaned by the validation script.
- Whitespace and integration ancestry checks: passed.

The first PostgreSQL attempt used the previous test port while the restarted disposable server was listening on its default port. It failed to connect; the corrected run used the verified local port and passed. This was a test-service connection correction, not an application change.

## Remaining boundaries

No PR, push, integration merge, main merge, deployment, production access or Notion status update was performed. Remote CI has not run for this new local branch. Final review and any remote check requirements remain before accepted merge. The original L010 branch is preserved; use the reconciliation branch as the current candidate.

L004 still needs rights/corpus acceptance. L005–L007 still needs reconciliation with L004's migration path and shared files before those changes can coexist. This L010 candidate does not claim to solve those later integration conflicts or to grant source publication rights. WHO/Cancer Australia approvals are not prerequisites for the L010 contract correction.
