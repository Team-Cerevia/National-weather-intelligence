from datetime import datetime, timezone
from typing import Any
import h3
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_H3_RESOLUTION: int = 7


class MediaItem(BaseModel):
    """Metadata for multimodal media attachments (images, videos, audio)."""

    url: str
    media_type: str | None = None  # e.g., "image/jpeg", "video/mp4"
    caption: str | None = None
    source_metadata: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class WeatherReport(BaseModel):
    """Canonical weather report contract shared across ingestion, streaming,
    intelligence, database, and API layers.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    # Core Identifiers & Provenance
    report_id: str = Field(..., description="Canonical unique identifier for this report")
    source: str = Field(..., description="Source name (e.g., imd, open_meteo, x, citizen)")
    source_type: str = Field(..., description="Category of source (e.g., official, weather_api, social_media, news, citizen)")
    source_id: str | None = Field(default=None, description="Original source-specific post/event ID")

    # Timestamps (Timezone-Aware UTC)
    timestamp: datetime = Field(..., description="Time when the weather event was observed/reported (timezone-aware UTC)")
    received_at: datetime | None = Field(default=None, description="Time when report was ingested into our system (timezone-aware UTC)")

    # Unstructured Content
    text: str = Field(..., description="Original raw report text or headline")

    # Geospatial Indexing
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0, description="Latitude in decimal degrees [-90, 90]")
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0, description="Longitude in decimal degrees [-180, 180]")
    h3_cell: str | None = Field(default=None, description="Derived H3 spatial hexagon index")

    # Location Hierarchy
    city: str | None = None
    district: str | None = None
    state: str | None = None
    country: str | None = "India"

    # Weather Event Category (Downstream AI populates if missing)
    event_category: str | None = Field(default=None, description="Inferred or reported event type (e.g., heavy_rain, flood)")

    # Metadata & Multimodal
    url: str | None = Field(default=None, description="Original URL reference")
    media_urls: list[str] = Field(default_factory=list, description="List of media URL strings")
    media_items: list[MediaItem] = Field(default_factory=list, description="Structured multimodal media items")
    hashtags: list[str] = Field(default_factory=list, description="Hashtags contained in report")

    language: str | None = Field(default=None, description="Language code (e.g., en, hi)")

    # Raw Payload Provenance
    raw_payload: dict[str, Any] | None = Field(default=None, description="Unmodified raw payload from source")

    # Contract Schema Versioning
    schema_version: str = Field(default="1.0", description="Contract schema version")

    @field_validator("timestamp", "received_at", mode="after")
    @classmethod
    def validate_timezone_aware_utc(cls, v: datetime | None) -> datetime | None:
        """Enforces timezone awareness for datetimes and normalizes them to canonical UTC."""
        if v is None:
            return None
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("Timestamp must be timezone-aware (e.g. UTC or with explicit offset). Naive datetimes are rejected.")
        return v.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_and_compute_h3(self) -> "WeatherReport":
        """Derives H3 spatial cell index if coordinates exist or validates consistency if h3_cell is supplied.

        Does not silently swallow H3 calculation failures.
        """
        if self.latitude is not None and self.longitude is not None:
            try:
                derived_h3 = h3.latlng_to_cell(self.latitude, self.longitude, DEFAULT_H3_RESOLUTION)
            except Exception as e:
                raise ValueError(f"H3 cell derivation failed for lat={self.latitude}, lon={self.longitude}: {e}") from e

            if self.h3_cell is not None:
                if self.h3_cell != derived_h3:
                    raise ValueError(
                        f"Supplied h3_cell '{self.h3_cell}' does not match derived cell '{derived_h3}' "
                        f"for coordinates lat={self.latitude}, lon={self.longitude} at resolution {DEFAULT_H3_RESOLUTION}."
                    )
            else:
                self.h3_cell = derived_h3
        elif self.h3_cell is not None:
            if not h3.is_valid_cell(self.h3_cell):
                raise ValueError(f"Supplied h3_cell '{self.h3_cell}' is not a valid H3 cell index.")
        return self
