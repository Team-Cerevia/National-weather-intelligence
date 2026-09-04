# REAL-TIME STREAMING & PIPELINE ENGINE

## Teammate 2 — Implementation Specification

**Branch:** `feat/streaming-pipeline`

**Owner:** Event Streaming, Queueing, Pipeline Reliability & Replay

---

# 1. Mission

You own the **real-time movement of weather reports through the platform**.

Your job begins after the ingestion team produces a normalized:

```text
WeatherReport
```

Your job is to make sure those reports can:

```text
enter the stream
      ↓
be processed asynchronously
      ↓
survive temporary failures
      ↓
be retried when necessary
      ↓
be replayed
      ↓
reach the intelligence/NLP pipeline
```

Think of your responsibility as:

> **"How do we reliably move a continuous flow of weather events through our system?"**

You are NOT responsible for understanding what the report means.

---

# 2. Responsibility Boundary

## YOU OWN

* Message broker / stream
* Producer
* Consumer
* Consumer groups
* Message acknowledgement
* Retry mechanism
* Dead-letter queue
* Replay mechanism
* Backpressure handling
* Event metadata
* Stream monitoring metrics
* Pipeline health
* Failure recovery
* Integration with the intelligence team's processing interface

## YOU DO NOT OWN

Do NOT implement:

* Social-media ingestion
* IMD ingestion
* Weather API clients
* News scraping
* Citizen-report collection
* NLP
* Fake-news detection
* Event classification
* Semantic deduplication
* Incident clustering
* Evidence scoring
* Dashboard UI
* ML models

Teammate 1 handles source acquisition.

The intelligence/backend team handles interpretation.

You handle **movement and reliability**.

---

# 3. Target Architecture

The overall system should look like:

```text
                  EXTERNAL SOURCES
                         │
                         ▼
                ┌─────────────────┐
                │   INGESTION     │
                │   TEAMMATE 1    │
                └────────┬────────┘
                         │
                    WeatherReport
                         │
                         ▼
                ┌─────────────────┐
                │     PRODUCER    │
                └────────┬────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │    EVENT STREAM      │
              │   Redis Streams      │
              │     (MVP)            │
              └──────────┬───────────┘
                         │
                  Consumer Group
                         │
              ┌──────────▼──────────┐
              │  STREAM CONSUMER    │
              └──────────┬──────────┘
                         │
                         ▼
               Intelligence Pipeline
                         │
                         ▼
                  NLP / Verification
                         │
                         ▼
                    Database
                         │
                         ▼
                    Dashboard
```

Your component is everything between:

```text
WeatherReport
      ↓
STREAM
      ↓
Intelligence Pipeline
```

---

# 4. Technology Decision

## MVP

Use:

```text
Python
Redis Streams
redis-py
Pydantic
FastAPI integration where necessary
Docker
```

Redis Streams supports consumer groups and tracks pending messages, which gives us the reliability primitives we need without introducing a large distributed Kafka deployment during the hackathon.

---

# 5. Kafka — Optional

The SIH problem statement mentions big-data technologies, so Kafka can be considered.

However:

**DO NOT spend the first day deploying Kafka.**

Kafka is a legitimate scalable/fault-tolerant event-streaming platform with partitioned topics and consumer groups.

If the team already has Kafka running comfortably, you may implement:

```text
WeatherReport
      ↓
Kafka Producer
      ↓
weather.reports
      ↓
Consumer Group
      ↓
Intelligence
```

Otherwise:

```text
Redis Streams
```

is the MVP implementation.

The architecture should keep the broker abstraction clean enough that Kafka can be added later.

---

# 6. Repository Structure

Create:

```text
streaming/
│
├── __init__.py
│
├── config/
│   ├── __init__.py
│   └── settings.py
│
├── models/
│   ├── __init__.py
│   └── stream_event.py
│
├── broker/
│   ├── __init__.py
│   ├── base.py
│   └── redis_stream.py
│
├── producer/
│   ├── __init__.py
│   └── producer.py
│
├── consumer/
│   ├── __init__.py
│   └── consumer.py
│
├── retry/
│   ├── __init__.py
│   └── retry_manager.py
│
├── dlq/
│   ├── __init__.py
│   └── dead_letter_queue.py
│
├── replay/
│   ├── __init__.py
│   └── replay.py
│
├── monitoring/
│   ├── __init__.py
│   └── metrics.py
│
├── scripts/
│   ├── start_stream.py
│   ├── produce_test_events.py
│   └── replay_events.py
│
└── tests/
    ├── test_producer.py
    ├── test_consumer.py
    ├── test_retry.py
    ├── test_dlq.py
    ├── test_replay.py
    └── test_stream.py
```

