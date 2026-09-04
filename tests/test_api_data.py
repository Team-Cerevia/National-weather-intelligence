"""Comprehensive offline unit tests for Open-Meteo and IMD weather API adapters."""

import io
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from contracts.weather_report import WeatherReport
from ingestion.adapters.api.imd_adapter import ImdAdapter
from ingestion.adapters.api.open_meteo_adapter import OpenMeteoAdapter
from ingestion.adapters.base import BaseWeatherAdapter
from ingestion.exceptions import IngestionError

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "ingestion" / "fixtures"


def _make_mock_response(payload: Any) -> MagicMock:
    """Helper to mock urllib.request.urlopen returning encoded JSON."""
    encoded = json.dumps(payload).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = encoded
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None
    return mock_resp


# =====================================================================
# OPEN-METEO ADAPTER TESTS
# =====================================================================


def test_open_meteo_successful_ingestion():
    """Test 1: Successful ingestion of Open-Meteo response matching official fixture."""
    fixture_path = FIXTURES_DIR / "weather_observations.json"
    with open(fixture_path, encoding="utf-8") as f:
        fixture_data = json.load(f)

    adapter = OpenMeteoAdapter()

    with patch("urllib.request.urlopen", return_value=_make_mock_response(fixture_data)):
        reports = adapter.fetch_and_parse(latitude=28.625, longitude=77.25)

    assert len(reports) == 1
    report = reports[0]

    assert isinstance(report, WeatherReport)
    assert report.source == "open_meteo"
    assert report.source_type == "weather_api"
    assert report.latitude == 28.625
    assert report.longitude == 77.25
    assert report.country == "India"
    assert report.timestamp == datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    assert report.timestamp.tzinfo == timezone.utc
    assert report.report_id.startswith("rep_open_meteo_")
    assert "Temperature 31.4°C" in report.text
    assert "Precipitation 12.8 mm" in report.text
    assert "Wind Speed 24.0 km/h" in report.text
    assert report.raw_payload == fixture_data


def test_open_meteo_invalid_coordinates():
    """Test 2: Invalid or partial coordinates raise ValueError before HTTP call."""
    adapter = OpenMeteoAdapter()

    with patch("urllib.request.urlopen") as mock_urlopen:
        # Latitude out of range
        with pytest.raises(ValueError, match="Latitude 95.0 is outside valid range"):
            adapter.fetch_report(latitude=95.0, longitude=77.0)

        # Longitude out of range
        with pytest.raises(ValueError, match="Longitude -195.0 is outside valid range"):
            adapter.fetch_report(latitude=28.0, longitude=-195.0)

        # Partial coordinates
        with pytest.raises(ValueError, match="Both latitude and longitude must be provided together"):
            BaseWeatherAdapter.validate_coordinates(28.0, None)

        # Verify no network request was made
        mock_urlopen.assert_not_called()


