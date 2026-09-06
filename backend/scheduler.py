"""Background ingestion scheduler for the National Weather Intelligence Platform.

Polls live data sources on a configurable interval:
  - Open-Meteo Forecast API (free, no key) — real weather for 20 major Indian cities
  - Indian weather news RSS feeds — BBC Hindi, NDTV, The Hindu, India Meteorological RSS

Pipeline per cycle:
  raw reports → NLP orchestrator → DB upsert → Redis publish → WebSocket broadcast
"""

import asyncio
import logging
import os
from typing import Any

from backend.api.routes.stream import ConnectionManager
from backend.db.models import IncidentModel, ReportModel
from backend.db.session import SessionLocal
from backend.streaming import publish_incident_update
from contracts.incident import Incident
from contracts.weather_report import WeatherReport
from ingestion.adapters.api.open_meteo_adapter import OpenMeteoAdapter
from ingestion.adapters.social.news_rss_adapter import NewsRssAdapter
from nlp.orchestrator import IntelligenceOrchestrator
from streaming.dlq import DeadLetterQueue

logger = logging.getLogger("backend.scheduler")
_dlq = DeadLetterQueue()

# ---------------------------------------------------------------------------
# Indian cities: (name, state, latitude, longitude)
# Covers all major metro areas + disaster-prone regions
# ---------------------------------------------------------------------------
INDIAN_CITIES: list[tuple[str, str, float, float]] = [
    ("Mumbai", "Maharashtra", 19.0760, 72.8777),
    ("Delhi", "Delhi", 28.7041, 77.1025),
    ("Bengaluru", "Karnataka", 12.9716, 77.5946),
    ("Chennai", "Tamil Nadu", 13.0827, 80.2707),
    ("Kolkata", "West Bengal", 22.5726, 88.3639),
    ("Hyderabad", "Telangana", 17.3850, 78.4867),
    ("Ahmedabad", "Gujarat", 23.0225, 72.5714),
    ("Pune", "Maharashtra", 18.5204, 73.8567),
    ("Jaipur", "Rajasthan", 26.9124, 75.7873),
    ("Lucknow", "Uttar Pradesh", 26.8467, 80.9462),
    ("Patna", "Bihar", 25.5941, 85.1376),
    ("Bhubaneswar", "Odisha", 20.2961, 85.8245),
    ("Guwahati", "Assam", 26.1445, 91.7362),
    ("Thiruvananthapuram", "Kerala", 8.5241, 76.9366),
    ("Chandigarh", "Punjab", 30.7333, 76.7794),
    ("Bhopal", "Madhya Pradesh", 23.2599, 77.4126),
    ("Nagpur", "Maharashtra", 21.1458, 79.0882),
    ("Visakhapatnam", "Andhra Pradesh", 17.6868, 83.2185),
    ("Srinagar", "Jammu & Kashmir", 34.0837, 74.7973),
    ("Port Blair", "Andaman & Nicobar", 11.6234, 92.7265),
]

# ---------------------------------------------------------------------------
# Public Indian weather / disaster news RSS feeds (no auth required)
# ---------------------------------------------------------------------------
RSS_FEEDS: list[str] = [
    # NDTV India weather
    "https://feeds.feedburner.com/ndtvnews-top-stories",
    # The Hindu - national / science (covers weather alerts)
    "https://www.thehindu.com/sci-tech/energy-and-environment/feeder/default.rss",
    # Times of India - weather
    "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
    # Hindustan Times - weather
    "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    # IMD Press Releases & Severe Weather CAP Feed (Official)
    "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml",
    # India Today weather section
    "https://www.indiatoday.in/rss/1206578",
]

# Polling intervals (seconds)
OPEN_METEO_INTERVAL: int = int(os.getenv("OPEN_METEO_POLL_INTERVAL", "300"))  # 5 min
RSS_INTERVAL: int = int(os.getenv("RSS_POLL_INTERVAL", "180"))  # 3 min