---

# 7. Stream Event Contract

Create:

```text
streaming/models/stream_event.py
```

The event should wrap the canonical `WeatherReport`.

Conceptually:

```text
StreamEvent
```

contains:

```text
event_id
event_type
created_at
source
report
schema_version
```

Example:

```json
{
  "event_id": "evt-123",
  "event_type": "weather.report.created",
  "created_at": "2026-09-04T10:42:00Z",
  "schema_version": "1.0",
  "source": "social",
  "report": {
    "report_id": "rep-123",
    "source": "x",
    "source_type": "social_media",
    "text": "Heavy rain in Sector 62 #IMD",
    "city": "Noida",
    "state": "Uttar Pradesh"
  }
}
```

---

# 8. Stream Naming

Use clear names.

For example:

```text
weather.reports
```

Main stream:

```text
weather.reports
```

Failed events:

```text
weather.reports.dlq
```

Processed/derived events can later use:

```text
weather.events
```

or:

```text
weather.incidents
```

Do NOT create dozens of streams.

Keep the MVP simple.

---

# 9. Producer

Create:

```text
streaming/producer/producer.py
```

The producer accepts:

```text
WeatherReport
```

and publishes:

```text
StreamEvent
```

to:

```text
weather.reports
```

Example flow:

```text
Teammate 1
     │
     ▼
WeatherReport
     │
     ▼
Producer
     │
     ▼
Redis XADD
     │
     ▼
weather.reports
```

---

# 10. Producer Requirements

The producer must:

* serialize the event
* attach event metadata
* preserve report ID
* preserve source
* preserve timestamp
* generate event ID
* publish to the stream
* return/log the stream message ID

Example logging:

```text
[PRODUCER]
event_id=evt-123
report_id=rep-123
source=social
stream=weather.reports
status=published
```

---

# 11. Consumer Group

Create a consumer group:

```text
intelligence-workers
```

Conceptually:

```text
weather.reports
        │
        ▼
intelligence-workers
        │
   ┌────┴────┐
   ▼         ▼
worker-1   worker-2
```

This allows the processing layer to scale horizontally.

Redis Streams consumer groups maintain pending messages for consumers that have received but not acknowledged them.

---

# 12. Consumer

Create:

```text
streaming/consumer/consumer.py
```

The consumer should:

```text
READ
  ↓
VALIDATE
  ↓
PROCESS
  ↓
ACK
```

Never acknowledge before processing succeeds.

Bad:

```text
READ
 ↓
ACK
 ↓
PROCESS
 ↓
CRASH
```

This can lose the event from the perspective of the processing workflow.

Good:

```text
READ
 ↓
PROCESS
 ↓
SUCCESS
 ↓
ACK
```

---

# 13. Intelligence Interface

The consumer must NOT contain NLP logic.

Instead create a clean interface:

```text
WeatherReport
      ↓
process_report(report)
```

The actual implementation can initially be a stub.

Example conceptual interface:

```text
Stream Consumer
      ↓
IntelligenceProcessor
      ↓
process(report)
```

Your teammate should be able to test the streaming system even before your NLP pipeline is finished.

---

# 14. Failure Handling

This is one of your most important responsibilities.

Consider:

```text
Consumer receives report
          ↓
NLP service crashes
          ↓
What happens?
```

The report should NOT simply disappear.

Instead:

```text
weather.reports
       ↓
consumer
       ↓
processing fails
       ↓
retry
       ↓
retry
       ↓
retry
       ↓
DLQ
```

---

# 15. Retry Strategy

Implement bounded retries.

For example:

