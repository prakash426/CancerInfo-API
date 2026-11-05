# CancerInfo API documentation

## Using the API

| Guide | Covers |
| :--- | :--- |
| [Usage guide](USAGE_GUIDE.md) | Client examples in cURL, Python, TypeScript, Go, Kotlin and Swift |
| [Public response contract](PUBLIC_RESPONSE_CONTRACT.md) | Resolution rules, filters, pagination, errors and headers |
| [Fact ID lookup](FACT_ID_LOOKUP.md) | Re-validating saved citations with `GET /v1/facts` |
| [Hosted access and usage](ACCESS_AND_USAGE.md) | Marketplace plan, quotas and the software-versus-content license split |

## Data, sources and rights

| Guide | Covers |
| :--- | :--- |
| [Content rights and attribution](CONTENT_RIGHTS_AND_ATTRIBUTION.md) | The document-level, fail-closed rights model |
| [Publication by content type](publication-use-policy.md) | Which content types each approval allows |
| [NHS and CDC excerpts](NHS_CDC_PUBLICATION.md) | How unchanged NHS and CDC excerpts are published and attributed |
| [WHO noncommercial publication](WHO_NONCOMMERCIAL_PUBLICATION.md) | How WHO content is limited to approved noncommercial access |

## Running the service

| Guide | Covers |
| :--- | :--- |
| [Migrations and initialization](MIGRATIONS_AND_INITIALIZATION.md) | Alembic, controlled bootstrap, Render and Neon operations |
| [Access, rate limits and readiness](ACCESS_RATE_READINESS.md) | Admin secrets, proxy trust, shared rate limiting and readiness probes |
| [Admin verification and Render release](ADMIN_VERIFICATION_AND_RENDER_RELEASE.md) | Credential checks and the release checklist |
| [Testing and validation](VALIDATION_GUIDE.md) | Test suite, CI pipeline, smoke tests and container validation |