def _upsert_report(report: WeatherReport) -> None:
    """Persist a WeatherReport to the database (idempotent by primary key). Routes errors to DLQ."""
    db = SessionLocal()
    try:
        from sqlalchemy import select

        existing = db.execute(select(ReportModel.report_id).where(ReportModel.report_id == report.report_id)).scalar()
        if not existing:
            db.add(ReportModel.from_contract(report))
            db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Failed to upsert report %s: %s", report.report_id, exc)
        try:
            _dlq.send_to_dlq(report.model_dump(mode="json"), f"Scheduler upsert failure: {exc}")
        except Exception as dlq_exc:
            logger.debug("DLQ dispatch note: %s", dlq_exc)
    finally:
        db.close()


def _upsert_incident(incident: Incident) -> Incident:
    """Idempotently persist or update an incident; return the persisted version."""
    from sqlalchemy import select

    db = SessionLocal()
    try:
        # Ensure all referenced reports exist as stubs
        for rep_id in incident.report_ids:
            if not db.execute(select(ReportModel.report_id).where(ReportModel.report_id == rep_id)).scalar():
                from datetime import datetime, timezone

                stub = ReportModel(
                    report_id=rep_id,
                    source="system",
                    source_type="stub",
                    timestamp=datetime.now(timezone.utc),
                    text=f"Report {rep_id} pending payload",
                )
                db.add(stub)
                db.flush()

        existing = db.execute(
            select(IncidentModel).where(IncidentModel.incident_id == incident.incident_id)
        ).scalar_one_or_none()

        if existing is None:
            db.add(IncidentModel.from_contract(incident))
            db.commit()
            logger.info("Created incident: %s [%s]", incident.incident_id, incident.event_category)
        else:
            # Update key mutable fields only — do not overwrite user edits to state/severity
            existing.last_updated_at = incident.last_updated_at
            existing.report_ids = list(set(existing.report_ids or []) | set(incident.report_ids))
            for tl in incident.timeline:
                from backend.db.models import IncidentTimelineModel

                key = (tl.timestamp, tl.event_type, tl.description, tl.report_id)
                existing_keys = {(t.timestamp, t.event_type, t.description, t.report_id) for t in existing.timeline}
                if key not in existing_keys:
                    existing.timeline.append(IncidentTimelineModel.from_contract(tl, incident_id=incident.incident_id))
            db.commit()
            db.refresh(existing)
            incident = existing.to_contract()
            logger.debug("Updated incident: %s", incident.incident_id)

        return incident
    except Exception as exc:
        db.rollback()
        logger.error("Failed to upsert incident %s: %s", incident.incident_id, exc)
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Core pipeline runner
# ---------------------------------------------------------------------------

_orchestrator: IntelligenceOrchestrator | None = None


def _get_orchestrator() -> IntelligenceOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = IntelligenceOrchestrator(time_window_hours=6.0, spatial_k_ring=1)
    return _orchestrator


async def _run_pipeline(
    reports: list[WeatherReport],
    stream_manager: ConnectionManager,
    source_label: str,
) -> None:
    """Run the NLP pipeline on a batch of reports and publish results."""
    if not reports:
        return

    logger.info("[%s] Processing %d reports through NLP pipeline…", source_label, len(reports))

    loop = asyncio.get_running_loop()
    orchestrator = _get_orchestrator()

    # NLP is CPU-bound — run in thread pool to avoid blocking the event loop
    incidents: list[Incident] = await loop.run_in_executor(None, orchestrator.process_reports, reports)

    logger.info("[%s] Pipeline produced %d incidents", source_label, len(incidents))

    for report in reports:
        await loop.run_in_executor(None, _upsert_report, report)

    for incident in incidents:
        try:
            persisted = await loop.run_in_executor(None, _upsert_incident, incident)
            # Publish to Redis + WebSocket
            try:
                publish_incident_update(persisted)
            except Exception as redis_err:
                logger.warning("Redis publish failed for %s: %s", persisted.incident_id, redis_err)
            await stream_manager.broadcast(
                {
                    "event": "incident_update",
                    "incident": persisted.model_dump(mode="json"),
                }
            )
        except Exception as exc:
            logger.error("Failed to persist/publish incident %s: %s", incident.incident_id, exc)


# ---------------------------------------------------------------------------
# Open-Meteo polling task
# ---------------------------------------------------------------------------


