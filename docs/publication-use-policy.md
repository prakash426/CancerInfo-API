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

## November 2 corpus decision

The exact, reviewable transition is in policies/publication-20261102.json.
It is bound to document IDs, original URLs, content hashes and prior field values,
and declares the exact public record manifest. The controlled script defaults
to a transaction rollback; applying it requires the explicit apply option.
It refuses changed documents, later conflicting decisions, unsupported fields
and unexpected public visibility. Repeated application is a no-op.

The release subset has 246 active records from 24 reviewed documents: NCI text,
MedlinePlus's own topic summary, Te Aho o Te Kahu text and reviewed AIHW, CBS,
Eurostat, ONS and Statistics Canada observations. Attribution and licence
conditions are included in response provenance. Five dataset documents retain
the catalogue original_url while canonical_url identifies the exact reviewed
resource cited by the data. Citations, statistics and all historical data are
unchanged; unrelated same-publisher URLs still fail.

WHO remains PERMISSION_PENDING. NHS remains REVIEW_REQUIRED pending its
adaptation/attribution handling; the CDC item remains REVIEW_REQUIRED because
its policy could not be reverified for this release. No research record is
removed. This is a deliberately smaller public subset, not loss of corpus data.

The subsequent NHS/CDC excerpt release is described in
[NHS and CDC publication](NHS_CDC_PUBLICATION.md). It clears only 17 unchanged
NHS excerpts and one exact CDC paragraph, using per-record review hashes and
mandatory notices on category, search and history responses. The original
paraphrases stay internal; WHO remains permission-pending. Apply migration
0005 first, deploy the new notice-aware code, then activate the reviewed plan.
This prevents the preceding release from publishing history without notices.
