"""REST API routes for querying, retrieving, and persisting incidents with evidence provenance."""

import logging
from datetime import date as dt_date
from datetime import datetime, time, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.db.models import EvidenceItemModel, IncidentModel, IncidentTimelineModel, ReportModel
from backend.db.session import get_db
from backend.streaming import publish_incident_update
from contracts.evidence import EvidenceRelationship, VerificationStatus
from contracts.incident import Incident, IncidentSeverity, IncidentState, IncidentTimeline

logger = logging.getLogger(__name__)

router = APIRouter()


def _ensure_report_stub(
    db: Session,
    report_id: str | None,
    source: str = "system",
    ts: datetime | None = None,
) -> None:
    """Ensure a placeholder report exists so PostgreSQL foreign key constraints are preserved.

    When the real WeatherReport is ingested later, its upsert logic will overwrite this stub.
    Stub records always have source_type='stub' so GET /reports/{id} returns 404 until genuine data arrives.
    """
    if not report_id:
        return
    existing = db.execute(select(ReportModel.report_id).where(ReportModel.report_id == report_id)).scalar()
    if not existing:
        stub = ReportModel(
            report_id=report_id,
            source=source,
            source_type="stub",
            timestamp=ts or datetime.now(timezone.utc),
            text=f"Report {report_id} pending detailed payload",
        )
        db.add(stub)
        db.flush()


@router.get(
    "",
    response_model=list[Incident],
    summary="List and filter weather incidents",
    description=(
        "Returns clustered weather incidents from PostgreSQL with optional filtering by date range, "
        "event category, severity, verification status, location hierarchy, and PostGIS spatial radius."
    ),
)
def list_incidents(
    db: Annotated[Session, Depends(get_db)],
    start_date: Annotated[
        datetime | None,
        Query(description="Filter incidents first reported on or after this timestamp (timezone-aware UTC)"),
    ] = None,
    end_date: Annotated[
        datetime | None,
        Query(description="Filter incidents first reported on or before this timestamp (timezone-aware UTC)"),
    ] = None,
    date: Annotated[
        dt_date | None,
        Query(description="Filter incidents occurring on this specific calendar date (UTC)"),
    ] = None,
    event_category: Annotated[
        str | None,
        Query(description="Exact canonical weather category (e.g., RAIN, FLOOD, THUNDERSTORM)"),
    ] = None,
    severity: Annotated[
        IncidentSeverity | None,
        Query(description="Filter by incident severity level"),
    ] = None,
    verification_status: Annotated[
        VerificationStatus | None,
        Query(description="Filter by evidence verification status"),
    ] = None,
    city: Annotated[
        str | None,
        Query(description="Case-insensitive substring match for city name"),
    ] = None,
    state: Annotated[
        str | None,
        Query(description="Case-insensitive substring match for state name"),
    ] = None,
    latitude: Annotated[
        float | None,
        Query(ge=-90.0, le=90.0, description="Centroid latitude for spatial radius query"),
    ] = None,
    longitude: Annotated[
        float | None,
        Query(ge=-180.0, le=180.0, description="Centroid longitude for spatial radius query"),
    ] = None,
    radius_km: Annotated[
        float,
        Query(gt=0.0, le=1000.0, description="Search radius in kilometers around coordinates"),
    ] = 10.0,
    limit: Annotated[
        int,
        Query(ge=1, le=500, description="Maximum number of incidents to return"),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of records to skip for pagination"),
    ] = 0,
) -> list[Incident]:
    """Query and filter weather incidents using PostgreSQL and PostGIS."""
    stmt = select(IncidentModel)

    # PostGIS Spatial radius filter
    if latitude is not None and longitude is not None:
        stmt = stmt.where(
            text(
                "ST_DWithin(incidents.location::geography, "
                "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, "
                ":radius_m)"
            ).bindparams(lon=longitude, lat=latitude, radius_m=radius_km * 1000.0)
        )
    elif (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both latitude and longitude must be provided together for location filtering.",
        )

    # Date / Time bounds
    if date is not None:
        day_start = datetime.combine(date, time.min, tzinfo=timezone.utc)
        day_end = datetime.combine(date, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(
            IncidentModel.first_reported_at >= day_start,
            IncidentModel.first_reported_at <= day_end,
        )
    if start_date is not None:
        stmt = stmt.where(IncidentModel.first_reported_at >= start_date)
    if end_date is not None:
        stmt = stmt.where(IncidentModel.first_reported_at <= end_date)

    # Event category filter
    if event_category:
        stmt = stmt.where(IncidentModel.event_category == event_category.upper().strip())

    # Severity filter
    if severity is not None:
        stmt = stmt.where(IncidentModel.severity == severity.value)

    # Verification status filter
    if verification_status is not None:
        stmt = stmt.where(IncidentModel.verification_status == verification_status.value)

    # Location hierarchy filters
    if city:
        stmt = stmt.where(IncidentModel.city.ilike(f"%{city.strip()}%"))
    if state:
        stmt = stmt.where(IncidentModel.state_name.ilike(f"%{state.strip()}%"))

    # Order by newest first, then paginate
    stmt = stmt.order_by(IncidentModel.first_reported_at.desc()).offset(offset).limit(limit)

    results = db.execute(stmt).scalars().all()
    return [incident.to_contract() for incident in results]


@router.get(
    "/{id}",
    response_model=Incident,
    summary="Get incident details by ID",
    description="Fetches an incident with full evidence provenance and timeline evolution history.",
)
def get_incident(
    id: str,
    db: Annotated[Session, Depends(get_db)],
) -> Incident:
    """Retrieve an individual incident by canonical incident_id."""
    stmt = select(IncidentModel).where(IncidentModel.incident_id == id)
    incident = db.execute(stmt).scalar_one_or_none()
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{id}' not found",
        )
    return incident.to_contract()


