from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator

try:
    import h3
except ImportError:
    h3 = None

DEFAULT_H3_RESOLUTION: int = 7


class MediaItem(BaseModel):
    """Metadata for multimodal media attachments (images, videos, audio)."""

    url: str
    media_type: str | None = None  # e.g., "image/jpeg", "video/mp4"
    caption: str | None = None
    source_metadata: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class WeatherReport(BaseModel):
    """Canonical weather report contract shared across ingestion, streaming,
    intelligence, database, and API layers.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    # Core Identifiers & Provenance
    report_id: str = Field(..., description="Canonical unique identifier for this report")
    source: str = Field(..., description="Source name (e.g., imd, open_meteo, x, citizen)")
    source_type: str = Field(..., description="Category of source (e.g., official, weather_api, social_media, news, citizen)")
    source_id: str | None = Field(default=None, description="Original source-specific post/event ID")

    # Timestamps (ISO-8601 UTC)
    timestamp: datetime = Field(..., description="Time when the weather event was observed/reported")
    received_at: datetime | None = Field(default=None, description="Time when report was ingested into our system")

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

    @model_validator(mode="after")
    def compute_h3_cell(self) -> "WeatherReport":
        """Derives H3 spatial cell index if coordinates are present and h3_cell is not provided.
        Does not modify latitude or longitude. Leaves h3_cell as None if coordinates are missing.
        """
        if self.h3_cell is None and self.latitude is not None and self.longitude is not None:
            if h3 is not None:
                try:
                    self.h3_cell = h3.latlng_to_cell(self.latitude, self.longitude, DEFAULT_H3_RESOLUTION)
                except Exception:
                    pass
        return self
