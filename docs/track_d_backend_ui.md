# Track D: Backend Persistence & Interactive GIS Dashboard

> **Owner:** Teammate C  
> **Branch:** `feat/backend-foundation` / `feat/app`  
> **Goal:** Build PostgreSQL + PostGIS database persistence, FastAPI REST & WebSocket APIs, and the interactive Leaflet GIS India Map with the Evidence Provenance Drawer.

---

## Responsibility Boundary

### What You Own
- **Database Schema (`backend/db/models.py`):** PostgreSQL + PostGIS + `pgvector` models for `Report`, `Incident`, `Evidence`, and `Timeline` (with SQLite fallback).
- **FastAPI REST API (`backend/api/routes/`):**
  - `/incidents`: List/filter incidents by date, event category, location (city/state), severity, and verification status.
  - `/incidents/{id}`: Detailed incident detail endpoint with full evidence provenance drawer data.
- **WebSocket Live Feed (`backend/api/routes/stream.py`):** Real-time broadcast of incident updates.
- **GIS Map & Admin Panel (`frontend/`):** Leaflet GIS India map with pulsing severity markers, filtering controls, and the **"Why is this real?" Evidence Provenance Drawer**.

---

## Data Contract Integration

Consumes `Incident` and `WeatherReport` contract objects from `contracts` to store in DB and render on the UI.

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
