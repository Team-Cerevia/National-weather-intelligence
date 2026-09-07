# METEORA — National Weather Big Data Analytics Platform

<p align="center">
  <img src="docs/logo.png" alt="METEORA Logo" width="160" style="border-radius: 50%; border: 2px solid #3d4a3e;" />
</p>

<p align="center">
  <b>Real-Time Weather Incident Ingestion, NLP Evidence Correlation & GIS Command Platform</b>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#core-intelligence-pipeline">Intelligence Pipeline</a> •
  <a href="#technology-stack">Tech Stack</a> •
  <a href="#system-architecture">Architecture</a> •
  <a href="#module-documentation">Module Docs</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#verification">Verification</a>
</p>

---

## Overview

**METEORA** is a National Weather Big Data Analytics Platform built for the **India Meteorological Department (IMD)** problem statement (Smart India Hackathon). 

Unlike standard forecasting apps that display radar or numerical predictions, **METEORA** is a **Ground-Truth Verification & Impact Correlation Engine**. It continuously ingests unstructured reports from social OSINT streams (`#IMD`), news RSS feeds, IMD CAP XML alerts, Open-Meteo APIs, and citizen reports, transforming raw text and media into verified, evidence-backed incident intelligence.

### Key Capabilities
- **Multi-Source Real-Time Ingestion**: Parses IMD CAP XML feeds, RSS news, X/Twitter OSINT, and direct ground observations.
- **NLP & Semantic Interpretation**: Performs event classification, location extraction, negation detection, and 384-dimensional ONNX vector embeddings.
- **H3 Spatial & Temporal Correlation**: Clusters reports into unified incidents using Uber H3 Resolution 7 hexagonal indexing and sliding time windows.
- **Evidence-Based Verification**: Assigns transparent confidence scores and verification states (`SUPPORTED`, `CONTRADICTED`, `UNVERIFIED`, `PENDING_REVIEW`) based on source trust weighting.
- **GIS Command Center & SITREP Export**: Next.js dashboard with interactive MapLibre/Leaflet mapping, real-time WebSockets, and 1-click government SITREP exports (CSV/JSON).

---

## Core Intelligence Pipeline

```
Raw Unstructured Reports
  │ (IMD CAP XML, RSS News, Social OSINT, Citizen Reports)
  ▼
1. NLP Interpretation Engine
  ├── Normalization & Language Filter
  ├── Disaster Relevance & Event Classification (12 Categories)
  ├── Location NER Extraction & Negation Detection
  └── 384-d ONNX Vector Embedding Generation
  ▼
2. Spatial / Temporal / Semantic Correlation Engine
  ├── Uber H3 Resolution 7 Hexagonal Spatial Indexing
  ├── Sliding Temporal Window Matching
  └── Multi-Factor Incident Cluster Formation
  ▼
3. Evidence Aggregation & Confidence Engine
  ├── Source Trust Weighting (IMD: 0.95, News: 0.70, Citizen: 0.45)
  ├── Contradiction & Negation Assessment
  └── Dynamic Priority Score & Verification Status Assignment
  ▼
4. Human Operator GIS Dashboard & SITREP Export
```

---

## Technology Stack

### Backend & Data Processing
- **Language & Runtime**: Python 3.12+ (managed with `uv`)
- **API Framework**: FastAPI, Pydantic v2, Starlette WebSockets
- **Database Layer**: PostgreSQL 16 + PostGIS (geospatial queries) + `pgvector` (vector similarity search)
- **ORMs & Drivers**: SQLAlchemy 2.0 (async), `asyncpg`, `psycopg3`
- **Streaming & Caching**: Redis Streams, Redis Pub/Sub, `redis-py` async

### NLP & AI Pipeline
- **Vector Embeddings**: ONNX Runtime (`all-MiniLM-L6-v2` / `bge-small-en-v1.5`), HuggingFace Tokenizers
- **NLP / Entity Parsing**: spaCy, regex negation rules, custom Location NER extractor
- **Computer Vision**: Perceptual Image Hashing (`imagehash` / dHash), PIL/Pillow EXIF metadata extraction

