# Marketplace and client artifacts

| File | What it is |
| :--- | :--- |
| [`rapidapi-openapi.json`](rapidapi-openapi.json) | Public OpenAPI 3.1 contract: the 15 public `GET` routes, with administrative routes removed. Server: `https://cancerinfo-api.onrender.com`. |
| [`postman_collection.json`](postman_collection.json) | Ready-to-run Postman collection. `baseUrl` defaults to the hosted API; set it to `http://localhost:3000` for local work. |

## Regenerating the public contract

The public file is generated from the running application's schema, so it never drifts from the code:

```bash
python scripts/export_public_openapi.py
```

`tests/test_public_contract.py` fails if the committed file no longer matches the runtime contract or if an administrative route leaks into it. Regenerate and commit the file whenever a public route, parameter or response model changes.

## Marketplace listing

Plan allowances, quotas and platform fees for the marketplace listing are documented in [Hosted API access and usage](../docs/ACCESS_AND_USAGE.md). The published Pricing tab on the marketplace always governs a subscription.
