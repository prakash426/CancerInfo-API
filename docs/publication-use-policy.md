# Publication by content type and approved use

An ELIGIBLE label is necessary, never sufficient. Every citation must still
have exact document/source/URL linkage, review evidence, reviewer, date,
permissible-use determination, redistribution permission, attribution and
resolved third-party rights. Mixed evidence must clear every citation.

## Content types

STRUCTURED_EXTRACTION and DERIVED_SUMMARY require derived_summary_allowed.
They do not require full_text_storage_allowed for delivery. This does not
approve retention of source full text by ingestion or research systems.
SOURCE_CONTENT requires explicit type approval and full_text_storage_allowed.
Translation, AI normalization and manual curation also require explicit type
approval and derivative permission; a summary flag alone cannot approve them.
Unknown and missing record types are withheld. Consensus is DERIVED_SUMMARY.
Historical versions need their own verified type for noncommercial delivery;
current record labels do not retroactively clear historical text. New refresh
snapshots record their content type. Older history remains preserved internally.

## Noncommercial approval

Migration 0004 adds nullable noncommercial_redistribution_allowed and
approved_publication_content_types to source_documents. It does not modify any
existing content or rights decisions. Missing approval means no access.
A rights owner must approve the exact downstream use in permissible_use and
supporting evidence, set redistribution_allowed and the noncommercial decision
true, and list the permitted ContentType values. Existing commercial and
full-text flags must remain truthful. No free-text inference or automatic
conversion of existing ELIGIBLE labels is performed.

The server accepts X-API-Key only when its SHA-256 digest is in the secret
NONCOMMERCIAL_API_KEY_SHA256 JSON list. Issue a random key of at least 32
characters only after reviewing the developer, application, monetization,
downstream display/storage/redistribution and accepted use conditions. Keep
an approval register outside Git. Clients cannot select their own use scope.
Remove the digest and reload configuration to revoke an application's key.
The setting defaults to an empty list. The admin key confers no publication
approval. Anonymous, invalid and commercial callers retain the commercial
permission requirement. No route grants an exception for WHO.

Responses expose the selected use in X-Publication-Use, include document
permissions and attribution in category/search provenance, and use private,
no-store cache control with Vary: X-API-Key. Infrastructure must honor these
headers and must not cache restricted responses independently of the key.
Developer keys constrain API access; they cannot prevent copying or grant
rights absent from the underlying permission.

## WHO remains restricted

Request 202610792 supports selected structured facts, concise paraphrased
summaries and limited attributed excerpts, subject to its conditions. It does
not establish commercial downstream rights. Keep commercial approval false.
Do not approve WHO downstream noncommercial distribution until the scope
questions about standalone distribution, developer republication, future pages
and AI processing are resolved in writing. No WHO review or API key is granted
by this change. Do not treat research/staging records as cleared public data.

## Release procedure

Before deploying this code, back up the database and rehearse migration 0004
on a clone. The existing startup check rejects the old schema. Apply the
additive migration deliberately; never reseed, restamp or replace the corpus.
Approve only an evidenced subset, validate the expected public manifest and
repeat regression checks. Updating schema or rights in production, merging to
main and deploying require a separate authorized release step.
