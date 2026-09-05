# Track D1: Backend Persistence & REST API

> **Owner:** Teammate C (Python Backend)  
> **Branch:** `feat/backend-foundation`  
> **Goal:** Build PostgreSQL + PostGIS database persistence with Docker Compose, FastAPI REST endpoints, and WebSocket feed for incident updates.

---

## Responsibility Boundary

### What You Own
- **Docker Compose Setup (`docker-compose.yml`):** Local PostgreSQL + PostGIS & Redis containers.
- **Database Schema (`backend/db/models.py`, `backend/db/session.py`):** SQLAlchemy ORM models mapping `contracts/` Pydantic models (`Report`, `Incident`, `Evidence`, `Timeline`).
- **FastAPI REST API (`backend/api/routes/`):**
  - `GET /api/v1/incidents`: List/filter incidents by date, event category, location, severity, and verification status.
  - `GET /api/v1/incidents/{id}`: Detailed incident response with evidence provenance list.
  - `POST /api/v1/incidents`: Upsert endpoint for Track C Intelligence engine to save processed incidents.
  - `POST /api/v1/reports`: REST ingest endpoint for raw weather reports.
- **WebSocket Live Feed (`backend/api/routes/stream.py`):** Real-time broadcast of incident updates.
- **Backend Unit Tests (`backend/tests/test_backend.py`).**

### What You Do NOT Own
- Frontend Leaflet map visualization or React components (Track D2).
- Data ingestion scrapers or API adapters (Track A1 & Track A2).
- NLP entity extraction or incident correlation logic (Track C).

---

## ⚡ Quick Start: Local Database (Docker Compose)

Start the local PostgreSQL 16 + PostGIS database:

```bash
docker compose up -d postgres
```

* **Host:** `localhost` (Port `5432`)
* **Database:** `weather_db`
* **User / Password:** `weather_user` / `weather_password`
* **Database URL:** `postgresql://weather_user:weather_password@localhost:5432/weather_db`

---

## Data Contract Integration

Import canonical models directly from `contracts`:

```python
from contracts import EvidenceItem, Incident, WeatherReport
```

---

## File Checklist

- `docker-compose.yml`
- `backend/__init__.py`
- `backend/db/models.py`
- `backend/db/session.py`
- `backend/api/routes/__init__.py`
- `backend/api/routes/incidents.py`
- `backend/api/routes/reports.py`
- `backend/api/routes/stream.py`
- `backend/main.py`
- `backend/tests/test_backend.py`

---

## Definition of Done

1. `docker compose up -d postgres` runs cleanly.
2. SQLAlchemy models map `contracts` correctly.
3. REST endpoints (`/api/v1/incidents`, `/api/v1/reports`) return valid JSON matching Pydantic contract schemas.
4. `uv run pytest backend/tests/` passes 100%.
5. `uv run ruff check .` passes with 0 errors.
