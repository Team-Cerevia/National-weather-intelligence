# Track C: Core Intelligence & AI Engines

> **Owner:** Lead AI Architect (YOU)  
> **Branch:** `feat/intelligence`  
> **Goal:** Build the core intelligence pipeline: NLP event extraction, spatio-temporal/semantic incident clustering, evidence provenance scoring, and incident state evolution.

---

## Responsibility Boundary

### What You Own
- **Pre-trained CPU NLP Extractor (`intelligence/nlp/extractor.py`):** Fast event categorization (RAIN, FLOOD, THUNDERSTORM, LIGHTNING, HEATWAVE, FOG, DUST_STORM, STRONG_WIND, HAILSTORM, CYCLONE), location extraction, metrics, and negation detection.
- **Incident Clustering Engine (`intelligence/clustering/incident_engine.py`):** Groups reports using H3 proximity + temporal window + vector embeddings into `Incident` objects.
- **Dynamic Merge/Split Algorithm (`intelligence/clustering/merge_split.py`):** Dynamic splitting/merging of evolving weather incidents.
- **Evidence Verification Engine (`intelligence/verification/evidence_engine.py`):** Evaluates supporting vs. contradicting evidence, source trust weighting, and builds `VerificationSummary`.
- **Evolution Engine (`intelligence/evolution/evolution_engine.py`):** Manages `IncidentState` transitions (Reported -> Verified -> Escalating -> De-escalating -> Resolved), spatial expansion, and priority score.
- **Intelligence Orchestrator (`intelligence/pipeline/orchestrator.py`):** Pipeline runner linking `WeatherReport` inputs to `Incident` outputs.

---

## Data Contract Integration

Uses `WeatherReport` as input, produces `Incident`, `EvidenceItem`, and `VerificationSummary` as output.

---

## File Checklist

- `intelligence/nlp/extractor.py`
- `intelligence/clustering/incident_engine.py`
- `intelligence/clustering/merge_split.py`
- `intelligence/verification/evidence_engine.py`
- `intelligence/evolution/evolution_engine.py`
- `intelligence/pipeline/orchestrator.py`
- `tests/test_intelligence.py`
