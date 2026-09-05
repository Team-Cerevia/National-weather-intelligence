"""SQLAlchemy 2.x ORM models mapping canonical contracts for PostgreSQL + PostGIS."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_relationship
from sqlalchemy.types import UserDefinedType

from contracts.evidence import (
    EvidenceItem,
    EvidenceRelationship,
    VerificationStatus,
    VerificationSummary,
)
from contracts.incident import (
    Incident,
    IncidentSeverity,
    IncidentState,
    IncidentTimeline,
)
from contracts.weather_report import MediaItem, WeatherReport

from .session import Base


class GeometryPoint(UserDefinedType):
    """PostGIS geometry(Point, 4326) spatial data type."""

    cache_ok = True

    def get_col_spec(self, **kw: Any) -> str:
        return "geometry(Point, 4326)"

    def bind_processor(self, dialect: Any) -> Any:
        def process(value: Any) -> Any:
            if value is None:
                return None
            if isinstance(value, (tuple, list)) and len(value) == 2:
                lon, lat = value
                return f"SRID=4326;POINT({lon} {lat})"
            if isinstance(value, str):
                return value
            return value

        return process

    def result_processor(self, dialect: Any, coltype: Any) -> Any:
        def process(value: Any) -> Any:
            return value

        return process


class ReportModel(Base):
    """SQLAlchemy model representing raw canonical weather reports."""

    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location: Mapped[Any | None] = mapped_column(GeometryPoint, nullable=True)
    h3_cell: Mapped[str | None] = mapped_column(String(15), nullable=True, index=True)

    city: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    district: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True, default="India")

    event_category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_urls: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    media_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    hashtags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")

    # Relationship to evidence items derived from this report
    evidence_items: Mapped[list["EvidenceItemModel"]] = orm_relationship("EvidenceItemModel", back_populates="report")

    __table_args__ = (
        Index("idx_reports_location_gist", "location", postgresql_using="gist"),
        Index("idx_reports_source_timestamp", "source", "timestamp"),
        Index("idx_reports_event_cat", "event_category"),
    )

    @classmethod
    def from_contract(cls, report: WeatherReport) -> "ReportModel":
        """Instantiate ReportModel from canonical WeatherReport contract."""
        loc_val = None
        if report.latitude is not None and report.longitude is not None:
            loc_val = f"SRID=4326;POINT({report.longitude} {report.latitude})"

        media_items_dicts = [item.model_dump() for item in report.media_items]

        return cls(
            report_id=report.report_id,
            source=report.source,
            source_type=report.source_type,
            source_id=report.source_id,
            timestamp=report.timestamp,
            received_at=report.received_at,
            text=report.text,
            latitude=report.latitude,
            longitude=report.longitude,
            location=loc_val,
            h3_cell=report.h3_cell,
            city=report.city,
            district=report.district,
            state=report.state,
            country=report.country,
            event_category=report.event_category,
            url=report.url,
            media_urls=list(report.media_urls),
            media_items=media_items_dicts,
            hashtags=list(report.hashtags),
            language=report.language,
            raw_payload=report.raw_payload,
            schema_version=report.schema_version,
        )

    def to_contract(self) -> WeatherReport:
        """Convert ReportModel back to canonical WeatherReport contract."""
        media_items_obj = [MediaItem(**m) for m in (self.media_items or [])]
        return WeatherReport(
            report_id=self.report_id,
            source=self.source,
            source_type=self.source_type,
            source_id=self.source_id,
            timestamp=self.timestamp,
            received_at=self.received_at,
            text=self.text,
            latitude=self.latitude,
            longitude=self.longitude,
            h3_cell=self.h3_cell,
            city=self.city,
            district=self.district,
            state=self.state,
            country=self.country,
            event_category=self.event_category,
            url=self.url,
            media_urls=self.media_urls or [],
            media_items=media_items_obj,
            hashtags=self.hashtags or [],
            language=self.language,
            raw_payload=self.raw_payload,
            schema_version=self.schema_version,
        )


class IncidentModel(Base):
    """SQLAlchemy model representing clustered real-world weather incidents."""

    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=IncidentState.REPORTED.value, index=True
    )
    severity: Mapped[str] = mapped_column(
        String(32), nullable=False, default=IncidentSeverity.MODERATE.value, index=True
    )
    priority_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location: Mapped[Any | None] = mapped_column(GeometryPoint, nullable=True)
    h3_cells: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    city: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    district: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    state_name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True, default="India")

    first_reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    report_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    # Verification Summary attributes for explainable provenance & filtering
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=VerificationStatus.UNVERIFIED.value, index=True
    )
    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    supporting_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contradicting_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    supporting_sources: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    contradicting_sources: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    verification_explanation: Mapped[str] = mapped_column(
        Text, nullable=False, default="Insufficient multi-source evidence to verify incident."
    )
    verification_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    evidence_items: Mapped[list["EvidenceItemModel"]] = orm_relationship(
        "EvidenceItemModel",
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    timeline: Mapped[list["IncidentTimelineModel"]] = orm_relationship(
        "IncidentTimelineModel",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentTimelineModel.timestamp",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_incidents_location_gist", "location", postgresql_using="gist"),
        Index("idx_incidents_cat_state", "event_category", "state"),
        Index("idx_incidents_sev_prio", "severity", "priority_score"),
        Index("idx_incidents_dates", "first_reported_at", "last_updated_at"),
        Index("idx_incidents_state_city", "state_name", "city"),
    )

    @classmethod
    def from_contract(cls, incident: Incident) -> "IncidentModel":
        """Instantiate IncidentModel and nested evidence/timeline items from canonical Incident."""
        loc_val = None
        if incident.latitude is not None and incident.longitude is not None:
            loc_val = f"SRID=4326;POINT({incident.longitude} {incident.latitude})"

        model = cls(
            incident_id=incident.incident_id,
            title=incident.title,
            event_category=incident.event_category,
            state=incident.state.value if isinstance(incident.state, IncidentState) else str(incident.state),
            severity=(
                incident.severity.value
                if isinstance(incident.severity, IncidentSeverity)
                else str(incident.severity)
            ),
            priority_score=incident.priority_score,
            latitude=incident.latitude,
            longitude=incident.longitude,
            location=loc_val,
            h3_cells=list(incident.h3_cells),
            city=incident.city,
            district=incident.district,
            state_name=incident.state_name,
            country=incident.country,
            first_reported_at=incident.first_reported_at,
            last_updated_at=incident.last_updated_at,
            report_ids=list(incident.report_ids),
        )

        if incident.verification_summary is not None:
            summary = incident.verification_summary
            model.verification_status = (
                summary.verification_status.value
                if isinstance(summary.verification_status, VerificationStatus)
                else str(summary.verification_status)
            )
            model.overall_confidence = summary.overall_confidence
            model.supporting_count = summary.supporting_count
            model.contradicting_count = summary.contradicting_count
            model.supporting_sources = list(summary.supporting_sources)
            model.contradicting_sources = list(summary.contradicting_sources)
            model.verification_explanation = summary.explanation
            model.verification_updated_at = summary.updated_at

            model.evidence_items = [
                EvidenceItemModel.from_contract(item, incident_id=incident.incident_id)
                for item in summary.evidence_items
            ]

        if incident.timeline:
            model.timeline = [
                IncidentTimelineModel.from_contract(t, incident_id=incident.incident_id)
                for t in incident.timeline
            ]

        return model

    def to_contract(self) -> Incident:
        """Convert IncidentModel back to canonical Incident contract."""
        summary_obj = None
        if self.verification_status is not None:
            evidence_contracts = [item.to_contract() for item in (self.evidence_items or [])]
            summary_obj = VerificationSummary(
                verification_status=VerificationStatus(self.verification_status),
                overall_confidence=self.overall_confidence,
                supporting_count=self.supporting_count,
                contradicting_count=self.contradicting_count,
                supporting_sources=self.supporting_sources or [],
                contradicting_sources=self.contradicting_sources or [],
                evidence_items=evidence_contracts,
                explanation=self.verification_explanation
                or "Insufficient multi-source evidence to verify incident.",
                updated_at=self.verification_updated_at or self.last_updated_at,
            )

        timeline_contracts = [t.to_contract() for t in (self.timeline or [])]

        return Incident(
            incident_id=self.incident_id,
            title=self.title,
            event_category=self.event_category,
            state=IncidentState(self.state),
            severity=IncidentSeverity(self.severity),
            priority_score=self.priority_score,
            latitude=self.latitude,
            longitude=self.longitude,
            h3_cells=self.h3_cells or [],
            city=self.city,
            district=self.district,
            state_name=self.state_name,
            country=self.country,
            first_reported_at=self.first_reported_at,
            last_updated_at=self.last_updated_at,
            report_ids=self.report_ids or [],
            verification_summary=summary_obj,
            timeline=timeline_contracts,
        )


class EvidenceItemModel(Base):
    """SQLAlchemy model representing individual evidence items verifying an incident."""

    __tablename__ = "evidence_items"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    incident_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("incidents.incident_id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("reports.report_id", ondelete="SET NULL"), nullable=True, index=True
    )

    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    relationship: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EvidenceRelationship.SUPPORTING.value, index=True
    )

    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_reliability_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    extracted_event: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extracted_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_proof_urls: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    incident: Mapped["IncidentModel"] = orm_relationship("IncidentModel", back_populates="evidence_items")
    report: Mapped["ReportModel | None"] = orm_relationship("ReportModel", back_populates="evidence_items")

    __table_args__ = (
        Index("idx_evidence_incident_rel", "incident_id", "relationship"),
    )

    @classmethod
    def from_contract(cls, item: EvidenceItem, incident_id: str) -> "EvidenceItemModel":
        """Instantiate EvidenceItemModel from canonical EvidenceItem contract."""
        rel_str = (
            item.relationship.value
            if isinstance(item.relationship, EvidenceRelationship)
            else str(item.relationship)
        )
        return cls(
            evidence_id=item.evidence_id,
            incident_id=incident_id,
            report_id=item.report_id,
            source=item.source,
            source_type=item.source_type,
            relationship=rel_str,
            confidence_score=item.confidence_score,
            source_reliability_weight=item.source_reliability_weight,
            reasoning=item.reasoning,
            extracted_event=item.extracted_event,
            extracted_location=item.extracted_location,
            media_proof_urls=list(item.media_proof_urls),
            timestamp=item.timestamp,
        )

    def to_contract(self) -> EvidenceItem:
        """Convert EvidenceItemModel back to canonical EvidenceItem contract."""
        return EvidenceItem(
            evidence_id=self.evidence_id,
            report_id=self.report_id or "",
            source=self.source,
            source_type=self.source_type,
            relationship=EvidenceRelationship(self.relationship),
            confidence_score=self.confidence_score,
            source_reliability_weight=self.source_reliability_weight,
            reasoning=self.reasoning,
            extracted_event=self.extracted_event,
            extracted_location=self.extracted_location,
            media_proof_urls=self.media_proof_urls or [],
            timestamp=self.timestamp,
        )


class IncidentTimelineModel(Base):
    """SQLAlchemy model tracking incident lifecycle evolution and updates."""

    __tablename__ = "incident_timeline"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("incidents.incident_id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    previous_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_state: Mapped[str | None] = mapped_column(String(32), nullable=True)

    previous_severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_severity: Mapped[str | None] = mapped_column(String(32), nullable=True)

    report_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("reports.report_id", ondelete="SET NULL"), nullable=True, index=True
    )

    incident: Mapped["IncidentModel"] = orm_relationship("IncidentModel", back_populates="timeline")
    report: Mapped["ReportModel | None"] = orm_relationship("ReportModel")

    __table_args__ = (
        Index("idx_timeline_incident_time", "incident_id", "timestamp"),
    )

    @classmethod
    def from_contract(cls, entry: IncidentTimeline, incident_id: str) -> "IncidentTimelineModel":
        """Instantiate IncidentTimelineModel from canonical IncidentTimeline contract."""
        prev_st = entry.previous_state.value if isinstance(entry.previous_state, IncidentState) else entry.previous_state
        new_st = entry.new_state.value if isinstance(entry.new_state, IncidentState) else entry.new_state
        prev_sev = (
            entry.previous_severity.value
            if isinstance(entry.previous_severity, IncidentSeverity)
            else entry.previous_severity
        )
        new_sev = (
            entry.new_severity.value
            if isinstance(entry.new_severity, IncidentSeverity)
            else entry.new_severity
        )

        return cls(
            incident_id=incident_id,
            timestamp=entry.timestamp,
            event_type=entry.event_type,
            description=entry.description,
            previous_state=prev_st,
            new_state=new_st,
            previous_severity=prev_sev,
            new_severity=new_sev,
            report_id=entry.report_id,
        )

    def to_contract(self) -> IncidentTimeline:
        """Convert IncidentTimelineModel back to canonical IncidentTimeline contract."""
        prev_st = IncidentState(self.previous_state) if self.previous_state else None
        new_st = IncidentState(self.new_state) if self.new_state else None
        prev_sev = IncidentSeverity(self.previous_severity) if self.previous_severity else None
        new_sev = IncidentSeverity(self.new_severity) if self.new_severity else None

        return IncidentTimeline(
            timestamp=self.timestamp,
            event_type=self.event_type,
            description=self.description,
            previous_state=prev_st,
            new_state=new_st,
            previous_severity=prev_sev,
            new_severity=new_sev,
            report_id=self.report_id,
        )
