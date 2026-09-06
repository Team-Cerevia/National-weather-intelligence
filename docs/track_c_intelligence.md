# Track C: Core Intelligence & AI Pipeline Architecture

> **Owner:** Lead AI Architect (YOU)
> **Branch:** `feat/intelligence`
> **Goal:** Build the multi-modal intelligence pipeline for weather event classification, location NER entity extraction, perceptual image hashing deduplication (pHash), EXIF metadata parsing, spatio-temporal incident clustering, and evidence verification.

---

## Isolated Scope & Non-Overlapping Boundaries

To avoid merge conflicts with other team members:
- **Track C Owned Directory:** `intelligence/` and `tests/test_intelligence.py`.
- **Do NOT touch:** `ingestion/` (Track A), `streaming/` (Track B), `backend/` (Track D1), `frontend/` (Track D2).
- **Interface Contract:** Consumes canonical `WeatherReport` Pydantic objects from `contracts/` and outputs canonical `Incident` & `EvidenceItem` Pydantic objects to `contracts/`.

---

## Intelligence Sub-Modules & ML Architecture

### 1. NLP Extractor & Classifier (`intelligence/nlp_extractor.py`)
- Weather event category classifier (`RAIN`, `FLOOD`, `WATERLOGGING`, `THUNDERSTORM`, `LIGHTNING`, `HEATWAVE`, `FOG`, `DUST_STORM`, `STRONG_WIND`, `HAILSTORM`, `CYCLONE`, `OTHER`).
- Negation detection engine for filtering false positives (e.g., "no rain in Delhi", "clear sky", "rumor of flood").
- **Location NER Extractor**: Named Entity Recognition (NER) location parser for extracting city and landmark names.
- Quantitative weather metric parser (`rainfall_mm`, `wind_speed_kmh`, `temperature_c`).

### 2. Perceptual Image Hashing & EXIF Metadata (`intelligence/vision/image_dedup.py`)
- **Perceptual Image Hashing (pHash / dHash)**: Computes image hashes to detect duplicate or reposted disaster images across social media posts.
- **EXIF Metadata Parser**: Extracts camera capture timestamp and hidden GPS latitude/longitude coordinates from image uploads.

### 3. Spatio-Temporal Incident Clustering Engine (`intelligence/incident_engine.py`)
- Groups individual reports into cohesive `Incident` objects using multi-factor correlation:
  1. Spatial proximity via H3 hexagonal cell resolution 7 (`h3_cell`).
  2. Temporal window proximity (e.g., 6-hour sliding window).
  3. Event category compatibility (e.g., `RAIN` + `FLOOD` vs. `HEATWAVE`).
  4. Text matching & distance matrix.

### 4. Evidence Verification & Confidence Engine (`intelligence/evidence_engine.py`)
- Aggregates supporting vs. contradicting report evidence.
- Calculates verification confidence score based on source trust weights (Official IMD > News RSS > Social Media > Citizen Report).
- Assigns verification status (`SUPPORTED`, `CONTRADICTED`, `UNVERIFIED`, `PENDING_REVIEW`).

### 5. Intelligence Orchestrator (`intelligence/orchestrator.py`)
- End-to-end pipeline wrapper connecting raw `WeatherReport` inputs to `Incident` outputs.

---

## File Checklist

- `intelligence/__init__.py`
- `intelligence/nlp_extractor.py`
- `intelligence/vision/__init__.py`
- `intelligence/vision/image_dedup.py`
- `intelligence/incident_engine.py`
- `intelligence/evidence_engine.py`
- `intelligence/orchestrator.py`
- `tests/test_intelligence.py`

---

## Definition of Done

1. `intelligence/` operates independently without modifying external track folders.
2. All modules process `WeatherReport` inputs and return valid `Incident` objects matching `contracts/`.
3. Unit tests pass with 100% success (`uv run pytest tests/test_intelligence.py`).
4. Linter passes cleanly (`uv run ruff check .`).
