# Access, request limits and database readiness

This candidate changes request controls and health reporting. It does not grant publication rights, change source decisions, import content, or modify WHO permissions. No migration or deployment is performed merely by opening this PR.

## Administrator access

Production startup rejects the built-in development key, empty values, documented placeholders, and keys shorter than 32 ASCII characters or containing whitespace. Generate a random secret using a password manager or `python -c 'import secrets; print(secrets.token_urlsafe(32))'`. Store it in the deployment secret manager as `ADMIN_API_KEY`. Never put it in Git, logs, examples or PR evidence. Settings validation hides supplied values, and administrator comparisons use constant-time comparison. Missing and wrong credentials return the same 401 response. Production seeding remains disabled.

## Proxy identity

`TRUSTED_PROXY_CIDRS` defaults to an empty JSON list. Forwarded addresses have no authority unless the actual socket peer belongs to an explicitly configured trusted proxy network. Trust-all IPv4 and IPv6 networks are rejected. The chain is evaluated from the socket peer toward the client, stopping at the first untrusted address. Malformed, duplicate and oversized forwarding chains use the socket peer conservatively. Neither `X-Real-IP` nor an arbitrary forwarded prefix grants a new allowance.

The Docker entry point disables Uvicorn proxy-header rewriting so the application sees the real socket peer. Custom process commands must also disable that rewriting. Before a future Render deployment, verify the platform's actual proxy peer addresses and header append/overwrite behavior, configure only those trusted networks, and confirm two real clients receive separate allowances. Do not guess a broad private-network trust range. With no trusted proxies configured, clients sharing a proxy share its allowance; this is a deliberate conservative default.

See the official [Uvicorn proxy settings](https://uvicorn.dev/settings/).

## Shared production limits

Production uses PostgreSQL request accounting. All workers, replicas and restarts using the same database share a sliding 60-second window, with `RATE_LIMIT_PER_MINUTE` requests per resolved client address. Anonymous and approved-use keys share this IP allowance; a key does not buy a separate quota. The default remains 120. Limits must be between 1 and 10,000. Concurrent checks serialize on the same bucket using PostgreSQL row locks. Database time determines expiry, avoiding worker-clock differences. Rejected requests do not extend the window. `Retry-After` and `X-RateLimit-Reset` report rounded-up seconds until the oldest counted request expires.

Migration `0006_shared_rate_limits` creates only `rate_limit_buckets` and its expiry index. It stores a SHA-256 address identifier, accepted-request timestamps, and expiry. This is pseudonymous operational accounting, not medical content. Each bucket contains at most the configured allowance of recent timestamps. Each accounted request removes up to 100 expired, unlocked buckets. Idle deployments can retain expired buckets until traffic resumes; expired timestamps never count toward a new allowance. No original records, citations, versions, WHO provenance, permissions, research or legacy tables are rewritten. Downgrading this migration removes only request accounting.

The table remains part of schema parity, bootstrap and foreign-key inventories. Corpus preservation digests exclude request accounting explicitly because serving a request must not change the corpus identifier. Exact backups can still include the operational table. SQLite and development use a thread-safe local limiter with a bounded client map and expired-client cleanup; it is not a shared production backend.

If PostgreSQL accounting fails, ordinary requests receive a sanitized 503 `RATE_LIMIT_UNAVAILABLE` with a five-second retry hint. The API does not fall back to unlimited access. Row-lock waits are bounded to one second and statements to three seconds. Application PostgreSQL connections have bounded connect, pool-wait and statement timeouts, configurable within validated bounds. Health, readiness, root and exact documentation routes are exempt; similarly named paths are not. CORS preflight is handled outside request accounting; allowed browser origins also receive CORS headers on 429 and 503 denials and internal errors.

See the official [PostgreSQL locking clauses](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE).

## Readiness and response handling

`/health` and `/api/health` remain static liveness probes. `/v1/ready` and the existing `/v1/health` verify database access, the all managed table and column names, including the registry/accounting schema and, in production or explicit migration-check mode, the expected Alembic revision. They return 200 while ready and 503 with `database: unavailable`, zero registry counts, and `Retry-After: 5` when unavailable. They roll back failed read transactions and never migrate, seed or repair data.

Failure messages and log events do not include database exceptions, credentials, request bodies, query strings, or submitted authentication headers. Readiness, accounting failures and unexpected request failures log server-generated request IDs. Success, validation errors, routing errors, rate denial, dependency failure and internal errors carry the same request, timing, rate, disclaimer, version, publication-use and private/no-store cache headers.

A future deployment should configure the platform's readiness check to `/v1/ready` and monitor its 503 responses separately from process liveness. Alert delivery, incident ownership, full staging load acceptance and a safe application rollback drill remain separate operational work. This PR does not configure external alerts or authorize a deployment.

## Future rollout checks

1. Back up the selected production database and verify the recovery target.
2. Provision a strong admin secret and verified proxy trust before starting the candidate.
3. Rehearse and apply the additive migration through the controlled release process. Startup refuses an old schema; no implicit migration runs.
4. Verify readiness, separate client allowances, forged-forwarding rejection, 429/503 headers, restart/multiworker continuity, administrator denial and required WHO exclusion against the accepted release.
5. Record the exact candidate, schema, corpus and CI evidence before an owner-authorized deployment.
