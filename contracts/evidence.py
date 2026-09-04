from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

# Indian Standard Time (IST) offset: UTC + 05:30
IST = timezone(timedelta(hours=5, minutes=30))


def get_ist_now() -> datetime:
    """Returns current datetime in Indian Standard Time (IST, UTC+5:30)."""
    return datetime.now(IST)



class VerificationStatus(str, Enum):
    """Status indicating the verification state of a report or incident based on evidence."""

    SUPPORTED = "SUPPORTED"
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    PENDING_REVIEW = "PENDING_REVIEW"


class EvidenceRelationship(str, Enum):
    """Relationship between an evidence report and an incident or observation."""

    SUPPORTING = "SUPPORTING"
    CORROBORATING = "CORROBORATING"
    CONTRADICTING = "CONTRADICTING"
    NEUTRAL = "NEUTRAL"


class EvidenceItem(BaseModel):
    """Represents a discrete piece of evidence linking a WeatherReport to an incident
    or verifying a weather observation.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    evidence_id: str = Field(..., description="Unique ID for this evidence item")
    report_id: str = Field(..., description="ID of the underlying WeatherReport providing this evidence")
    source: str = Field(..., description="Source name (e.g. imd, x, citizen, open_meteo)")
    source_type: str = Field(..., description="Source category (e.g. official, social_media, citizen)")

    relationship: EvidenceRelationship = Field(
        default=EvidenceRelationship.SUPPORTING,
        description="Whether this evidence supports or contradicts the incident",
    )

    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Processing confidence score exposing uncertainty (0.0 to 1.0), or None if unassigned",
    )
    source_reliability_weight: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Source trust weight (e.g. official=1.0, social=0.6), or None if unassigned",
    )

    reasoning: str = Field(..., description="Transparent explanation of why this report counts as supporting/contradicting evidence")

    extracted_event: str | None = Field(default=None, description="Extracted event type (e.g., heavy_rain, flood)")
    extracted_location: str | None = Field(default=None, description="Extracted location name or H3 cell")
    media_proof_urls: list[str] = Field(default_factory=list, description="URLs of attached photo/video proof")

    timestamp: datetime = Field(default_factory=get_ist_now, description="Timestamp of the evidence report in IST (Asia/Kolkata)")


class VerificationSummary(BaseModel):
    """Explainable evidence summary answering: 'Why does the system believe this incident is real?'"""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Overall evidence-based verification status",
    )
    overall_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Aggregated confidence score exposing uncertainty (0.0 to 1.0), or None if uncalculated",
    )

    supporting_count: int = Field(default=0, ge=0, description="Total number of supporting evidence items")
    contradicting_count: int = Field(default=0, ge=0, description="Total number of contradicting evidence items")

    supporting_sources: list[str] = Field(default_factory=list, description="Unique source list of supporting evidence")
    contradicting_sources: list[str] = Field(default_factory=list, description="Unique source list of contradicting evidence")

    evidence_items: list[EvidenceItem] = Field(default_factory=list, description="Detailed list of all evidence items")

    explanation: str = Field(
        default="Insufficient multi-source evidence to verify incident.",
        description="Transparent human-readable evidence summary for operators",
    )

    updated_at: datetime = Field(default_factory=get_ist_now, description="Last evidence evaluation time in IST (Asia/Kolkata)")

