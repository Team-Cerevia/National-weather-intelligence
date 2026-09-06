"""National Weather Intelligence Platform - FastAPI REST API Application."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import api_router
from backend.api.routes.stream import stream_manager
import backend.db.models  # Ensure ORM models are registered on Base.metadata
from backend.db.session import init_db
from backend.scheduler import start_ingestion_scheduler
from backend.streaming import redis_subscriber_task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager managing schema verification and Redis subscriber lifecycle."""
    logger.info("Verifying database schema and PostGIS extension on startup...")
    try:
        await asyncio.to_thread(init_db)
        logger.info("Database schema verified successfully.")
    except Exception as e:
        logger.warning("Database startup check encountered: %s", e)

    # Shared stop event for all background tasks
    stop_event = asyncio.Event()
    app.state.stop_event = stop_event

    # Launch background Redis subscriber task
    subscriber_task = asyncio.create_task(redis_subscriber_task(manager=stream_manager, stop_event=stop_event))
    app.state.redis_subscriber_task = subscriber_task
    logger.info("Redis incident update subscriber task started.")

    # Launch ingestion scheduler (Open-Meteo + RSS polling)
    ingestion_tasks = await start_ingestion_scheduler(stream_manager, stop_event)
    app.state.ingestion_tasks = ingestion_tasks
    logger.info("Ingestion scheduler started with %d source tasks.", len(ingestion_tasks))

    yield

    # Clean shutdown of all background tasks
    logger.info("Stopping all background tasks...")
    stop_event.set()

    all_tasks = [subscriber_task, *(getattr(app.state, "ingestion_tasks", []))]
    for task in all_tasks:
        task.cancel()
    results = await asyncio.gather(*all_tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
            logger.debug("Background task terminated with: %s", result)
    logger.info("Shutting down backend API service.")


app = FastAPI(
    title="National Weather Big Data Analytics Platform API",
    description="REST API service for Track D1: weather report ingestion, incident queries, and evidence provenance.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware for local frontend dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST endpoints under /api/v1
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["system"], summary="Root service health check")
def root_health_check() -> dict[str, str]:
    """Root health check confirming application is running."""
    return {"status": "healthy", "service": "national-weather-intelligence"}
