# National Weather Intelligence Platform

## Project

We are building a prototype for the Smart India Hackathon problem:

National Weather Big Data Analytics Platform.

The system collects weather-related reports from multiple sources,
processes them using NLP/ML, correlates reports into incidents,
assigns evidence/confidence scores, and visualizes incidents on a
web dashboard.

## Core differentiator

This is NOT primarily a weather forecasting application.

The core intelligence pipeline is:

Raw Reports
→ NLP Interpretation
→ Structured Evidence
→ Spatial/Temporal/Semantic Correlation
→ Incident Formation
→ Evidence Aggregation
→ Confidence/Priority
→ Human Operator

## Current development priority

We have approximately 3 days to build a working prototype.

Therefore:

1. Prioritize a working vertical slice over architectural completeness.
2. Do not introduce unnecessary microservices.
3. Do not implement Kafka/Flink/Kubernetes unless explicitly requested.
4. Use simple local components first.
5. Every major component must be testable independently.
6. Avoid fake functionality hidden behind UI.
7. Do not claim that an event is "true" solely because an ML/LLM model says so.
8. Verification should be evidence-based and expose uncertainty.
9. Keep source provenance for every report.
10. Prefer deterministic logic where appropriate.

## Initial stack

Backend:
- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy

Data:
- PostgreSQL
- PostGIS
- pgvector

Streaming:
- Redis Streams

NLP/ML:
- spaCy
- sentence-transformers/onnx runtime loaded-as thats fast
- scikit-learn
- lightweight transformer models where appropriate

Frontend:
- Next.js
- TypeScript
- Tailwind CSS
- MapLibre/Leaflet as appropriate

Infrastructure:
- Docker Compose

## NLP pipeline

Raw text
→ normalization
→ language detection
→ disaster relevance
→ event classification
→ entity/location extraction
→ temporal extraction
→ impact extraction
→ negation detection
→ embedding generation

## Event ontology

RAIN
FLOOD
WATERLOGGING
THUNDERSTORM
LIGHTNING
HEATWAVE
FOG
DUST_STORM
STRONG_WIND
HAILSTORM
CYCLONE
OTHER

## Incident correlation

Reports should NOT be grouped using semantic similarity alone.

Correlation should consider:

- semantic similarity
- geographic proximity
- temporal proximity
- event type compatibility

## Evidence model

Every report must retain:

- source
- source_id
- timestamp
- original text
- URL if available
- extracted location
- event type
- processing confidence
- verification status

## Verification

Use:

SUPPORTED
CONTRADICTED
UNVERIFIED
PENDING_REVIEW

Do not use "TRUE" or "FAKE" as an automatic absolute judgment.

## Coding requirements

- Type hints
- Pydantic models
- modular architecture
- unit tests
- meaningful logging
- .env configuration
- no hardcoded secrets
- clean error handling

## Development rule

Before implementing a large feature:

1. Explain the implementation plan.
2. Identify files that will change.
3. Implement the smallest working version.
4. Run tests.
5. Run linting.
6. Verify the result.
7. Summarize what changed.

Do not modify unrelated files.