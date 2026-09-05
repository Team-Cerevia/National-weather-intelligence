# Track D: Backend Persistence & Interactive GIS Dashboard

> **Goal:** Build PostgreSQL + PostGIS database persistence, FastAPI REST & WebSocket APIs, and the interactive Leaflet GIS India Map with the Evidence Provenance Drawer.

---

## Decoupled Sub-Track Division

To allow pure backend work without UI dependencies, Track D is split into two independent sub-tracks:

### ⚙️ **Track D1: Backend Foundation & REST API (Assigned to Teammate C - Python Backend)**
* **Branch:** `feat/backend-foundation`
* **What You Own:**
  - **Database Schema (`backend/db/models.py`, `backend/db/session.py`):** PostgreSQL + PostGIS models for `Report`, `Incident`, `Evidence`, and `Timeline` (with SQLite fallback).
  - **FastAPI REST API (`backend/api/routes/`):**
    - `GET /api/v1/incidents`: List/filter incidents by date, event category, location, severity, and verification status.
    - `GET /api/v1/incidents/{id}`: Detailed incident endpoint with full evidence provenance data.
    - `POST /api/v1/incidents`: Endpoint for Track C Intelligence engine to save processed incidents.
    - `POST /api/v1/reports`: Endpoint to ingest raw weather reports.
  - **WebSocket Live Feed (`backend/api/routes/stream.py`):** Real-time broadcast of incident updates.
  - **Backend Unit Tests (`backend/tests/test_backend.py`).**

### 🎨 **Track D2: Frontend GIS Map & Evidence Drawer (Frontend/UI - Stretch Goal / Teammate D)**
* **Branch:** `feat/frontend-dashboard`
* **What You Own:**
  - **GIS Map & Admin Panel (`frontend/src/components/Map.tsx`):** Leaflet GIS India map with color-coded pulsing severity markers.
  - **Evidence Provenance Drawer (`frontend/src/components/EvidenceDrawer.tsx`):** Slide-over panel showing verification status and supporting/contradicting evidence.

---

## Local Database Setup (Docker Compose)

To spin up a local PostgreSQL + PostGIS database instance instantly:

```bash
docker compose up -d postgres
```

* **Host**: `localhost` (Port `5432`)
* **Database**: `weather_db`
* **User / Password**: `weather_user` / `weather_password`
* **Database URL**: `postgresql://weather_user:weather_password@localhost:5432/weather_db`

*(SQLite fallback is also available if Docker is temporarily unavailable).*

## Data Contract & Ingestion Integration

* **Data Contracts (`contracts/`)**: Consumes `Incident` and `WeatherReport` Pydantic objects from `contracts/` to store in DB models and render on the UI.
* **Live Ingestion Adapters (Completed in `main`)**: Real-time Open-Meteo (`OpenMeteoAdapter`) and official IMD (`ImdAdapter`) report generators are available in [`ingestion/adapters/api/`](file:///c:/Users/harve/OneDrive/docs/GitHub/National-weather-intelligence/ingestion/adapters/api/) to trigger data ingestion into the database.

---

## File Checklist

- `backend/db/models.py`
- `backend/db/session.py`
- `backend/api/routes/incidents.py`
- `backend/api/routes/reports.py`
- `backend/api/routes/stream.py`
- `frontend/src/components/Map.tsx`
- `frontend/src/components/EvidenceDrawer.tsx`
- `backend/tests/test_backend.py`

---

## Definition of Done
1. Database migrations run cleanly.
2. REST endpoints return valid JSON matching contract schemas.
3. Leaflet map renders incidents and opens the Evidence Provenance Drawer on click.
4. `uv run ruff check .` passes with 0 errors.