async def open_meteo_task(stream_manager: ConnectionManager, stop_event: asyncio.Event) -> None:
    """Polls Open-Meteo for all configured Indian cities on OPEN_METEO_INTERVAL schedule."""
    adapter = OpenMeteoAdapter()
    logger.info(
        "Open-Meteo ingestion task started — polling %d cities every %ds",
        len(INDIAN_CITIES),
        OPEN_METEO_INTERVAL,
    )
    while not stop_event.is_set():
        reports: list[WeatherReport] = []
        for city, state, lat, lon in INDIAN_CITIES:
            try:
                loop = asyncio.get_running_loop()
                city_reports: list[WeatherReport] = await loop.run_in_executor(None, adapter.fetch_and_parse, lat, lon)
                # Annotate with city/state metadata (Open-Meteo doesn't return place names)
                for r in city_reports:
                    r.city = city
                    r.state = state
                reports.extend(city_reports)
            except Exception as exc:
                logger.warning("Open-Meteo fetch failed for %s: %s", city, exc)

        await _run_pipeline(reports, stream_manager, "open_meteo")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=OPEN_METEO_INTERVAL)
        except asyncio.TimeoutError:
            pass  # Normal — loop again


# ---------------------------------------------------------------------------
# RSS polling task
# ---------------------------------------------------------------------------


async def rss_task(stream_manager: ConnectionManager, stop_event: asyncio.Event) -> None:
    """Polls configured Indian news RSS feeds on RSS_INTERVAL schedule."""
    adapter = NewsRssAdapter()
    logger.info(
        "RSS ingestion task started — polling %d feeds every %ds",
        len(RSS_FEEDS),
        RSS_INTERVAL,
    )
    while not stop_event.is_set():
        reports: list[WeatherReport] = []
        for feed_url in RSS_FEEDS:
            try:
                loop = asyncio.get_running_loop()
                feed_reports: list[WeatherReport] = await loop.run_in_executor(
                    None,
                    lambda u=feed_url: adapter.fetch_and_parse(url=u, filter_weather_relevance=True),
                )
                reports.extend(feed_reports)
            except Exception as exc:
                logger.warning("RSS fetch failed for %s: %s", feed_url, exc)

        await _run_pipeline(reports, stream_manager, "rss")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=RSS_INTERVAL)
        except asyncio.TimeoutError:
            pass  # Normal — loop again


# ---------------------------------------------------------------------------
# Social Media OSINT polling task
# ---------------------------------------------------------------------------


async def social_osint_task(stream_manager: ConnectionManager, stop_event: asyncio.Event) -> None:
    """Polls public social media OSINT feeds (#indiaweather, #monsoon, #IMD) on RSS_INTERVAL schedule."""
    from ingestion.adapters.social.social_adapter import SocialAdapter

    adapter = SocialAdapter()
    logger.info("Social Media OSINT task started — polling live weather hashtags every %ds", RSS_INTERVAL)
    while not stop_event.is_set():
        try:
            loop = asyncio.get_running_loop()
            hashtags = ["indiaweather", "monsoon", "imd", "weatheralert"]
            social_reports: list[WeatherReport] = await loop.run_in_executor(
                None,
                lambda: adapter.fetch_and_parse(hashtags=hashtags),
            )
            await _run_pipeline(social_reports, stream_manager, "social_media")
        except Exception as exc:
            logger.warning("Social OSINT fetch failed: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=RSS_INTERVAL)
        except asyncio.TimeoutError:
            pass


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def start_ingestion_scheduler(
    stream_manager: ConnectionManager,
    stop_event: asyncio.Event,
) -> list[asyncio.Task[Any]]:
    """Launches all ingestion polling tasks and returns task handles for cancellation."""
    tasks: list[asyncio.Task[Any]] = [
        asyncio.create_task(open_meteo_task(stream_manager, stop_event), name="open_meteo_ingestion"),
        asyncio.create_task(rss_task(stream_manager, stop_event), name="rss_ingestion"),
        asyncio.create_task(social_osint_task(stream_manager, stop_event), name="social_osint_ingestion"),
    ]
    logger.info("Ingestion scheduler started with %d source tasks.", len(tasks))
    return tasks