```text
Attempt 1
   ↓
failure
   ↓
wait 1 sec
   ↓
Attempt 2
   ↓
failure
   ↓
wait 2 sec
   ↓
Attempt 3
   ↓
failure
   ↓
DLQ
```

Use exponential backoff.

Suggested:

```text
1 second
2 seconds
4 seconds
```

Maximum:

```text
3 attempts
```

for MVP.

---

# 16. Dead Letter Queue

Create:

```text
streaming/dlq/dead_letter_queue.py
```

Failed events should be preserved.

Example:

```text
weather.reports
       │
       ▼
consumer
       │
   processing
       │
    FAILURE
       │
 retries exhausted
       │
       ▼
weather.reports.dlq
```

The DLQ event should preserve:

```text
original_event
failure_reason
failure_timestamp
attempt_count
consumer_id
```

---

# 17. DLQ Example

```json
{
  "event_id": "evt-123",
  "attempt_count": 3,
  "failure_reason": "NLP service unavailable",
  "failed_at": "2026-09-04T10:44:00Z",
  "original_event": {}
}
```

This is useful both operationally and for the dashboard.

---

# 18. Pending Messages

If a consumer crashes after reading a message but before acknowledging it, the message can remain pending in the Redis consumer group. Redis exposes pending-message information through its consumer-group mechanisms.

Implement a recovery mechanism.

Conceptually:

```text
consumer-1
   ↓
receives event
   ↓
CRASH
   ↓
event becomes pending
   ↓
consumer-2 detects stale event
   ↓
claims event
   ↓
processes
   ↓
ACK
```

Use Redis's pending/claim mechanisms rather than simply deleting the event.

---

# 19. Replay

Create:

```text
streaming/replay/replay.py
```

The platform should be able to replay historical events.

Example:

```text
historical events
       ↓
replay script
       ↓
weather.reports
       ↓
normal pipeline
```

This is extremely useful for the hackathon.

It means you can demonstrate:

> "We received 500 historical reports and replayed them through the real-time pipeline."

---

# 20. Replay Modes

Support at least:

```text
FAST
```

and:

```text
REAL_TIME
```

Example:

```text
FAST:
500 events → immediately

REAL_TIME:
event 1 → wait according to timestamp
event 2 → ...
```

This lets the team simulate a live weather event.

---

# 21. Event Time vs Processing Time

Every event has at least two important times:

```text
event_time
processing_time
```

Example:

```text
Citizen reports flooding:
09:55

Platform receives it:
10:01
```

Therefore:

```text
event_time      = 09:55
processing_time = 10:01
```

Do NOT overwrite the original event timestamp with ingestion time.

This distinction matters when calculating real-time windows and handling delayed/out-of-order reports.

Event-time processing is a standard stream-processing concept; systems such as Flink use event timestamps and watermarks specifically to handle delayed/out-of-order events.

---

# 22. Ordering

Do not assume:

```text
event A happened first
→
event A arrives first
```

Real systems can receive events out of order.

Example:

```text
10:00 event arrives at 10:01
10:02 event arrives at 10:02
09:58 event arrives at 10:03
```

Preserve:

```text
event_time
```

separately from:

```text
received_at
```

The intelligence layer can later use event time for incident windows.

---

# 23. Backpressure

Imagine:

```text
500 reports/sec
```

but NLP can only process:

```text
100 reports/sec
```

Do NOT spawn unlimited Python tasks.

The stream should naturally buffer incoming events while consumers process them.

Your monitoring should expose:

```text
incoming rate
processing rate
pending count
failure rate
```

---

# 24. Stream Metrics

Create:

```text
streaming/monitoring/metrics.py
```

Track at minimum:

```text
events_received
events_processed
events_failed
events_retried
events_sent_to_dlq
processing_latency
pending_messages
```

Expose them in a way the monitoring/dashboard team can consume.

If Prometheus is already in the project, expose Prometheus-compatible metrics.

---

# 25. Important Dashboard Metrics

The dashboard should eventually be able to show:

```text
┌──────────────────────────────────────┐
│ REAL-TIME PIPELINE                   │
├──────────────────────────────────────┤
│ Events/minute             127        │
│ Processed                 12,483     │
│ Failed                    31         │
│ Retried                   27         │
│ DLQ                       4          │
│ Pending                   16         │
│ Avg latency               184 ms     │
└──────────────────────────────────────┘
```

