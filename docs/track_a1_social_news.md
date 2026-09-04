# Track A1: Social Media, Hashtags & News Ingestion

> **Owner:** Teammate A1  
> **Branch:** `feat/data-ingestion-social`  
> **Goal:** Build social media (#IMD, weather hashtags, media URLs) and weather news RSS feed adapters that output canonical `WeatherReport` contract objects.

---

## 📌 Responsibility Boundary

### ✅ What You Own
- **Social Media Scraper / Adapter (`ingestion/adapters/social/social_adapter.py`):** Extract weather posts, hashtags (`#IMD`, `#IndiaWeather`, `#Monsoon`), media URLs (photos/videos), and location text.
- **News RSS Feed Adapter (`ingestion/adapters/social/news_rss_adapter.py`):** Fetch live weather articles and news alerts.
- **Hashtag & Media Extractor (`ingestion/adapters/social/extractors.py`):** Parse hashtags, media links, and language codes.
- **Test Fixtures (`ingestion/fixtures/social_posts.json`):** Mock social posts and news feeds for testing.
- **Unit Tests (`ingestion/tests/test_social.py`):** Tests for social and news parsing.

### ❌ What You Do NOT Own
- Open-Meteo API / Citizen REST endpoint (Track A2).
- Redis event streaming (Track B).
- Incident clustering or NLP evidence processing (Track C).

---

## 🛠️ Data Contract Output

Your adapters **MUST** return instances of `WeatherReport` imported from `contracts`:

```python
from contracts import WeatherReport

report = WeatherReport(
    report_id="soc_001",
    source="x_social",
    source_type="social_media",
    source_id="tweet_18923719",
    timestamp=timestamp_utc,
    text="Heavy waterlogging in Noida Sector 62 #NoidaRain #IMD",
    hashtags=["#NoidaRain", "#IMD"],
    media_urls=["https://example.com/photos/flood1.jpg"],
    city="Noida",
    state="Uttar Pradesh",
)
```

---

## 📂 File Checklist

- `ingestion/adapters/social/__init__.py`
- `ingestion/adapters/social/social_adapter.py`
- `ingestion/adapters/social/news_rss_adapter.py`
- `ingestion/adapters/social/extractors.py`
- `ingestion/fixtures/social_posts.json`
- `ingestion/tests/test_social.py`

---

## ✅ Definition of Done
1. Adapters return valid `WeatherReport` objects.
2. `uv run ruff check .` and `uv run ruff format --check .` pass.
3. `uv run pytest ingestion/tests/test_social.py` passes 100%.
