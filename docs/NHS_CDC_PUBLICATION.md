# NHS and CDC unchanged excerpt publication

This release appends 17 NHS clinical excerpts and one CDC screening excerpt.
All 347 original records, their citations and versions remain unchanged.
No WHO document or record is approved or modified. Four older NHS paraphrases,
two changed extracts, contact/link lists and footer fragments remain internal.

NHS excerpts were compared with the visible official page text after whitespace
normalization. They retain original wording, headings and context. Copy dates
and exact source links accompany each excerpt. They use the unchanged-copy
route under NHS terms section 3.6(a), including the dated NHS attribution and
service-level OGL notice. They are scoped to England. No adapted NHS content or
NHS-derived consensus is approved. Consumers must carry these notices through
to presentation and must not impose a specific charge for NHS content.

The CDC record is a verbatim screening-recommendations paragraph retaining the
45-to-75 range and the individual decision for ages 76 to 85. Its quote is exact.
The original paraphrase and its inaccurate quote remain preserved internally.
CDC, ATSDR, HHS and US Government nonendorsement and free-original notices
accompany the excerpt and appear in the portal/API documentation. Logos,
third-party components, altered substantive content and framed pages are not
licensed by this decision. Applicable international copyright rules still apply.

Migration 0005 adds a nullable document publication_record_reviews JSON field.
Public SOURCE_CONTENT requires a review matching record ID, exact content and
quote hashes, original source URL and copy timestamp. Missing, malformed,
revoked or stale reviews fail closed. Source/URL/document rights gates still
apply. The review does not clear older historical text or derived consensus.
Cleared historical copies carry version-specific source attribution, copy dates
and reuse notices in the additive history sources field.
New ingestion defaults to structured output, which these documents do not
permit for delivery. Modifying an excerpt automatically withholds it until a
new exact review. No approval depends solely on an NHS/CDC source identity.

The exact plan is policies/nhs-cdc-excerpts-20261102.json. The controlled
scripts/publish_reviewed_excerpts.py defaults to rollback, checks original
content hashes, appends deterministic records/citations/history, checks the
exact public manifest and refuses conflicting reviews. Reapplication is a
no-op. A failed application must roll back the caller's transaction.

Deploy after backup/restore rehearsal, full tests, PR CI and deliberate schema
and policy application. Expected totals: 365 stored records, 264 public records,
60 WHO provenance rows and 5628 legacy rows. The original local research and
staging files are not replaced by the production release.

Official policies reviewed November 2, 2026:

- https://www.nhs.uk/our-policies/terms-and-conditions/
- https://www.nhs.uk/our-policies/terms-and-conditions/content-not-licensed-for-re-use/
- https://www.cdc.gov/other/agencymaterials.html
- https://www.cdc.gov/colorectal-cancer/screening/
