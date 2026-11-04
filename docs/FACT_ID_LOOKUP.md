# Fact ID lookup

`GET /v1/facts?ids=<comma separated IDs>` resolves up to 50 content record and consensus item IDs for saved citation revalidation. It returns `{"data": [...], "meta": {...}}`. Each item uses the same `SearchResultItem` schema and serializer as `/v1/search`, including cancer, record, consensus and source fields. The request order is retained; repeated IDs appear once. Lookup results have an empty `matched_terms` list because no text query was run.

Unknown, inactive and withdrawn IDs are omitted. The response remains HTTP 200, including when no IDs resolve. Missing, empty or malformed ID lists and lists over 50 return the existing HTTP 422 `VALIDATION_ERROR` envelope. The route uses the same request headers, rate limit, publication use key and rights gates as the other public endpoints. No database migration or new configuration setting is required.

Example:

```bash
curl 'http://localhost:3000/v1/facts?ids=record-id,consensus-id'
```

For local development, create a virtual environment, install `requirements.txt`, set `DATABASE_URL` to a disposable SQLite database, run `alembic upgrade head`, run `python scripts/bootstrap.py`, then start `python -m uvicorn app.main:app --host 127.0.0.1 --port 3000`. The root README contains the full commands and production configuration notes.

The generated `/openapi.json` includes this route. The older `rapidapi/rapidapi-openapi.json` is an incomplete eight path marketplace draft and does not include it. A consumer using the direct hosted API can use this route after deployment; a consumer using a RapidAPI imported catalog needs a separately reviewed marketplace spec update.
