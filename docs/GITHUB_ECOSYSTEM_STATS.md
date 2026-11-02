# GitHub Open API Ecosystem: Publication, Discovery & Usage Statistics

## Current guidance, September 22, 2026

This guide applies to Python refactor `1199f735e3d77b5c1ada35e6451c7a5b4e36d063`. Current guidance below supersedes the prior draft retained at the end.

### Success metrics

Acceptance metrics should measure the final published corpus and release: every published record has reviewed document rights and supporting citation; unknown publisher dates remain unknown; denied records never appear in public paths; candidate CI and image/staging/gateway checks pass; a restore succeeds; documented endpoints match the public contract.

Current measured baseline is 28 passing local tests plus four reproduced defects, 21 seeded records across five cancers and five categories, and 15 generated OpenAPI paths versus 8 static paths. These are engineering observations, not clinical quality or adoption metrics.

Choose latency, availability and support targets after selecting hosting and expected traffic. No production traffic, users, uptime, costs, medical outcomes or test-coverage percentage was verified. Do not reuse unsupported ecosystem statistics as project success evidence.

### Problem and audience

The project addresses developers’ need to retrieve structured cancer information with visible sources, jurisdiction and coverage limitations. Its core deliverable is a reusable Python API that independent applications can consume.

The owner explicitly rejected the unsolicited Node/React application as part of the current API product and retained it only for possible future demonstration. Bob is the owner’s name for the code-authoring assistant. The original personal motivation remains part of the project story; it is not evidence of clinical correctness or market adoption.

Intended audiences include developers building educational and source-transparent informational tools. No user research, adoption counts or medical outcome evidence was established by this repository review. Product descriptions should state implemented retrieval capabilities and distinguish future concepts.

### Platform opportunities

The most relevant follow-up is a small API demonstration client that uses the same published API as external consumers. The archived cancerinfo-explorer-ui directory and ZIP provide a starting point, not a certified runnable product. A source import in GoogleDriveSync refers to a missing service and Firebase is absent from its declared dependencies; no UI build was run here.

A future demo should show endpoint, response, record citation, jurisdiction, freshness limitations and empty coverage without its own clinical dataset. Swagger and ReDoc already provide API exploration within FastAPI, so a richer UI is not a launch prerequisite.

Other opportunities remain educational integrations and source-transparent developer tools. No traffic, revenue, adoption or clinical outcome estimate is supported by this repository. Prior ecosystem statistics without cited evidence must not be used in launch claims.

### Evidence correction

The earlier numerical benchmarks, demographic shares, traffic ratios, directory conversion estimates and virality predictions have no supporting sources in this repository. They are withdrawn as project evidence. No inference about the owner’s family circumstances should be made from the earlier marketing examples. Retain only a project-specific discovery plan: accurate README, tested examples, clear support path, verified release URL and honest coverage. Gather actual usage after release before reporting adoption.

## Historical draft, not current instructions or verified claims

The following original draft is retained to preserve review history. It may contain obsolete commands, unsupported numbers, clinical examples and unverified readiness claims. Do not execute or publish those claims without replacing them with the current accepted implementation and evidence.

## GitHub Open API Ecosystem: Publication, Discovery & Usage Statistics

This report answers: **How do developers publish public APIs on GitHub, how are they discovered, who uses them, and how often?**

---

### 1. Executive Statistics & Industry Adoption Overview

| Metric Category | Industry Benchmark (Public Health & Scientific APIs) |
| :--- | :--- |
| **Total Public APIs Globally** | 50,000+ active public APIs across GitHub and API Hubs |
| **Developers on RapidAPI Hub** | 4.2+ Million registered developers |
| **Average Monthly Calls (Top Public Health APIs)** | 1.8M – 15M requests / month per service |
| **Median Time to First 1,000 GitHub Stars** | 4.2 months for well-curated healthcare datasets |
| **Open Source Licensing Ratio** | 88% MIT or Apache 2.0 / 12% AGPL/GPL |

---

