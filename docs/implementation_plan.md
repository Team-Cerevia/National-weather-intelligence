# National Weather Intelligence Platform — Master Implementation Plan

## Problem Statement Alignment: National Weather Big Data Analytics Platform

Per the SIH Problem Statement, our architecture addresses 5 core pillars:
1. **Multi-Source Real-Time Ingestion:** Social media (#IMD & weather hashtags, GPS, photos/videos), public datasets, news/websites, weather APIs, citizen reports.
2. **AI/ML Intelligence & Verification:** Categorization (rainfall, thunderstorms, flooding, heatwaves, fog, dust storms, strong winds), fake/misleading report detection, untrusted source verification, semantic deduplication, spatio-temporal incident clustering.
3. **Evidence & Evolution Provenance:** Multi-source supporting/contradicting evidence aggregation, source trust weighting, incident state evolution.
4. **Geospatial & Big Data Storage:** H3 spatial hexagonal indexing + PostGIS spatial proximity + `pgvector` text embeddings.
5. **Interactive Dashboard & Admin Panel:** Real-time GIS India map, Date/Event/Location/Verification filtering, and **"Why is this real?" Evidence Provenance Drawer**.

---

## Decoupled Multi-Track Team Workload Division

To maximize hackathon velocity and avoid merge conflicts, work is divided into **decoupled tracks** linked by **Shared Contracts (`contracts/`)**:

```text
                              SHARED CONTRACTS FOUNDATION
                                      (contracts/)
                     WeatherReport, EvidenceItem, Incident
                                       │
     ┌─────────────────┬───────────────┼───────────────┬─────────────────┐
     ▼                 ▼               ▼               ▼                 ▼
  TRACK A1          TRACK A2        TRACK B         TRACK C           TRACK D
Social & News      APIs & Data     Streaming     Intelligence      Backend & UI
 (Teammate A1)    (Teammate A2)   (Teammate B)   (YOU / Lead AI)   (Teammate C)
──────────────    ─────────────   ────────────   ───────────────   ────────────
• #IMD Social     • Open-Meteo    • Redis        • Pre-trained     • PostgreSQL +
  Scraper /         API Adapter     Streams        CPU NLP           PostGIS +
  Parser          • IMD API /       Broker       • Incident          pgvector
• News RSS          Fixtures      • Producer &     Engine          • FastAPI REST
  Feed Parser     • Public Data     Consumer     • Evidence          APIs
• Hashtag &         CSV/JSON      • Retry &        Engine          • WebSockets
  Media Extractor • Citizen Ingest  DLQ          • Evolution       • Leaflet GIS
• Social Fixtures • Synthetic     • Replay         Engine            India Map &
                    Stream Replay   Engine       • Intelligence      Admin Panel
                                                   Orchestrator    • Provenance UI
```

---

## Master Track Summary

| Track | Owner | Status / Branch | Core Responsibility | Guide |
| :--- | :--- | :--- | :--- | :--- |
| **Track A1** | Teammate A1 | 🔄 `feat/data-ingestion-social` | Social Media (#IMD, hashtags), News RSS feeds, Media extractors | [`docs/track_a1_social_news.md`](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/docs/track_a1_social_news.md) |
| **Track A2** | Teammate A2 | ✅ **DONE** (`main`) | Open-Meteo API, IMD Data, Public CSVs, Citizen REST ingest | [`docs/track_a2_api_data.md`](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/docs/track_a2_api_data.md) |
| **Track B** | Teammate B | 🔄 `feat/streaming` | Redis Streams broker, Producer, Consumer Groups, Retry/DLQ, Replay | [`docs/track_b_streaming.md`](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/docs/track_b_streaming.md) |
| **Track C** | YOU (AI Lead) | 🔄 `feat/intelligence` | Pre-trained NLP, Incident Clustering, Evidence Verification, Evolution | [`docs/track_c_intelligence.md`](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/docs/track_c_intelligence.md) |
| **Track D1** | Teammate C | 🔄 `feat/backend-foundation` | PostgreSQL + PostGIS, Docker Compose, FastAPI REST & WebSockets | [`docs/track_d1_backend.md`](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/docs/track_d1_backend.md) |
| **Track D2** | Frontend/UI | 🔄 `feat/frontend-dashboard` | Leaflet GIS India Map, Filters & Evidence Provenance Drawer UI | [`docs/track_d2_frontend.md`](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/docs/track_d2_frontend.md) |

---

## Environment & Credential Security Guidelines

1. **Never Commit Secrets or API Keys:** Hardcoding API keys, passwords, database credentials, or tokens in source code is strictly forbidden.
2. **Use `.env` for Local Secrets:** Create a `.env` file locally by copying `.env.example` in the project root:
   ```bash
   cp .env.example .env
   ```
3. **`.gitignore` Enforcement:** The `.env` file and all variations (`.env.*`, `.env.local`) are explicitly gitignored. Verify `git status` before committing to ensure no credentials are staged.
4. **Accessing Variables in Python:** Use `os.getenv()` or `pydantic-settings` to load configuration from environment variables.

---

## Integration Flow

```text
[Track A1: Social/News] ──┐
                          ├──► [Track B: Streaming] ──► [Track C: YOUR Intelligence] ──► [Track D: DB & Dashboard]
[Track A2: APIs/Data]   ──┘
```

Because **Track C** takes contract objects (`WeatherReport`) and outputs contract objects (`Incident`, `VerificationSummary`), all tracks can be developed and tested in 100% parallel using contract objects and mock fixtures!
