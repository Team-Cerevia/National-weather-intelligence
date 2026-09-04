"""Shared minimal base adapter interface and utilities for weather ingestion."""

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from ingestion.exceptions import IngestionError


class BaseWeatherAdapter(ABC):
    """Abstract base class providing shared coordinate validation, UTC normalization,
    and deterministic report ID generation for all weather adapters.
    """

    @abstractmethod
    def fetch_and_parse(self, **kwargs: Any) -> list[Any]:
        """Fetch raw source data and parse it into canonical objects."""
        raise NotImplementedError

    @staticmethod
    def validate_coordinates(latitude: float | None, longitude: float | None) -> None:
        """Validates coordinate ranges [-90, 90] and [-180, 180].

        Both coordinates must be present, or both must be None.
        Raises ValueError if ranges are invalid or partially supplied.
        """
        if latitude is None and longitude is None:
            return

        if (latitude is None) != (longitude is None):
            raise ValueError("Both latitude and longitude must be provided together. Partial coordinates are rejected.")

        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            raise ValueError("Coordinates must be numeric values.")

        if not (-90.0 <= float(latitude) <= 90.0):
            raise ValueError(f"Latitude {latitude} is outside valid range [-90.0, 90.0].")

        if not (-180.0 <= float(longitude) <= 180.0):
            raise ValueError(f"Longitude {longitude} is outside valid range [-180.0, 180.0].")

    @staticmethod
    def ensure_utc_datetime(dt_or_str: datetime | str, assume_utc_if_naive: bool = False) -> datetime:
        """Converts an ISO string or datetime object into a timezone-aware UTC datetime.

        Raises IngestionError if timestamp is malformed or unparseable.
        """
        if isinstance(dt_or_str, datetime):
            if dt_or_str.tzinfo is None or dt_or_str.tzinfo.utcoffset(dt_or_str) is None:
                if assume_utc_if_naive:
                    return dt_or_str.replace(tzinfo=timezone.utc)
                raise IngestionError(
                    f"Naive datetime '{dt_or_str}' rejected. Must have explicit timezone or assume_utc_if_naive=True."
                )
            return dt_or_str.astimezone(timezone.utc)

        if not isinstance(dt_or_str, str) or not dt_or_str.strip():
            raise IngestionError(f"Invalid timestamp value: {dt_or_str!r}")

        raw_str = dt_or_str.strip()
        # Normalize trailing 'Z' to '+00:00' for standard fromisoformat compatibility
        normalized_str = raw_str[:-1] + "+00:00" if raw_str.endswith("Z") else raw_str

        try:
            parsed = datetime.fromisoformat(normalized_str)
        except (ValueError, TypeError) as e:
            # Fallback for common space-separated date times: YYYY-MM-DD HH:MM:SS
            try:
                parsed = datetime.strptime(raw_str, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                raise IngestionError(f"Failed to parse timestamp string '{dt_or_str}': {e}") from e

        if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
            if assume_utc_if_naive:
                parsed = parsed.replace(tzinfo=timezone.utc)
            else:
                raise IngestionError(f"Parsed timestamp '{dt_or_str}' has no timezone offset.")

        return parsed.astimezone(timezone.utc)

    @staticmethod
    def generate_deterministic_report_id(source: str, source_id: str, timestamp: datetime) -> str:
        """Generates a stable, deterministic report_id using SHA-256 hash token.

        Guarantees that re-ingesting the exact same source observation produces the
        same report_id without random UUIDs.
        """
        utc_ts = timestamp.astimezone(timezone.utc).isoformat()
        identity_key = f"{source}:{source_id}:{utc_ts}"
        hash_token = hashlib.sha256(identity_key.encode("utf-8")).hexdigest()[:16]
        return f"rep_{source}_{hash_token}"