### 2. Developer Demographic Breakdown: Who Uses Public Health APIs?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   PUBLIC HEALTHCARE API USER DISTRIBUTION                   │
├───────────────────────────────────────────────────────┬─────────────────────┤
│ Developer / Organization Segment                      │ Percentage (%)      │
├───────────────────────────────────────────────────────┼─────────────────────┤
│ 🚀 HealthTech & Biotech Startups (MVPs, Telehealth)   │ ████████████ 34%    │
│ 🎓 Academic, University & Clinical Researchers        │ ██████████ 28%      │
│ 🎗️ Patient Advocacy & Non-Profit Mobile Apps          │ ████████ 22%        │
│ 💻 Independent Hackathon Builders & CS Students       │ ██████ 16%          │
└───────────────────────────────────────────────────────┴─────────────────────┘
```

#### Primary Use-Cases & Request Volume:
1. **AI / LLM Grounding & RAG Pipelines (42% of traffic growth)**:
   Developers integrate APIs like CancerInfo to prevent hallucination in oncology medical chatbots and patient assistants.
2. **Clinical Navigation & Patient Portals (26% of traffic)**:
   Community clinics, telehealth services, and non-profits fetch structured symptoms and screening guidance.
3. **Academic Epidemiological Dashboards (18% of traffic)**:
   Researchers cross-correlate cancer types, anatomical sites, and jurisdictional screening policies.
4. **Educational Tools & Student Projects (14% of traffic)**:
   Bioinformatics and medical students building portfolio apps and diagnostic helpers.

---

### 3. How Developers Post Public APIs on GitHub (The Standard Formula)

Successful open-source public APIs on GitHub follow a 5-pillar structure:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 ANATOMY OF A VIRAL GITHUB PUBLIC API REPO                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [1] Heartfelt / Clear Value Pitch ──────► Explain the 'Why' in 2 sentences │
│  [2] Badges & Live Status Indicator ─────► Builds instant trust & shows live│
│  [3] One-Click Quickstart ───────────────► curl command / docker compose up │
│  [4] Interactive Explorer / Swagger ─────► Developers test before cloning   │
│  [5] Direct Topic Tags & Directory PRs ──► #api #cancer #health #fastapi    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Essential GitHub Topic Tags to Apply:
Add these topics in the GitHub repository settings (About section):
`#api` `#cancer` `#healthcare` `#oncology` `#fastapi` `#public-api` `#rest-api` `#rapidapi` `#open-data` `#bioinformatics` `#python`

---

### 4. How APIs Get Discovered & Shared Worldwide

Developers discover public APIs through 4 primary distribution channels:

```
                  ┌────────────────────────────────────────┐
                  │        API DISCOVERY CHANNELS          │
                  └──────────────────┬─────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
         ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  GitHub Repos    │       │  RapidAPI Hub    │       │  Postman Network │
│  public-apis     │       │  & API Market    │       │  & Open APIs     │
│  (330k+ Stars)   │       │  (4M+ Devs)      │       │  (30M+ Users)    │
└──────────────────┘       └──────────────────┘       └──────────────────┘
```

1. **The `public-apis/public-apis` GitHub Repository** (Over 330,000 GitHub Stars):
   - A directory developers use to discover APIs. Check its current submission rules and describe the API’s access requirements accurately.
2. **RapidAPI Hub**:
   - An API marketplace where developers can review the listing and subscription plans. Describe the Basic plan and applicable platform charges in the pricing section; do not promise recommendation or placement.
3. **Hacker News (Show HN)**:
   - Genuine, mission-driven developer projects with personal stories (like honoring parents lost to cancer) routinely reach the front page of Hacker News, attracting thousands of contributors and stars.
4. **Product Hunt**:
   - Present the API as a developer tool under suitable health and developer categories. Link to the current subscription and usage terms wherever pricing is discussed.

---

### 5. Traffic Frequency & Consumption Patterns

- **Weekdays vs Weekends**: 72% of requests occur Monday–Friday during business hours (clinical software development, university research).
- **Batch vs Realtime**: 60% of consumers query endpoints in real-time (apps/search), while 40% run scheduled nightly batch queries to cache updates.
- **Cache Hit Ratio**: With proper `ETag` and HTTP caching, public health APIs achieve 85%+ cache hit ratios, allowing inexpensive hosting to support millions of calls.
