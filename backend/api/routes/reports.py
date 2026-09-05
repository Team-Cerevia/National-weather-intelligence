"""REST API routes for ingesting and retrieving raw weather reports."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import ReportModel
from backend.db.session import get_db
from contracts.weather_report import WeatherReport

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=WeatherReport,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest or upsert a raw weather report",
    description="Accepts a canonical WeatherReport, validates Pydantic invariants, and upserts into PostgreSQL.",
)
def ingest_report(
    report: WeatherReport,
    db: Annotated[Session, Depends(get_db)],
) -> WeatherReport:
    """Persist or update a canonical weather report."""
    try:
        existing = db.execute(
            select(ReportModel).where(ReportModel.report_id == report.report_id)
        ).scalar_one_or_none()

        if existing is None:
            new_model = ReportModel.from_contract(report)
            db.add(new_model)
            db.commit()
            db.refresh(new_model)
            logger.info("Persisted new report: %s", report.report_id)
            return new_model.to_contract()

        # Idempotent update for existing report
        loc_val = None
        if report.latitude is not None and report.longitude is not None:
            loc_val = f"SRID=4326;POINT({report.longitude} {report.latitude})"

        existing.source = report.source
        existing.source_type = report.source_type
        existing.source_id = report.source_id
        existing.timestamp = report.timestamp
        existing.received_at = report.received_at
        existing.text = report.text
        existing.latitude = report.latitude
        existing.longitude = report.longitude
        existing.location = loc_val
        existing.h3_cell = report.h3_cell
        existing.city = report.city
        existing.district = report.district
        existing.state = report.state
        existing.country = report.country
        existing.event_category = report.event_category
        existing.url = report.url
        existing.media_urls = list(report.media_urls)
        existing.media_items = [item.model_dump() for item in report.media_items]
        existing.hashtags = list(report.hashtags)
        existing.language = report.language
        existing.raw_payload = report.raw_payload
        existing.schema_version = report.schema_version

        db.commit()
        db.refresh(existing)
        logger.info("Updated existing report: %s", report.report_id)
        return existing.to_contract()
    except Exception as e:
        db.rollback()
        logger.exception("Error ingesting report %s: %s", report.report_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist report to database",
        ) from e


@router.get(
    "/{id}",
    response_model=WeatherReport,
    summary="Get raw report by ID",
    description="Fetches a persisted WeatherReport from PostgreSQL by its unique canonical report ID.",
)
def get_report(
    id: str,
    db: Annotated[Session, Depends(get_db)],
) -> WeatherReport:
    """Retrieve an individual report by its canonical report_id."""
    stmt = select(ReportModel).where(ReportModel.report_id == id)
    report = db.execute(stmt).scalar_one_or_none()
    if report is None or report.source_type == "stub":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{id}' not found",
        )
    return report.to_contract()