### Frontend Dashboard
- **Framework**: Next.js 15 (App Router, TypeScript)
- **Styling**: Tailwind CSS (Dark Command Center Theme)
- **Mapping & GIS**: Leaflet.js / MapLibre GL, Custom H3 Overlay Layers
- **Icons & UI**: Lucide React, Custom SVG Weather Badges

### Infrastructure & Tooling
- **Containerization**: Docker, Docker Compose
- **Testing & Quality**: Pytest (async), Ruff (linter/formatter)

---

## System Architecture

```
                               ┌─────────────────────────────┐
                               │   External Data Sources     │
                               │ IMD CAP XML, RSS News,      │
                               │ Social OSINT, Ground Report │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                Ingestion & Streaming Layer                             │
│       ingestion/ (RSS, CAP XML, Weather API) ──> Redis Streams (streaming/)            │
└─────────────────────────────────────────────┬──────────────────────────────────────────┘
                                              │
                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              NLP & Evidence Intelligence                               │
│        nlp/ (Classifier, Embedding Engine, H3 Correlation, Evidence Engine)            │
└─────────────────────────────────────────────┬──────────────────────────────────────────┘
                                              │
                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               Persistence & API Layer                                 │
│         PostgreSQL + PostGIS + pgvector (backend/db) ──> FastAPI (backend/api)          │
└─────────────────────────────────────────────┬──────────────────────────────────────────┘
                                              │
                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              GIS Command Center Frontend                               │
│               Next.js Dashboard + Real-time WebSockets (frontend/)                     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Module Documentation

For deep technical specifications, data contracts, and track architectural breakdowns, refer to the module documentation in [`docs/`](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/docs):

- 📜 [**Contracts & Shared Data Specs**](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/docs/shared_data_contract.md): Pydantic data schemas for `WeatherReport`, `Incident`, and `EvidenceItem`.
- 📡 [**Ingestion Track (Track A1 & A2)**](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/docs/track_a1_social_news.md): RSS feeds, Twitter/X OSINT scrapers, and Open-Meteo API connectors.
- ⚡ [**Streaming Track (Track B)**](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/docs/track_b_streaming.md): Redis Streams queue architecture and async consumers.
- 🧠 [**Intelligence & NLP Track (Track C)**](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/docs/track_c_intelligence.md): ONNX embedding execution, H3 index correlation, and verification algorithms.
- 🖥️ [**Backend API Track (Track D1)**](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/docs/track_d1_backend.md): FastAPI REST endpoints, PostGIS spatial queries, and WebSockets.
- 🎨 [**Frontend Command Center (Track D2)**](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/docs/track_d2_frontend.md): Next.js components, MapLibre map layers, and SITREP generator.

---

## Quick Start

### 1. Prerequisites
- **Python**: 3.12+
- **Node.js**: 18+
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv) (recommended)
- **Docker**: Docker Desktop (for Postgres/PostGIS & Redis)

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/Team-Cerevia/National-weather-intelligence.git
cd National-weather-intelligence

# Install Python dependencies using uv
uv sync

# Configure environment variables
cp .env.example .env
```

### 3. Launch Services & Infrastructure
```bash
# Start PostgreSQL (PostGIS + pgvector) and Redis
docker compose up -d

# Run database migrations / initialization
uv run python -m backend.db.init_db

# Start Backend API server (http://localhost:8000)
uv run uvicorn backend.main:app --reload

# In a new terminal, start Frontend Next.js app (http://localhost:3000)
cd frontend
npm install
npm run dev
```

---

## Verification & Testing

Every major component is independently testable without external mock hidden state.

```bash
# Run full suite of automated unit & integration tests (62 passing tests)
uv run pytest

# Run fast code linting and formatting checks
uv run ruff check .
```

---

## License

Distributed under the MIT License. See [`LICENSE`](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/LICENSE) for more information.
