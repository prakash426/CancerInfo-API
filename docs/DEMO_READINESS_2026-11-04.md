# Demo readiness check, November 4, 2026

## Candidate and checks

The reviewed local branch was `launch_blockers` at `cd9ed1c4fd5a04bd1eefd64b7cb5fc9872a62763`. GitHub `main` was `3f12f6ab346bd11b3604d747ebd625def3cf6790` and had the same tracked file tree before the local changes below. Its [quality pipeline](https://github.com/prakash426/CancerInfo-API/actions/runs/41862478553) completed successfully.

The Python 3.11 local suite passed twice at 295 passed, 10 skipped and one Starlette deprecation warning. A focused readiness timeout and concurrency check passed after the local fix. Dependency consistency, tracked artifact guard and whitespace checks passed. The 10 skipped cases require a local PostgreSQL service, which was unavailable. Docker was installed, but its engine was not running. The successful `main` pipeline supplies PostgreSQL and container coverage for the pre-fix commit.

A disposable SQLite database upgraded through Alembic revision `0006_shared_rate_limits`, completed controlled bootstrap and served HTTP checks. Liveness, readiness, cancers, sources, coverage, search, content and OpenAPI returned 200. Unknown category returned 404 and invalid pagination returned 422. Responses had request IDs. No local corpus or production database was modified.

A modest local concurrency smoke check sent 40 requests across cancer listing, search, coverage and content with eight workers. All returned 200; observed request latency was 0.144 seconds at the 95th percentile and 0.152 seconds at the maximum. This is a disposable local SQLite check, not a capacity measurement of the deployed service.

## Public deployment

The [public readiness endpoint](https://cancerinfo-api.onrender.com/v1/ready) returned 200 with `database: connected`, 11 registered sources and 25 cancers. Its first request took 32.3 seconds. Warm requests took 2 to 5 seconds: cancer listing and search returned 200, an unknown category returned the expected 404, and OpenAPI returned 200. The deployed OpenAPI JSON matched the local application's 17 paths exactly.

For a live demo, call readiness ahead of the presentation and wait for 200 before showing the first content request. The observed first request delay is a real timing risk. This check did not measure sustained load, multiple workers, external gateway behavior, clinical content accuracy, or marketplace acceptance.

## Local changes awaiting release

Readiness probes now retain a concurrency permit until a timed out worker finishes. The regression test measures peak active probes under a simulated database hang. The two candidate reports were moved into `docs/` without changing their names, and their test and documentation references were updated. The README status was refreshed with dated evidence. Code commit `39206325d5274bfdce7b6388a46f4b8febbbe8c4` is pushed to `launch_blockers` and passed the [full GitHub pipeline](https://github.com/prakash426/CancerInfo-API/actions/runs/41885088136), including PostgreSQL and container checks. It is not yet merged into `main` or deployed.

GitHub branch review found no work that needed merging into `launch_blockers`. Sixteen obsolete remote branches were deleted; only `main` and `launch_blockers` remain. The separate commit on `fix/CIAPI-L010-public-response-contract` matched the integrated public response files, except that its older application startup created and seeded tables automatically. The merged code retains controlled migration and bootstrap.
