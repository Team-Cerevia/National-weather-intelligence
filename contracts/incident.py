from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .evidence import VerificationSummary


class IncidentState(str, Enum):
    """Life cycle states of a weather incident."""

    REPORTED = "REPORTED"
    VERIFIED = "VERIFIED"
    ESCALATING = "ESCALATING"
    DE_ESCALATING = "DE_ESCALATING"
    RESOLVED = "RESOLVED"


class IncidentSeverity(str, Enum):
    """Severity levels of a weather incident."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentTimeline(BaseModel):
    """Individual timeline entry tracking incident evolution events."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of event in timezone-aware UTC",
    )
    event_type: str = Field(
        ..., description="Timeline event type (e.g. created, state_change, report_added, severity_escalated)"
    )
    description: str = Field(..., description="Human-readable explanation of timeline entry")

    previous_state: IncidentState | None = None
    new_state: IncidentState | None = None

    previous_severity: IncidentSeverity | None = None
    new_severity: IncidentSeverity | None = None

    report_id: str | None = Field(default=None, description="Associated report ID if triggered by a report")

    @field_validator("timestamp", mode="after")
    @classmethod
    def validate_timestamp_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError(
                "Timestamp must be timezone-aware (e.g. UTC or with explicit offset). Naive datetimes are rejected."
            )
        return v.astimezone(timezone.utc)


class Incident(BaseModel):
    """Canonical Incident contract representing a clustered real-world weather incident."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    incident_id: str = Field(..., description="Unique canonical identifier for the incident")
    title: str = Field(..., description="Descriptive title of the incident")
    event_category: str = Field(
        ..., description="Canonical weather category (e.g. RAIN, FLOOD, THUNDERSTORM, HEATWAVE)"
    )

    state: IncidentState = Field(default=IncidentState.REPORTED, description="Current lifecycle state")
    severity: IncidentSeverity = Field(default=IncidentSeverity.MODERATE, description="Current severity level")

    priority_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Calculated urgency/priority score (0-100), or None if unassigned",
    )

    # Geospatial Location & Spatial Expansion
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0, description="Centroid latitude")
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0, description="Centroid longitude")
    h3_cells: list[str] = Field(default_factory=list, description="H3 hexagon cells covered by spatial expansion")

    city: str | None = None
    district: str | None = None
    state_name: str | None = Field(default=None, description="State name in India")
    country: str | None = "India"

    # Temporal Bounds (Timezone-Aware UTC)
    first_reported_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time first report was received in timezone-aware UTC",
    )
    last_updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time of last update in timezone-aware UTC",
    )

    # Clustered Reports & Provenance
    report_ids: list[str] = Field(default_factory=list, description="IDs of all reports clustered into this incident")
    verification_summary: VerificationSummary | None = Field(default=None, description="Evidence & provenance summary")

    # Evolution Timeline
    timeline: list[IncidentTimeline] = Field(default_factory=list, description="Complete evolution event history")

    @field_validator("first_reported_at", "last_updated_at", mode="after")
    @classmethod
    def validate_datetimes_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError(
                "Datetimes must be timezone-aware (e.g. UTC or with explicit offset). Naive datetimes are rejected."
            )
        return v.astimezone(timezone.utc)
