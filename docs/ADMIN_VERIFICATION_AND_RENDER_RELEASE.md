# Administrator verification and Render release gates

## Credential check

GET /v1/admin/verify accepts the existing X-Admin-Key or Authorization: Bearer header. Valid credentials return HTTP 200 with data.authenticated=true in the standard envelope; missing or invalid credentials return 401. The endpoint does not depend on a corpus session, run ingestion, seed data, or return credentials, client addresses, or environment values. Responses use private, no-store caching. Normal request accounting still applies, so production verification can update ephemeral rate counters and can return 429 or 503. It is not a database readiness probe.

Use it after an authorized credential rotation to verify the replacement succeeds and the retired credential fails. Use a secret manager or secure HTTP client; do not place keys in URLs, chat, logs, screenshots or shell history. Generate a random 64-character hexadecimal replacement and update authorized admin consumers at cutover. Render Save only stages a value; the running process uses its previous value until a deployment activates the change. A rollback must retain the replacement key.

## Proxy investigation, November 4, 2026

Verified Render environment has ADMIN_API_KEY, DATABASE_URL and ENVIRONMENT only, with no linked environment groups. ENVIRONMENT is production. TRUSTED_PROXY_CIDRS is absent, so the candidate defaults to an empty list. The Docker command override is empty; the candidate Dockerfile leaves forwarded-header processing to app/core/security.py and preserves the socket peer. Auto-deploy is On Commit on main; health path is /health.

An empty trust list ignores forwarded identities. If the socket peer is a Render proxy, users through that peer share its quota. This preserves resistance to forged headers but does not establish fair per-client limits.

Render's official FastAPI guidance recommends limiting trust to managed load-balancer IPs or CIDRs and warns against trusting every peer. It does not supply the verified ingress ranges for this service. Render outbound ranges describe egress to external systems, not the ingress peers required here. Neither a single observed peer nor all private address space establishes an appropriate allowlist.

Required before production acceptance:

1. Obtain Render's supported ingress peer ranges and forwarding contract for this service, including how user-supplied and duplicate X-Forwarded-For headers are handled and whether peer ranges can change. This requires platform confirmation; no support message was sent by this change.
2. Validate raw socket peer and forwarding behavior using an isolated candidate service with disposable data. Use bounded private diagnostics with no credentials or public IP-echo endpoint. Check IPv4 and IPv6 where supported.
3. Set TRUSTED_PROXY_CIDRS to a JSON list of only confirmed ranges. Do not trust all networks, guess ranges, or use the service's outbound ranges. Preserve right-to-left chain validation and malformed-header fallback.
4. Test independent clients, forged prefixes, duplicate and malformed headers, quota isolation, 429 responses, restart persistence and proxy changes. Existing automated tests cover parser and shared-accounting behavior, but do not prove Render's live ingress contract.
5. If Render cannot provide a stable trust boundary, choose a gateway with authenticated origin access and an explicit forwarding contract, or redesign authenticated client quotas. Do not silently switch to arbitrary first-header trust.

Official sources:

- https://render.com/articles/fastapi-production-best-practices
- https://render.com/docs/outbound-ip-addresses
- https://render.com/docs/configure-environment-variables

## Promotion constraints

PR22 requires 0006_shared_rate_limits. Live remains 0005_record_publication. The migration adds only rate_limit_buckets, its expiry index and the Alembic version change; no corpus or rights updates. Candidate production startup rejects 0005. Main's On Commit deployment makes merging PR22 a deployment trigger.

Do not merge PR22 or deploy this candidate while live schema changes are prohibited. The verification endpoint can be reviewed and merged into launch_blockers independently. Remaining release gates include proxy confirmation, rotation of the previously exposed administrator credential, a fresh backup and coordinated migration/application rollout. WHO commercial access remains blocked; no data or policy changes are included here.