You do not need to build this UI.

You need to expose the data.

---

# 26. Health Check

Create a health mechanism such as:

```text
GET /health/stream
```

or a service-level health function.

It should verify:

```text
Redis reachable
stream exists
consumer group exists
consumer active
```

Example:

```json
{
  "status": "healthy",
  "broker": "redis",
  "stream": "weather.reports",
  "consumer_group": "intelligence-workers"
}
```

---

# 27. Docker

Create a service/container for Redis.

For local development:

```text
docker compose
```

should be able to start:

```text
redis
backend
stream consumer
```

Do not introduce Kubernetes just for this component during the first day.

---

# 28. Environment Variables

Use environment variables:

```text
REDIS_HOST
REDIS_PORT
REDIS_DB
REDIS_STREAM
REDIS_CONSUMER_GROUP
REDIS_CONSUMER_NAME
MAX_RETRIES
```

Do NOT hardcode production configuration.

---

# 29. Testing

## Producer Tests

Test:

* event serialization
* publishing
* event ID generation
* source metadata
* stream name

---

## Consumer Tests

Test:

* event consumption
* valid message
* malformed message
* processing success
* ACK after success

---

## Retry Tests

Test:

```text
failure
→ retry
→ retry
→ success
```

and:

```text
failure
→ retry
→ retry
→ retry
→ DLQ
```

---

## DLQ Tests

Verify:

* failed event preserved
* failure reason preserved
* retry count preserved
* original event preserved

---

## Replay Tests

Test:

```text
historical fixture
 ↓
replay
 ↓
stream
 ↓
consumer
```

---

# 30. Failure Simulation

Create a deliberate failure mode for the demo.

For example:

```text
FAIL_PROCESSING=true
```

Then:

```text
Event
 ↓
Consumer
 ↓
FAIL
 ↓
Retry 1
 ↓
Retry 2
 ↓
Retry 3
 ↓
DLQ
```

Then disable failure:

```text
FAIL_PROCESSING=false
```

and replay the DLQ event.

This makes the reliability architecture demonstrable rather than theoretical.

---

# 31. Main Demo

The ideal demonstration is:

```text
              SOCIAL REPORT
                    │
                    ▼
              Teammate 1
                    │
                    ▼
              WeatherReport
                    │
                    ▼
                 PRODUCER
                    │
                    ▼
              REDIS STREAM
                    │
                    ▼
             CONSUMER GROUP
                    │
                    ▼
             NLP/INTELLIGENCE
                    │
                    ▼
                INCIDENT
                    │
                    ▼
               DASHBOARD
```

Then demonstrate failure:

```text
                 EVENT
                   │
                   ▼
                STREAM
                   │
                   ▼
               CONSUMER
                   │
                FAILURE
                   │
             ┌─────┴─────┐
             ▼           ▼
          RETRY         DLQ
```

Then:

```text
DLQ
 ↓
Replay
 ↓
Consumer
 ↓
Success
```

This is a much stronger demonstration of "real-time big-data infrastructure" than simply showing a queue.

---

# 32. Scaling Demonstration

Start:

```text
worker-1
```

Then:

```text
worker-1
worker-2
worker-3
```

All consume from the same consumer group.

Show that workload can be distributed across workers.

The architecture should support horizontal scaling without changing the producer.

---

# 33. Kafka Migration Path

Keep the broker interface abstract:

```text
BaseEventBroker
```

with operations conceptually equivalent to:

```text
publish()
consume()
ack()
retry()
get_pending()
replay()
```

Then:

```text
RedisStreamBroker
KafkaBroker
```

can implement the same interface later.

Do NOT implement Kafka unless time permits.

---

# 34. Optional Apache Flink Integration

Flink should be treated as a **stretch goal**, not a P0 requirement.

Flink is designed for stateful processing over bounded and unbounded streams and supports event-time processing and late-data handling.

If the core Redis pipeline is already working, investigate whether Flink can be used for:

```text
weather.reports
       ↓
Flink
       ↓
5-minute aggregations
       ↓
regional event counts
```

For example:

