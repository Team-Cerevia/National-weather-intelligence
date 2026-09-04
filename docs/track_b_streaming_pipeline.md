# Track B: Real-Time Event Streaming & Pipeline Engine

> **Owner:** Teammate 2  
> **Branch:** `feat/streaming`  
> **Goal:** Build a robust, scalable event streaming pipeline (using Redis Streams with local fallback) to queue, process, retry, and replay `WeatherReport` events reliably.

---

## 📌 Responsibility Boundary

### ✅ What You Own
- **Stream Producer (`streaming/producer.py`):** Accepts `WeatherReport` objects, serializes them to JSON, and pushes them to Redis Streams (e.g., `stream:weather_reports`).
- **Stream Consumer & Workers (`streaming/consumer.py`):** Consumer group worker that reads events, acknowledges processed items, and handles backpressure.
- **Dead-Letter Queue (DLQ) & Retries (`streaming/dlq.py`):** Handles failed message processing with exponential backoff and moves unrecoverable messages to `stream:dlq:weather_reports`.
- **Replay Utility (`streaming/replay.py`):** Capability to replay past stream events from a specific point in time or message ID for reprocessing/testing.

### ❌ What You Do NOT Own
- Ingestion fetching logic (Track A).
- NLP entity extraction, incident correlation, or evidence scoring.
- Frontend visualization.

---

## 🛠️ Data Contract Integration

The streaming pipeline **MUST** operate on canonical `WeatherReport` objects from `contracts.weather_report`:

```python
from contracts import WeatherReport

# Producer serializes to JSON string / dict payload
payload = report.model_dump_json()

# Consumer deserializes and validates
report = WeatherReport.model_validate_json(payload)
```

---

## 📂 Target Directory Structure

```text
streaming/
├── __init__.py
├── config.py             # Stream configuration (Redis host, port, stream names)
├── producer.py           # WeatherReportPublisher class
├── consumer.py           # WeatherReportConsumer Group worker
├── dlq.py                # Retry logic & Dead-Letter Queue handler
├── replay.py             # Replay management utility
└── tests/
    ├── test_producer.py
    ├── test_consumer.py
    └── test_dlq.py
```

---

## 🚀 Implementation Steps

### Step 1: Stream Producer (`streaming/producer.py`)
Implement `WeatherReportPublisher`:
- Connects to Redis Streams (or mock in-memory fallback for local dev).
- Validates the `WeatherReport` input.
- Publishes to stream topic `weather_reports_stream`.

```python
class WeatherReportPublisher:
    def publish(self, report: WeatherReport) -> str:
        """Serializes and publishes a WeatherReport to Redis Stream. Returns message ID."""
        pass
```

### Step 2: Consumer Group Worker (`streaming/consumer.py`)
Implement `WeatherReportConsumer`:
- Joins consumer group `intelligence_workers`.
- Reads pending/new messages using `XREADGROUP`.
- Invokes a processing handler callback.
- Acknowledges message with `XACK` upon successful execution.

### Step 3: Retries & Dead-Letter Queue (`streaming/dlq.py`)
- If processing fails, increment retry count metadata.
- Retry up to `MAX_RETRIES` (e.g., 3 times) with backoff.
- If retries are exhausted, move payload to `weather_reports_dlq`.

### Step 4: Stream Replay Utility (`streaming/replay.py`)
- Allow replaying events from timestamp $T_1$ to $T_2$ or starting from stream ID `0-0` into a target consumer group.

### Step 5: Unit & Integration Tests
Write tests in `streaming/tests/`:
```bash
uv run pytest streaming/tests/ -v
```

---

## ✅ Definition of Done
1. Producer reliably publishes `WeatherReport` instances and Consumer deserializes them cleanly.
2. Failed messages are routed to DLQ after maximum retries without crashing the consumer.
3. `uv run python -m ruff check .` passes with 0 errors.
4. `uv run python -m ruff format --check .` passes.
5. `uv run pytest` passes 100%.
