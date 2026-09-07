# Production Architecture & Data Flowchart (National Weather Big Data Analytics Platform)

This guide documents both the **Current Working Prototype Architecture** (Fast, Lightweight Redis Streams + PostGIS) and the **Target Enterprise Big Data Architecture** (Apache NiFi + Apache Kafka + Apache Flink + Apache Iceberg) for full national-scale deployment across India.

---

## 1. Target Enterprise Big Data Architecture Blueprint

Use this 6-Tier Distributed Big Data Architecture for your main presentation slide:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: ENTERPRISE MULTI-SOURCE INGESTION TIER                                                                        │
│ • Apache NiFi Data Routing & Transformation Engine                                                                    │
│ • Kafka Producers & Webhooks (IMD CAP XML Feeds, Social OSINT Stream API, RSS Connectors)                              │
│ • Citizen Response Mobile App & Operator Field Portal                                                                  │
└──────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────┘
                                                   │
                                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 2: HIGH-THROUGHPUT DISTRIBUTED STREAMING BROKER                                                                  │
│ • Apache Kafka Multi-Node Cluster (Partitioned Topic Logs)                                                             │
│ • Schema Registry (Avro / Protobuf Weather Report Schemas)                                                             │
│ • Kafka Dead Letter Queue (DLQ) & Fault-Tolerant Replay Buffer                                                        │
└──────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────┘
                                                   │
                                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 3: REAL-TIME STREAM ANALYTICS & AI PIPELINE TIER                                                                 │
│ • Apache Flink Stateful Stream Processing Engine                                                                      │
│ • Local ONNX Multilingual Transformer (384-d Dense Embedding Execution)                                                │
│ • spaCy NLP Engine & Proximity Negation Filter ("no rain in Delhi")                                                   │
│ • Vision Perceptual Image Hashing (dHash) & EXIF GPS Extractor                                                         │
└──────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────┘
                                                   │
                                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 4: DISTRIBUTED SPATIAL-TEMPORAL CORRELATION ENGINE                                                               │
│ • Uber H3 Resolution 7 Hexagonal Spatial Indexing                                                                      │
│ • Stateful Sliding Temporal Window Stream Join (6-Hour Window)                                                         │
│ • Dynamic Evidence Calibration Engine (IMD Authority: 0.95 | News: 0.70 | Citizen: 0.45)                             │
│ • Cross-Source Contradiction & Confidence Score Calculation                                                             │
└──────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────┘
                                                   │
                                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 5: ENTERPRISE BIG DATA STORAGE & LAKEHOUSE TIER                                                                  │
│ • PostgreSQL 16 + PostGIS Geospatial Database                                                                          │
│ • pgvector Index (384-d Cosine Similarity Search for Duplicate Detection)                                              │
│ • Apache Iceberg / Parquet Data Lakehouse (Long-Term Historical Climate Analytics)                                     │
└──────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────┘
                                                   │
                                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 6: COMMAND CENTER, DECISION SUPPORT & CLOUD EXPORT TIER                                                           │
│ • FastAPI Async REST APIs & Starlette Live WebSockets Stream                                                          │
│ • Next.js 15 Interactive GIS Command Dashboard (MapLibre GL + H3 Vector Layers)                                      │
│ • Emergency Response Operator Copilot Assistant (AI Decision Support)                                                 │
│ • Automated Government SITREP Exporter (CSV & AWS S3 Bucket Storage)                                                   │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Jury Pitch Script: Prototype vs. Enterprise Scaling

When presenting to the **IMD / MoES Jury**, use this exact dual-narrative pitch:

1. **Working Prototype (Delivered Today)**:
   > *"For our 3-day hackathon prototype, we built a fully functional, lightweight vertical slice using Python 3.12, FastAPI, Redis Streams, PostgreSQL + PostGIS + pgvector, and Next.js. Every line of code is live, tested with 62 unit tests, and deployed on AWS EC2."*

2. **Enterprise Production Scaling (Target Blueprint)**:
   > *"For full national deployment across India's 700+ districts, our architecture seamlessly swaps Redis Streams and local state with **Apache Kafka**, **Apache Flink**, and an **Apache Iceberg Data Lakehouse**—ensuring sub-second processing for millions of concurrent weather posts during major cyclones."*