def test_open_meteo_http_error():
    """Test 3: HTTP status error (e.g. 500) raises domain-specific IngestionError."""
    adapter = OpenMeteoAdapter()
    http_err = urllib.error.HTTPError(
        url="https://api.open-meteo.com/v1/forecast",
        code=500,
        msg="Internal Server Error",
        hdrs={},  # type: ignore[arg-type]
        fp=io.BytesIO(b"Server Error"),
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(IngestionError, match="Open-Meteo HTTP error 500"):
            adapter.fetch_report(latitude=28.625, longitude=77.25)


def test_open_meteo_timeout():
    """Test 4: Request timeout raises domain-specific IngestionError."""
    adapter = OpenMeteoAdapter()
    url_err = urllib.error.URLError(reason="connection timed out")

    with patch("urllib.request.urlopen", side_effect=url_err):
        with pytest.raises(IngestionError, match="Open-Meteo request timed out"):
            adapter.fetch_report(latitude=28.625, longitude=77.25)


def test_open_meteo_malformed_response():
    """Test 5: Malformed JSON or missing required observation keys raises IngestionError."""
    adapter = OpenMeteoAdapter()

    # Missing 'current' key
    with patch("urllib.request.urlopen", return_value=_make_mock_response({"latitude": 28.0})):
        with pytest.raises(IngestionError, match="missing 'current' observation object"):
            adapter.fetch_report(latitude=28.0, longitude=77.0)

    # Missing 'time' in 'current'
    with patch("urllib.request.urlopen", return_value=_make_mock_response({"current": {"temperature_2m": 30.0}})):
        with pytest.raises(IngestionError, match="missing or invalid 'time'"):
            adapter.fetch_report(latitude=28.0, longitude=77.0)

    # Top-level is not a dict
    with patch("urllib.request.urlopen", return_value=_make_mock_response(["not_a_dict"])):
        with pytest.raises(IngestionError, match="top-level JSON must be an object"):
            adapter.fetch_report(latitude=28.0, longitude=77.0)


def test_open_meteo_weather_report_serde():
    """Test 6: Output WeatherReport strictly supports Pydantic JSON serialization & deserialization."""
    fixture_path = FIXTURES_DIR / "weather_observations.json"
    with open(fixture_path, encoding="utf-8") as f:
        fixture_data = json.load(f)

    adapter = OpenMeteoAdapter()
    with patch("urllib.request.urlopen", return_value=_make_mock_response(fixture_data)):
        report = adapter.fetch_report(latitude=28.625, longitude=77.25)

    # Verify deterministic report_id repeatability
    second_run = adapter.parse_payload(fixture_data, requested_lat=28.625, requested_lon=77.25)
    assert report.report_id == second_run.report_id

    # Verify round-trip serde
    json_str = report.model_dump_json()
    reconstructed = WeatherReport.model_validate_json(json_str)

    assert reconstructed.report_id == report.report_id
    assert reconstructed.timestamp == report.timestamp
    assert reconstructed.latitude == report.latitude
    assert reconstructed.longitude == report.longitude
    assert reconstructed.source == report.source


# =====================================================================
# IMD CURRENT WEATHER ADAPTER TESTS
# =====================================================================


def test_imd_successful_ingestion():
    """Test 7: Successful ingestion of representative mock IMD Current Weather fixture."""
    fixture_path = FIXTURES_DIR / "imd_reports.json"
    with open(fixture_path, encoding="utf-8") as f:
        fixture_data = json.load(f)

    adapter = ImdAdapter()

    with patch("urllib.request.urlopen", return_value=_make_mock_response(fixture_data)):
        reports = adapter.fetch_and_parse()

    assert len(reports) == 1
    report = reports[0]

    assert isinstance(report, WeatherReport)
    assert report.source == "imd"
    assert report.source_type == "official"
    assert report.source_id == "42182"
    assert report.city == "New Delhi (Safdarjung)"
    assert report.latitude == 28.584
    assert report.longitude == 77.206
    assert report.country == "India"
    assert report.timestamp == datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    assert report.timestamp.tzinfo == timezone.utc
    assert report.report_id.startswith("rep_imd_")
    assert "Temperature 33.2°C" in report.text
    assert "Relative Humidity 70%" in report.text
    assert "Rainfall (24h) 12.0 mm" in report.text
    assert "Wind Speed 15.0 km/h" in report.text


def test_imd_utc_aware_timestamp_handling():
    """Test 8: IMD Current Weather observation time is strictly verified as timezone-aware UTC."""
    adapter = ImdAdapter()

    sample_payload = {
        "station_id": "42182",
        "station": "Safdarjung",
        "obs_date": "2026-09-04",
        "obs_time_utc": "14:30:00",
    }

    reports = adapter.parse_payload([sample_payload])
    assert len(reports) == 1
    report = reports[0]

    assert report.timestamp.tzinfo == timezone.utc
    assert report.timestamp == datetime(2026, 9, 4, 14, 30, 0, tzinfo=timezone.utc)
    assert report.timestamp.utcoffset().total_seconds() == 0  # type: ignore[union-attr]


def test_imd_missing_optional_fields():
    """Test 9: IMD record with missing rainfall and missing coordinates produces valid report,
    while partial coordinates are strictly rejected.
    """
    adapter = ImdAdapter()

    # Valid missing optional fields: no rainfall, no coordinates
    minimal_record = {
        "station_id": "42182",
        "station": "Safdarjung",
        "obs_date": "2026-09-04",
        "obs_time_utc": "10:00:00",
        "temperature": 30.0,
    }

    reports = adapter.parse_payload([minimal_record])
    assert len(reports) == 1
    report = reports[0]
    assert report.latitude is None
    assert report.longitude is None
    assert "Rainfall (24h) not reported" in report.text

    # Partial coordinates (latitude present, longitude missing) must raise IngestionError
    partial_coord_record = {
        "station_id": "42182",
        "station": "Safdarjung",
        "obs_date": "2026-09-04",
        "obs_time_utc": "10:00:00",
        "latitude": 28.584,
        "longitude": None,
    }
    with pytest.raises(IngestionError, match="Partial coordinates in IMD record"):
        adapter.parse_payload([partial_coord_record])


def test_imd_http_error():
    """Test 10: IMD API HTTP error (e.g. 403 Forbidden) raises IngestionError."""
    adapter = ImdAdapter()
    http_err = urllib.error.HTTPError(
        url="https://api.imd.gov.in/api/v1/current_wx",
        code=403,
        msg="Forbidden",
        hdrs={},  # type: ignore[arg-type]
        fp=io.BytesIO(b"Forbidden"),
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(IngestionError, match="IMD API HTTP error 403"):
            adapter.fetch_and_parse(station_id="42182")


def test_imd_malformed_response():
    """Test 11: Malformed IMD response (missing station id/name, missing date) raises IngestionError."""
    adapter = ImdAdapter()

    # Missing both station_id and station name
    with pytest.raises(IngestionError, match="missing both station_id and station name"):
        adapter.parse_payload([{"obs_date": "2026-09-04", "temperature": 30.0}])

    # Missing obs_date
    with pytest.raises(IngestionError, match="missing 'obs_date'"):
        adapter.parse_payload([{"station_id": "42182", "station": "Safdarjung"}])

    # Unexpected top-level type (e.g. integer)
    with pytest.raises(IngestionError, match="Malformed IMD response"):
        adapter.parse_payload(12345)  # type: ignore[arg-type]


def test_imd_contract_compatibility():
    """Test 12: IMD WeatherReport validates contract invariants and serde cleanly."""
    fixture_path = FIXTURES_DIR / "imd_reports.json"
    with open(fixture_path, encoding="utf-8") as f:
        fixture_data = json.load(f)

    adapter = ImdAdapter()
    reports = adapter.parse_payload(fixture_data)
    report = reports[0]

    # Verify deterministic report_id consistency
    repeat_reports = adapter.parse_payload(fixture_data)
    assert report.report_id == repeat_reports[0].report_id

    # Verify serialization and deserialization
    json_str = report.model_dump_json()
    reconstructed = WeatherReport.model_validate_json(json_str)

    assert reconstructed.report_id == report.report_id
    assert reconstructed.source == "imd"
    assert reconstructed.source_type == "official"
    assert reconstructed.timestamp == report.timestamp
    assert reconstructed.latitude == report.latitude
    assert reconstructed.longitude == report.longitude
