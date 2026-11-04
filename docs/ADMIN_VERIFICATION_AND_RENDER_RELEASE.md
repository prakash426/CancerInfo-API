# Administrator verification and Render release gates

## Credential check

GET /v1/admin/verify accepts the existing X-Admin-Key or Authorization: Bearer header. Valid credentials return HTTP 200 with data.authenticated=true in the standard envelope; missing or invalid credentials return 401. The endpoint does not depend on a corpus session, run ingestion, seed data, or return credentials, client addresses, or environment values. Responses use private, no-store caching. Normal request accounting still applies, so production verification can update ephemeral rate counters and can return 429 or 503. It is not a database readiness probe.

Use it after an authorized credential rotation to verify the replacement succeeds and the retired credential fails. Use a secret manager or secure HTTP client; do not place keys in URLs, chat, logs, screenshots or shell history. Generate a random 64-character hexadecimal replacement and update authorized admin consumers at cutover. Render Save only stages a value; the running process uses its previous value until a deployment activates the change. A rollback must retain the replacement key.

## Render public-ingress client identity

The service is a public Render Free Docker web service. Render's official PocketBase deployment guide states that Cloudflare overwrites CF-Connecting-IP on public web requests. Render's Free-service documentation states that Free web services cannot receive private-network traffic. This supports an explicit public-ingress header mode without guessing changing internal proxy CIDRs.

Set TRUST_RENDER_CF_CONNECTING_IP=true only for this public ingress topology. Configuration refuses this mode unless the platform supplies RENDER=true and RENDER_SERVICE_TYPE=web. These environment markers are configuration guards, not cryptographic proof of the request path. Any future move to a paid plan, private/direct ingress, or another platform requires reviewing that boundary before retaining the setting. Untrusted callers must not reach the app through a path that bypasses Cloudflare's header overwrite.

In this mode the API accepts exactly one CF-Connecting-IP containing a single valid IPv4 or IPv6 address. Missing, duplicate, oversized, list-valued, scoped or invalid values fall back conservatively to the socket peer. X-Forwarded-For and True-Client-IP cannot override it or rescue malformed values. Outside this mode, the existing explicit TRUSTED_PROXY_CIDRS chain processing remains unchanged. The default is false, and trust-all networks remain forbidden.

Stage TRUST_RENDER_CF_CONNECTING_IP=true using Render Environment Save only. Leave TRUSTED_PROXY_CIDRS=[]; do not insert guessed ingress ranges, outbound IPs, or all private networks. Candidate Docker CMD must continue preserving socket identity. Saving does not activate this behavior on the old image; it requires a later authorized deployment of the new code.

Before production acceptance, confirm the service is still public Free with no direct/private ingress. After the later deployment, test two independent networks and forged CF-Connecting-IP and X-Forwarded-For inputs through the public URL, confirming that the edge overwrites forged identity and quotas remain independent. Automated tests verify application parsing and client isolation, not actual Render routing. No public IP-echo endpoint is added. Private diagnostics, if necessary, must exclude credentials and have bounded retention. If this topology changes, disable the header mode until the replacement trust boundary is verified.

Official sources:

- https://render.com/articles/host-pocketbase-on-render (public CF-Connecting-IP overwrite contract)
- https://render.com/docs/free (Free instances cannot receive private-network traffic)
- https://render.com/docs/environment-variables (platform markers)
- https://render.com/docs/configure-environment-variables (Save only defers activation)

## Promotion constraints

PR22 requires 0006_shared_rate_limits. Live remains 0005_record_publication. The migration adds only rate_limit_buckets, its expiry index and the Alembic version change; no corpus or rights updates. Candidate production startup rejects 0005. Main's On Commit deployment makes merging PR22 a deployment trigger.

Do not merge PR22 or deploy this candidate while live schema changes are prohibited. The verification endpoint can be reviewed and merged into launch_blockers independently. Remaining release gates include staging and later validating the Render public-ingress mode, rotation of the previously exposed administrator credential, a fresh backup and coordinated migration/application rollout. WHO commercial access remains blocked; no data or policy changes are included here.
