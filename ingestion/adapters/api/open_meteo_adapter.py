"""Open-Meteo API ingestion adapter for real-time weather observations."""

import json
import os
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from contracts.weather_report import WeatherReport
from ingestion.adapters.base import BaseWeatherAdapter
from ingestion.exceptions import IngestionError


class OpenMeteoAdapter(BaseWeatherAdapter):
    """Ingests real-time weather observations from the public Open-Meteo Forecast API."""

    DEFAULT_ENDPOINT = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = base_url or os.getenv("OPEN_METEO_API_URL", self.DEFAULT_ENDPOINT)
        self.timeout = timeout

    def fetch_and_parse(self, latitude: float, longitude: float) -> list[WeatherReport]:
        """Fetches current weather for coordinates and returns canonical WeatherReport objects."""
        report = self.fetch_report(latitude=latitude, longitude=longitude)
        return [report]

    def fetch_report(self, latitude: float, longitude: float) -> WeatherReport:
        """Fetches and parses a single coordinate weather observation into a WeatherReport."""
        # 1. Coordinate range validation (raises ValueError on invalid coordinates)
        self.validate_coordinates(latitude, longitude)

        # 2. Make HTTP request with urllib
        url = (
            f"{self.base_url}"
            f"?latitude={latitude}&longitude={longitude}"
            "&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
            "&timezone=UTC"
        )
        payload = self._request_json(url)

        # 3. Parse and map to canonical WeatherReport
        return self.parse_payload(payload=payload, requested_lat=latitude, requested_lon=longitude)

    def parse_payload(
        self, payload: dict[str, Any], requested_lat: float, requested_lon: float
    ) -> WeatherReport:
        """Parses an official Open-Meteo JSON response payload into a canonical WeatherReport."""
        if not isinstance(payload, dict):
            raise IngestionError("Malformed Open-Meteo response: top-level JSON must be an object.")

        current = payload.get("current")
        if not isinstance(current, dict):
            raise IngestionError("Malformed Open-Meteo response: missing 'current' observation object.")

        raw_time = current.get("time")
        if not raw_time or not isinstance(raw_time, str):
            raise IngestionError("Malformed Open-Meteo response: missing or invalid 'time' in 'current'.")

        # Open-Meteo returns time in UTC when timezone=UTC is requested
        timestamp = self.ensure_utc_datetime(raw_time, assume_utc_if_naive=True)

        # Weather variables
        temp = current.get("temperature_2m")
        humidity = current.get("relative_humidity_2m")
        precip = current.get("precipitation")
        wind = current.get("wind_speed_10m")
        wmo = current.get("weather_code")

        # Deterministic natural language summary text
        text = (
            f"Open-Meteo weather observation for coordinates ({requested_lat:.4f}, {requested_lon:.4f}): "
            f"Temperature {temp}°C, Relative Humidity {humidity}%, Precipitation {precip} mm, "
            f"Wind Speed {wind} km/h, Weather Code {wmo}."
        )

        source = "open_meteo"
        source_type = "weather_api"
        source_id = f"om_{requested_lat:.4f}_{requested_lon:.4f}"
        report_id = self.generate_deterministic_report_id(source, source_id, timestamp)

        return WeatherReport(
            report_id=report_id,
            source=source,
            source_type=source_type,
            source_id=source_id,
            timestamp=timestamp,
            received_at=datetime.now(timezone.utc),
            text=text,
            latitude=float(requested_lat),
            longitude=float(requested_lon),
            country="India",
            raw_payload=payload,
            schema_version="1.0",
        )

    def _request_json(self, url: str) -> dict[str, Any]:
        """Makes an HTTP GET request and decodes the JSON response safely."""
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "National-Weather-Intelligence/0.1.0",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            raise IngestionError(f"Open-Meteo HTTP error {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            reason = str(e.reason).lower()
            if isinstance(e.reason, (socket.timeout, TimeoutError)) or "timed out" in reason:
                raise IngestionError(f"Open-Meteo request timed out: {e.reason}") from e
            raise IngestionError(f"Open-Meteo network connection error: {e.reason}") from e
        except (socket.timeout, TimeoutError) as e:
            raise IngestionError(f"Open-Meteo request timed out: {e}") from e
        except json.JSONDecodeError as e:
            raise IngestionError(f"Open-Meteo returned invalid JSON: {e}") from e
        except Exception as e:
            raise IngestionError(f"Open-Meteo request failed unexpectedly: {e}") from e
