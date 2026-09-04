# Track A: Data Ingestion & Source Normalization Engine

> **Owner:** Teammate 1  
> **Branch:** `feat/data-ingestion`  
> **Goal:** Ingest weather data from heterogeneous sources (IMD, Open-Meteo, Social Media, News, Citizen reports) and normalize them into the canonical `WeatherReport` contract.

---

## 📌 Responsibility Boundary

### ✅ What You Own
- **Source Adapters (`ingestion/sources/`):** Fetching/parsing data from IMD, Open-Meteo/Weather APIs, News feeds, Social Media posts, and Citizen reports.
- **Normalization (`ingestion/normalization/`):** Cleaning text, normalizing timestamps to timezone-aware UTC, and mapping location coordinates/names.
- **Fixtures (`ingestion/fixtures/`):** Sample mock data payloads for offline development and testing.
- **Adapter Unit Tests (`ingestion/tests/` or `tests/`):** Ensuring every adapter returns valid `WeatherReport` objects.

### ❌ What You Do NOT Own
- Event streaming / Redis queues (Track B).
- Incident clustering, evidence scoring, or NLP intelligence pipelines.
- Frontend UI components.

---

## 🛠️ Data Contract Requirements

Every source adapter **MUST** return instances of `WeatherReport` imported from `contracts.weather_report`:

```python
from contracts import DEFAULT_H3_RESOLUTION, WeatherReport
```

### Mandatory Rules
1. **Timezones:** `timestamp` and `received_at` MUST be timezone-aware (normalized to UTC).
2. **Coordinates & H3:** Latitude and longitude must be provided together. `h3_cell` will be auto-derived at resolution `7` (`DEFAULT_H3_RESOLUTION`).
3. **Provenance:** Retain original `source`, `source_type`, `source_id`, `text`, and optional `raw_payload`.
4. **Extra Fields:** Strict schema (`extra="forbid"`). Do NOT add arbitrary unknown fields.

---

## 📂 Target Directory Structure

```text
ingestion/
├── __init__.py
├── sources/
│   ├── __init__.py
│   ├── base.py              # BaseSourceAdapter abstract class
│   ├── imd.py               # Official IMD weather warnings/bulletins adapter
│   ├── weather_api.py       # Open-Meteo / Weather API adapter
│   ├── social.py            # Social media / X post adapter
│   ├── news.py              # Weather news article adapter
│   └── citizen.py           # Citizen crowd-sourced report adapter
├── normalization/
│   ├── __init__.py
│   ├── text_normalizer.py   # Text cleaning & unicode normalization
│   └── location_normalizer.py # Location string & coordinate mapping
├── fixtures/
│   ├── imd_bulletins.json
│   ├── weather_api_sample.json
│   └── social_posts.json
└── tests/
    ├── test_imd_adapter.py
    ├── test_weather_api_adapter.py
    └── test_normalization.py
```

---

## 🚀 Implementation Steps

### Step 1: Base Adapter (`ingestion/sources/base.py`)
Define an abstract interface that all adapters inherit from:
```python
from abc import ABC, abstractmethod
from contracts import WeatherReport


class BaseSourceAdapter(ABC):
    @abstractmethod
    def fetch_reports(self) -> list[WeatherReport]:
        """Fetch raw data from source and return normalized WeatherReport items."""
        pass
```

### Step 2: Source Adapters
Implement adapters for each required source in `ingestion/sources/`:
- `imd.py`: Parses official IMD alerts/bulletins.
- `weather_api.py`: Fetches real-time structured data from Open-Meteo or Weather API.
- `social.py` / `citizen.py`: Parses social/citizen text posts into canonical reports.

### Step 3: Normalization Helpers
- Clean whitespace, remove special noise characters in `text_normalizer.py`.
- Validate coordinates in `location_normalizer.py`.

### Step 4: Unit Testing
Write unit tests for each adapter in `ingestion/tests/`:
```bash
uv run pytest ingestion/tests/ -v
```

---

## ✅ Definition of Done
1. All adapters inherit from `BaseSourceAdapter` and output valid `WeatherReport` models.
2. `uv run python -m ruff check .` passes with 0 errors.
3. `uv run python -m ruff format --check .` passes.
4. `uv run pytest` passes 100%.
