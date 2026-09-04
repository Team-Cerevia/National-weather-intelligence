# Track A2: Weather APIs, Public Datasets & Citizen Ingestion

> **Owner:** Teammate A2  
> **Branch:** `feat/data-ingestion-api`  
> **Goal:** Build Open-Meteo API, IMD official bulletin, public dataset (CSV/JSON), and citizen report adapters that output canonical `WeatherReport` contract objects.

---

## 📌 Responsibility Boundary

### ✅ What You Own
- **Open-Meteo Live API Adapter (`ingestion/adapters/api/open_meteo_adapter.py`):** Fetch real-time temperature, precipitation, and wind speeds.
- **IMD Bulletin / Alert Adapter (`ingestion/adapters/api/imd_adapter.py`):** Parse official IMD warnings.
- **Public Dataset Loader (`ingestion/adapters/api/dataset_adapter.py`):** Load historical/public CSV & JSON weather datasets.
- **Citizen Report Parser (`ingestion/adapters/api/citizen_adapter.py`):** Parse citizen app submission payloads.
- **H3 Geospatial Helper (`ingestion/geo_utils.py`):** Coordinates-to-H3 conversion functions using resolution `7` (`DEFAULT_H3_RESOLUTION`).
- **Test Fixtures & Replay (`ingestion/fixtures/synthetic_reports.json`).**
- **Unit Tests (`ingestion/tests/test_api_data.py`).**

### ❌ What You Do NOT Own
- Social media scrapers or news RSS feeds (Track A1).
- Redis streaming broker (Track B).
- ML intelligence pipeline (Track C).

---

## 🛠️ Data Contract Output

Your adapters **MUST** return instances of `WeatherReport` imported from `contracts`:

```python
from contracts import DEFAULT_H3_RESOLUTION, WeatherReport

report = WeatherReport(
    report_id="meteo_001",
    source="open_meteo",
    source_type="weather_api",
    timestamp=timestamp_utc,
    text="Heavy Rainfall Alert: 45mm/hr observed",
    latitude=28.6139,
    longitude=77.2090,
    # h3_cell is auto-derived if latitude and longitude are supplied
    city="New Delhi",
    state="Delhi",
)
```

---

## 📂 File Checklist

- `ingestion/adapters/api/__init__.py`
- `ingestion/adapters/api/open_meteo_adapter.py`
- `ingestion/adapters/api/imd_adapter.py`
- `ingestion/adapters/api/dataset_adapter.py`
- `ingestion/adapters/api/citizen_adapter.py`
- `ingestion/geo_utils.py`
- `ingestion/fixtures/synthetic_reports.json`
- `ingestion/tests/test_api_data.py`

---

## ✅ Definition of Done
1. Adapters return valid `WeatherReport` objects with valid lat/lon and derived H3 cell res 7.
2. `uv run ruff check .` and `uv run ruff format --check .` pass.
3. `uv run pytest ingestion/tests/test_api_data.py` passes 100%.