```text
Delhi
10:00–10:05

rain reports = 83
flood reports = 27
heat reports = 0
```

But:

**DO NOT sacrifice the working pipeline to add Flink.**

---

# 35. What You Should NOT Build

Do NOT build:

```text
Kafka cluster
+
Flink cluster
+
Spark
+
Redis
+
RabbitMQ
```

just because the problem statement says "big data."

That is unnecessary complexity for a 3-day prototype.

A clean:

```text
Source
 ↓
Redis Stream
 ↓
Consumer Group
 ↓
Intelligence
```

pipeline is better than five partially working technologies.

---

# 36. Definition of Done

## Core

* [ ] Redis runs through Docker.
* [ ] `WeatherReport` can be published.
* [ ] `weather.reports` stream exists.
* [ ] Consumer group exists.
* [ ] Consumer can process events.
* [ ] Successful events are acknowledged.
* [ ] Failed events are retried.
* [ ] Exhausted retries go to DLQ.

## Reliability

* [ ] Pending messages can be inspected.
* [ ] Failed consumer messages can be recovered/claimed.
* [ ] Replay works.
* [ ] Event time and processing time are preserved.
* [ ] One failed event does not kill the consumer.
* [ ] Consumer can restart without losing unacknowledged work.

## Monitoring

* [ ] Processing count available.
* [ ] Failure count available.
* [ ] Retry count available.
* [ ] DLQ count available.
* [ ] Pending count available.
* [ ] Processing latency available.

## Integration

* [ ] Teammate 1 can publish `WeatherReport`.
* [ ] Intelligence team can consume `WeatherReport`.
* [ ] End-to-end pipeline works locally.

---

# 37. Priority Plan — 3 Days

## P0 — MUST FINISH

```text
Day 1

Redis
 ↓
WeatherReport producer
 ↓
weather.reports
 ↓
Consumer
 ↓
Intelligence interface
```

Then:

```text
Day 1/2

Retry
 ↓
DLQ
 ↓
ACK
```

---

## P1 — SHOULD FINISH

```text
Day 2

Replay
Pending message recovery
Metrics
Docker Compose
Failure simulation
```

---

## P2 — NICE TO HAVE

```text
Day 3

Kafka adapter
Flink experiment
advanced event-time windows
load testing
```

If P0/P1 aren't complete:

**DO NOT START P2.**

---

# 38. Handoff Contract With Teammate 1

Teammate 1 gives you:

```text
WeatherReport
```

You provide:

```text
publish(report)
```

They should NOT need to know:

* Redis commands
* consumer groups
* retry logic
* DLQ
* stream IDs

The integration should be as simple as:

```text
producer.publish(weather_report)
```

---

# 39. Handoff Contract With Intelligence Team

Your consumer gives them:

```text
WeatherReport
```

They provide:

```text
process_report(report)
```

Your streaming layer should not care whether the intelligence system uses:

```text
spaCy
transformers
LLM
rules
embeddings
ML model
```

You only care about:

```text
success
failure
```

---

# 40. The Architectural Boundary

Remember this distinction:

```text
                INGESTION
             Teammate 1
                    │
                    │ WeatherReport
                    ▼
              ┌───────────┐
              │   STREAM  │
              │ YOU OWN   │
              └─────┬─────┘
                    │
                    ▼
              ┌───────────┐
              │INTELLIGENCE│
              │    TEAM    │
              └───────────┘
```

Teammate 1 answers:

> "How do we acquire the data?"

You answer:

> "How do we reliably move the data?"

The intelligence team answers:

> "What does the data mean?"

---

# 41. Final Success Criterion

At the end of your work, we should be able to demonstrate:

> **"A weather report entering from any supported source can be published as a normalized event, processed asynchronously by scalable consumers, retried when processing fails, preserved in a dead-letter queue when retries are exhausted, recovered after consumer failure, and replayed through the same pipeline."**

That is your component.

---

# 42. One-Line Mental Model

```text
INGESTION = GET THE DATA

STREAMING = MOVE THE DATA RELIABLY

INTELLIGENCE = UNDERSTAND THE DATA

DATABASE = REMEMBER THE DATA

DASHBOARD = SHOW THE DATA
```

Stay inside the **STREAMING** boundary.
