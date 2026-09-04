# Track B: Event Streaming & Pipeline Reliability

> **Owner:** Teammate B  
> **Branch:** `feat/streaming`  
> **Goal:** Build a robust, scalable event streaming pipeline (using Redis Streams with local fallback) to queue, process, retry, and replay `WeatherReport` events reliably.

---

## Responsibility Boundary

### What You Own
- **Stream Broker (`streaming/broker.py`):** Redis Streams connection manager with in-memory queue fallback.
- **Stream Producer (`streaming/producer.py`):** Accepts `WeatherReport` objects, serializes them to JSON, and publishes to Redis Streams (`stream:weather_reports`).
- **Stream Consumer (`streaming/consumer.py`):** Scalable Consumer Group worker with ACK handling.
- **Dead-Letter Queue (`streaming/dlq.py`):** Handles failed message processing with exponential backoff and moves unrecoverable messages to `stream:dlq:weather_reports`.
- **Replay Engine (`streaming/replay.py`):** Capability to replay past stream events from a specific point in time or message ID for reprocessing/testing.
- **Unit Tests (`streaming/tests/test_streaming.py`).**

### What You Do NOT Own
- Ingestion adapters (Track A1 & Track A2).
- NLP entity extraction or incident clustering (Track C).
- Frontend visualization (Track D).

---

## Data Contract Integration

The streaming pipeline **MUST** operate on canonical `WeatherReport` objects from `contracts`:

```python
from contracts import WeatherReport

# Producer serializes to JSON string
payload = report.model_dump_json()

# Consumer deserializes and validates
report = WeatherReport.model_validate_json(payload)
```

---

## File Checklist

- `streaming/__init__.py`
- `streaming/broker.py`
- `streaming/producer.py`
- `streaming/consumer.py`
- `streaming/dlq.py`
- `streaming/replay.py`
- `streaming/tests/test_streaming.py`

---

## Definition of Done
1. Producer publishes `WeatherReport` instances and Consumer deserializes them cleanly.
2. Failed messages route to DLQ after max retries without crashing the worker.
3. `uv run ruff check .` and `uv run ruff format --check .` pass.
4. `uv run pytest streaming/tests/` passes 100%.
