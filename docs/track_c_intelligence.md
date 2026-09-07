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

---

## Engineering Note: H3 Hash-Index Optimization in Incident Correlation

### Problem (Before Fix)

The original `correlate_reports()` loop used a **linear scan** to find a matching incident for each incoming report:

```python
# O(n × m) — n reports, m existing incidents
for report in reports:           # O(n)
    for incident in incidents:   # O(m) — scans ALL incidents every time
        # check event type
        # check temporal window
        # check spatial proximity via H3 k-ring
```

For a realistic load of **5,000 reports** and **1,000 incidents**, this is **5 million comparisons** per ingestion cycle. As the incident list grows, performance degrades quadratically.

The H3 `h3_cells` field was already stored on each incident — but it was not being used as a lookup key. The spatial structure was available; the index was not.

---

### Solution: H3 Cell Hash-Index (`Dict[str, List[Incident]]`)

A **hash map** keyed by H3 cell string is built incrementally alongside the incident list:

```python
# Data structure: O(1) average insert and lookup per H3 cell
h3_index: dict[str, list[Incident]] = {}

# When a NEW incident is created, register it in the index:
for cell in new_incident.h3_cells:
    h3_index.setdefault(cell, []).append(new_incident)
```

For each incoming report, instead of scanning all incidents, we:

1. Compute the H3 **k-ring neighborhood** of the report's cell — exactly **7 cells** at `k=1` (center + 6 neighbours). This is an O(1) H3 library call.
2. Look up **only** the incidents registered in those 7 cells from the hash map — O(1) per cell.
3. Apply temporal window and event-type checks only to this small candidate set.

```python
neighbor_cells = set(h3.grid_disk(report_cell, k=1))   # 7 cells, O(1)

candidates = []
seen_ids = set()
for cell in neighbor_cells:                              # 7 iterations
    for inc in h3_index.get(cell, []):                  # O(1) hash lookup
        if inc.incident_id not in seen_ids:
            seen_ids.add(inc.incident_id)
            candidates.append(inc)
# candidates: typically 1–3 incidents in the same geographic area
```

---

### Complexity Analysis

| | Before | After |
|---|---|---|
| **Per-report lookup** | O(m) — scan all incidents | O(k² × c) — k=7 cells, c=incidents/cell (≈1–3) |
| **Full cycle (n reports, m incidents)** | O(n × m) | O(n × k² × c) ≈ **O(n)** in practice |
| **5,000 reports × 1,000 incidents** | ~5,000,000 comparisons | ~35,000–105,000 comparisons |
| **Space overhead** | None | O(n × k) for the index — O(n) in practice |

The fallback to coordinate-distance linear scan is preserved for reports with no valid H3 cell (e.g., reports missing GPS).

---

### Why H3 and Not a Simple Bounding Box?

H3 hexagonal cells have **no edge-adjacency ambiguity** — every hexagon has exactly 6 equidistant neighbours. A `k=1` ring covers a radius of ~5–10km at resolution 7. Bounding boxes at the same scale have diagonal-corner cells that are farther apart than edge-adjacent cells, creating uneven spatial coverage. H3's `grid_disk()` gives a geometrically consistent neighbourhood every time.

This is also why we can answer the jury question: *"How do you handle reports from adjacent areas of the same weather event?"* — the k-ring naturally bridges the boundary between two hexagons even if a report falls in a neighboring cell to the incident's centroid cell.
