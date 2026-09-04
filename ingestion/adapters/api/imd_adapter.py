"""IMD Current Weather API ingestion adapter for official weather observations."""

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

# Isolated field mapping for IMD Current Weather API (/api/v1/current_wx).
# Uses explicit, minimal representative keys matching the documented conceptual schema.
# Update this dictionary if live production schema keys vary.
IMD_CURRENT_WX_FIELDS = {
    "station_id": "station_id",
    "station_name": "station",
    "obs_date": "obs_date",
    "obs_time_utc": "obs_time_utc",
    "temperature": "temperature",
    "humidity": "humidity",
    "wind_speed": "wind_speed",
    "wind_direction": "wind_direction",
    "rainfall_24h": "rainfall_24h",
    "latitude": "latitude",
    "longitude": "longitude",
}


class ImdAdapter(BaseWeatherAdapter):
    """Ingests official weather observations from the IMD Current Weather API."""

    DEFAULT_ENDPOINT = "https://api.imd.gov.in/api/v1/current_wx"

    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = base_url or os.getenv("IMD_API_URL", self.DEFAULT_ENDPOINT)
        self.api_key = api_key or os.getenv("WEATHER_API_KEY")
        self.timeout = timeout

    def fetch_and_parse(self, station_id: str | None = None) -> list[WeatherReport]:
        """Fetches current weather from IMD endpoint and returns canonical WeatherReports."""
        url = self.base_url
        if station_id:
            url = f"{self.base_url}?id={station_id}"

        payload = self._request_json(url)
        return self.parse_payload(payload)

    def parse_payload(self, payload: dict[str, Any] | list[dict[str, Any]]) -> list[WeatherReport]:
        """Parses an IMD Current Weather API response payload into canonical WeatherReport objects."""
        items = self._extract_items(payload)
        reports: list[WeatherReport] = []

        for item in items:
            report = self._parse_single_observation(item)
            reports.append(report)

        return reports

    def _extract_items(self, payload: Any) -> list[dict[str, Any]]:
        """Extracts individual station observation records from response payload."""
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if isinstance(payload, dict):
            if "data" in payload and isinstance(payload["data"], list):
                return [item for item in payload["data"] if isinstance(item, dict)]
            # If payload is itself a single station dictionary with station_id
            if IMD_CURRENT_WX_FIELDS["station_id"] in payload or IMD_CURRENT_WX_FIELDS["station_name"] in payload:
                return [payload]

        raise IngestionError("Malformed IMD response: expected a list or object containing a 'data' array.")

    def _parse_single_observation(self, item: dict[str, Any]) -> WeatherReport:
        """Normalizes a single IMD station observation dictionary into a canonical WeatherReport."""
        f = IMD_CURRENT_WX_FIELDS

        station_id = item.get(f["station_id"])
        station_name = item.get(f["station_name"])

        if not station_id and not station_name:
            raise IngestionError("Malformed IMD record: missing both station_id and station name.")

        station_id_str = str(station_id) if station_id is not None else str(station_name)
        display_name = str(station_name) if station_name is not None else f"Station {station_id_str}"

        # Parse observation timestamp (officially documented as UTC)
        obs_date = item.get(f["obs_date"])
        obs_time = item.get(f["obs_time_utc"])

        if not obs_date:
            raise IngestionError(f"Malformed IMD record for station '{station_id_str}': missing '{f['obs_date']}'.")

        time_part = obs_time if obs_time else "00:00:00"
        dt_str = f"{obs_date}T{time_part}" if "T" not in str(obs_date) else str(obs_date)

        # IMD current_wx time of observation is UTC
        timestamp = self.ensure_utc_datetime(dt_str, assume_utc_if_naive=True)

        # Optional coordinates handling
        raw_lat = item.get(f["latitude"])
        raw_lon = item.get(f["longitude"])

        lat: float | None = None
        lon: float | None = None

        if raw_lat is not None and raw_lon is not None:
            try:
                lat = float(raw_lat)
                lon = float(raw_lon)
                self.validate_coordinates(lat, lon)
            except ValueError as e:
                raise IngestionError(f"Invalid coordinates in IMD record for '{station_id_str}': {e}") from e
        elif (raw_lat is None) != (raw_lon is None):
            raise IngestionError(
                f"Partial coordinates in IMD record for '{station_id_str}': lat={raw_lat}, lon={raw_lon}."
            )

        # Weather variables
        temp = item.get(f["temperature"])
        humidity = item.get(f["humidity"])
        rainfall = item.get(f["rainfall_24h"])
        wind_speed = item.get(f["wind_speed"])

        temp_str = f"Temperature {temp}°C" if temp is not None else "Temperature not reported"
        humidity_str = f"Relative Humidity {humidity}%" if humidity is not None else "Humidity not reported"
        rainfall_str = f"Rainfall (24h) {rainfall} mm" if rainfall is not None else "Rainfall (24h) not reported"
        wind_str = f"Wind Speed {wind_speed} km/h" if wind_speed is not None else "Wind speed not reported"

        text = (
            f"IMD Current Weather observation for {display_name}: "
            f"{temp_str}, {humidity_str}, {rainfall_str}, {wind_str}."
        )

        source = "imd"
        source_type = "official"
        source_id = station_id_str
        report_id = self.generate_deterministic_report_id(source, source_id, timestamp)

        return WeatherReport(
            report_id=report_id,
            source=source,
            source_type=source_type,
            source_id=source_id,
            timestamp=timestamp,
            received_at=datetime.now(timezone.utc),
            text=text,
            latitude=lat,
            longitude=lon,
            city=str(station_name) if station_name else None,
            country="India",
            raw_payload=item,
            schema_version="1.0",
        )

    def _request_json(self, url: str) -> Any:
        """Executes an HTTP GET request to the IMD endpoint with optional auth headers."""
        headers = {
            "User-Agent": "National-Weather-Intelligence/0.1.0",
            "Accept": "application/json",
        }
        if self.api_key and self.api_key != "your_weather_api_key_here":
            headers["X-API-KEY"] = self.api_key

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            raise IngestionError(f"IMD API HTTP error {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            reason = str(e.reason).lower()
            if isinstance(e.reason, (socket.timeout, TimeoutError)) or "timed out" in reason:
                raise IngestionError(f"IMD API request timed out: {e.reason}") from e
            raise IngestionError(f"IMD API network connection error: {e.reason}") from e
        except (socket.timeout, TimeoutError) as e:
            raise IngestionError(f"IMD API request timed out: {e}") from e
        except json.JSONDecodeError as e:
            raise IngestionError(f"IMD API returned invalid JSON: {e}") from e
        except Exception as e:
            raise IngestionError(f"IMD API request failed unexpectedly: {e}") from e