@router.post(
    "",
    response_model=Incident,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update an incident",
    description=(
        "Idempotently persists an incident generated by the intelligence layer. "
        "Creates a new record or updates existing scalar attributes, evidence items, and timeline entries."
    ),
)
def upsert_incident(
    incident: Incident,
    db: Annotated[Session, Depends(get_db)],
) -> Incident:
    """Persist or update an incident with its complete evidence provenance and timeline."""
    try:
        # 1. Ensure any referenced reports exist to preserve Foreign Key integrity
        for rep_id in incident.report_ids:
            _ensure_report_stub(db, rep_id)

        if incident.verification_summary:
            for ev in incident.verification_summary.evidence_items:
                _ensure_report_stub(
                    db,
                    ev.report_id,
                    source=ev.source,
                    ts=ev.timestamp,
                )

        for t in incident.timeline:
            if t.report_id:
                _ensure_report_stub(db, t.report_id, ts=t.timestamp)

        # 2. Check for existing incident
        existing = db.execute(
            select(IncidentModel).where(IncidentModel.incident_id == incident.incident_id)
        ).scalar_one_or_none()

        if existing is None:
            new_incident = IncidentModel.from_contract(incident)
            db.add(new_incident)
            db.commit()
            db.refresh(new_incident)
            logger.info("Created new incident: %s", incident.incident_id)
            result = new_incident.to_contract()
            try:
                publish_incident_update(result)
            except Exception as redis_err:
                logger.error("Failed to publish incident %s update to Redis: %s", incident.incident_id, redis_err)
            return result

        # 3. Update existing incident scalar attributes
        loc_val = None
        if incident.latitude is not None and incident.longitude is not None:
            loc_val = f"SRID=4326;POINT({incident.longitude} {incident.latitude})"

        existing.title = incident.title
        existing.event_category = incident.event_category
        existing.state = incident.state.value if isinstance(incident.state, IncidentState) else str(incident.state)
        existing.severity = (
            incident.severity.value if isinstance(incident.severity, IncidentSeverity) else str(incident.severity)
        )
        existing.priority_score = incident.priority_score
        existing.latitude = incident.latitude
        existing.longitude = incident.longitude
        existing.location = loc_val
        existing.h3_cells = list(incident.h3_cells)
        existing.city = incident.city
        existing.district = incident.district
        existing.state_name = incident.state_name
        existing.country = incident.country
        existing.first_reported_at = incident.first_reported_at
        existing.last_updated_at = incident.last_updated_at
        existing.report_ids = list(incident.report_ids)

        # 4. Synchronize verification summary & evidence items
        if incident.verification_summary is not None:
            summary = incident.verification_summary
            existing.verification_status = (
                summary.verification_status.value
                if isinstance(summary.verification_status, VerificationStatus)
                else str(summary.verification_status)
            )
            existing.overall_confidence = summary.overall_confidence
            existing.supporting_count = summary.supporting_count
            existing.contradicting_count = summary.contradicting_count
            existing.supporting_sources = list(summary.supporting_sources)
            existing.contradicting_sources = list(summary.contradicting_sources)
            existing.verification_explanation = summary.explanation
            existing.verification_updated_at = summary.updated_at

            # Map existing evidence items by evidence_id
            existing_ev_map = {ev.evidence_id: ev for ev in existing.evidence_items}
            new_ev_map = {ev.evidence_id: ev for ev in summary.evidence_items}

            # Delete orphaned evidence items
            for ev_id, ev_model in list(existing_ev_map.items()):
                if ev_id not in new_ev_map:
                    existing.evidence_items.remove(ev_model)

            # Update existing or add new evidence items
            for ev_id, ev_contract in new_ev_map.items():
                rel_str = (
                    ev_contract.relationship.value
                    if isinstance(ev_contract.relationship, EvidenceRelationship)
                    else str(ev_contract.relationship)
                )
                if ev_id in existing_ev_map:
                    ev_model = existing_ev_map[ev_id]
                    ev_model.report_id = ev_contract.report_id
                    ev_model.source = ev_contract.source
                    ev_model.source_type = ev_contract.source_type
                    ev_model.relationship = rel_str
                    ev_model.confidence_score = ev_contract.confidence_score
                    ev_model.source_reliability_weight = ev_contract.source_reliability_weight
                    ev_model.reasoning = ev_contract.reasoning
                    ev_model.extracted_event = ev_contract.extracted_event
                    ev_model.extracted_location = ev_contract.extracted_location
                    ev_model.media_proof_urls = list(ev_contract.media_proof_urls)
                    ev_model.timestamp = ev_contract.timestamp
                else:
                    existing.evidence_items.append(
                        EvidenceItemModel.from_contract(ev_contract, incident_id=incident.incident_id)
                    )

        # 5. Synchronize evolution timeline entries using natural key matching
        def _timeline_key(
            entry: IncidentTimeline | IncidentTimelineModel,
        ) -> tuple[datetime, str, str, str | None]:
            return (entry.timestamp, entry.event_type, entry.description, entry.report_id)

        existing_timeline_map = {_timeline_key(t): t for t in existing.timeline}
        incoming_timeline_map = {_timeline_key(t): t for t in incident.timeline}

        # Remove deleted timeline events if any
        for key, t_model in list(existing_timeline_map.items()):
            if key not in incoming_timeline_map:
                existing.timeline.remove(t_model)

        # Update existing in place or append new timeline events
        for key, t_contract in incoming_timeline_map.items():
            if key in existing_timeline_map:
                t_model = existing_timeline_map[key]
                t_model.previous_state = (
                    t_contract.previous_state.value
                    if isinstance(t_contract.previous_state, IncidentState)
                    else t_contract.previous_state
                )
                t_model.new_state = (
                    t_contract.new_state.value
                    if isinstance(t_contract.new_state, IncidentState)
                    else t_contract.new_state
                )
                t_model.previous_severity = (
                    t_contract.previous_severity.value
                    if isinstance(t_contract.previous_severity, IncidentSeverity)
                    else t_contract.previous_severity
                )
                t_model.new_severity = (
                    t_contract.new_severity.value
                    if isinstance(t_contract.new_severity, IncidentSeverity)
                    else t_contract.new_severity
                )
            else:
                existing.timeline.append(
                    IncidentTimelineModel.from_contract(t_contract, incident_id=incident.incident_id)
                )

        db.commit()
        db.refresh(existing)
        logger.info("Updated existing incident: %s", incident.incident_id)
        result = existing.to_contract()
        try:
            publish_incident_update(result)
        except Exception as redis_err:
            logger.error("Failed to publish incident %s update to Redis: %s", incident.incident_id, redis_err)
        return result
    except Exception as e:
        db.rollback()
        logger.exception("Error upserting incident %s: %s", incident.incident_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist incident to database",
        ) from e
