from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from contracts.weather_report import MediaItem, WeatherReport, DEFAULT_H3_RESOLUTION


def test_1_valid_complete_weather_report():
    raw_data = {"raw_sensor_code": 102, "reporter": "station_01"}
    report = WeatherReport(
        report_id="rep_1001",
        source="open_meteo",
        source_type="weather_api",
        source_id="om_88219",
        timestamp=datetime(2026, 9, 4, 10, 30, tzinfo=timezone.utc),
        received_at=datetime(2026, 9, 4, 10, 31, tzinfo=timezone.utc),
        text="Heavy rainfall recorded in Noida Sector 62",
        latitude=28.627,
        longitude=77.372,
        city="Noida",
        district="Gautam Buddha Nagar",
        state="Uttar Pradesh",
        country="India",
        event_category="heavy_rain",
        url="https://open-meteo.com/en/forecast",
        media_urls=["https://example.com/rain.jpg"],
        media_items=[
            MediaItem(
                url="https://example.com/rain.jpg",
                media_type="image/jpeg",
                caption="Rain gauge reading",
                source_metadata={"resolution": "1920x1080"},
            )
        ],
        hashtags=["#NoidaRain", "#IMDAlert"],
        language="en",
        raw_payload=raw_data,
        schema_version="1.0",
    )

    assert report.report_id == "rep_1001"
    assert report.source == "open_meteo"
    assert report.latitude == 28.627
    assert report.longitude == 77.372
    assert report.h3_cell is not None
    assert isinstance(report.h3_cell, str)
    assert len(report.media_items) == 1
    assert report.media_items[0].media_type == "image/jpeg"
    assert report.raw_payload == raw_data


def test_2_minimal_valid_weather_report():
    report = WeatherReport(
        report_id="rep_min_01",
        source="citizen",
        source_type="citizen",
        timestamp="2026-09-04T12:00:00Z",
        text="Waterlogging near city station",
    )

    assert report.report_id == "rep_min_01"
    assert report.source == "citizen"
    assert report.source_type == "citizen"
    assert report.text == "Waterlogging near city station"
    assert report.latitude is None
    assert report.longitude is None
    assert report.h3_cell is None
    assert report.country == "India"
    assert report.schema_version == "1.0"


def test_3_missing_coordinates():
    report = WeatherReport(
        report_id="rep_no_geo",
        source="social",
        source_type="social_media",
        timestamp=datetime.now(timezone.utc),
        text="Heavy winds in South Delhi area",
        latitude=None,
        longitude=None,
    )

    assert report.latitude is None
    assert report.longitude is None
    assert report.h3_cell is None


def test_4_missing_optional_fields():
    report = WeatherReport(
        report_id="rep_opt_01",
        source="news",
        source_type="news",
        timestamp="2026-09-04T14:00:00Z",
        text="Flood warning issued for coastal areas",
    )

    assert report.source_id is None
    assert report.received_at is None
    assert report.event_category is None
    assert report.url is None
    assert report.media_urls == []
    assert report.media_items == []
    assert report.hashtags == []
    assert report.language is None
    assert report.raw_payload is None


def test_5_invalid_latitude():
    with pytest.raises(ValidationError) as exc_info:
        WeatherReport(
            report_id="rep_err_lat",
            source="test",
            source_type="test",
            timestamp="2026-09-04T12:00:00Z",
            text="Invalid lat test",
            latitude=95.0,  # Invalid latitude (>90)
            longitude=77.0,
        )
    assert "latitude" in str(exc_info.value)


def test_6_invalid_longitude():
    with pytest.raises(ValidationError) as exc_info:
        WeatherReport(
            report_id="rep_err_lon",
            source="test",
            source_type="test",
            timestamp="2026-09-04T12:00:00Z",
            text="Invalid lon test",
            latitude=28.0,
            longitude=-195.0,  # Invalid longitude (<-180)
        )
    assert "longitude" in str(exc_info.value)


def test_7_timestamp_validation():
    # Valid ISO string auto-parsed
    report = WeatherReport(
        report_id="rep_ts_01",
        source="imd",
        source_type="official",
        timestamp="2026-09-04T15:30:00Z",
        text="Rainfall forecast update",
    )

    assert isinstance(report.timestamp, datetime)
    assert report.timestamp.year == 2026
    assert report.timestamp.month == 9

    # Invalid timestamp format raises ValidationError
    with pytest.raises(ValidationError):
        WeatherReport(
            report_id="rep_ts_err",
            source="imd",
            source_type="official",
            timestamp="not-a-datetime",
            text="Rainfall forecast update",
        )


def test_8_h3_generation_when_coordinates_exist():
    import h3

    lat, lon = 28.627, 77.372
    report = WeatherReport(
        report_id="rep_h3_calc",
        source="open_meteo",
        source_type="weather_api",
        timestamp="2026-09-04T10:00:00Z",
        text="Noida report",
        latitude=lat,
        longitude=lon,
    )

    expected_h3 = h3.latlng_to_cell(lat, lon, DEFAULT_H3_RESOLUTION)
    assert report.h3_cell == expected_h3
    assert report.latitude == lat
    assert report.longitude == lon


def test_9_h3_remains_null_when_coordinates_do_not_exist():
    report = WeatherReport(
        report_id="rep_h3_null",
        source="citizen",
        source_type="citizen",
        timestamp="2026-09-04T10:00:00Z",
        text="No coords report",
    )

    assert report.h3_cell is None


def test_10_media_metadata_validation():
    media = MediaItem(
        url="https://example.com/video.mp4",
        media_type="video/mp4",
        caption="Storm footage",
        source_metadata={"duration_sec": 15},
    )
    report = WeatherReport(
        report_id="rep_media_01",
        source="social",
        source_type="social_media",
        timestamp="2026-09-04T10:00:00Z",
        text="Check out this storm video",
        media_items=[media],
    )

    assert len(report.media_items) == 1
    assert report.media_items[0].url == "https://example.com/video.mp4"
    assert report.media_items[0].caption == "Storm footage"


def test_11_schema_version():
    report_default = WeatherReport(
        report_id="rep_ver_1",
        source="imd",
        source_type="official",
        timestamp="2026-09-04T10:00:00Z",
        text="Standard report",
    )
    assert report_default.schema_version == "1.0"

    report_custom = WeatherReport(
        report_id="rep_ver_2",
        source="imd",
        source_type="official",
        timestamp="2026-09-04T10:00:00Z",
        text="Custom schema version report",
        schema_version="1.1",
    )
    assert report_custom.schema_version == "1.1"


def test_12_serialization_deserialization():
    report = WeatherReport(
        report_id="rep_serde_01",
        source="open_meteo",
        source_type="weather_api",
        timestamp="2026-09-04T10:00:00+00:00",
        text="Test serialization",
        latitude=19.076,
        longitude=72.877,
        city="Mumbai",
    )

    json_str = report.model_dump_json()
    reconstructed = WeatherReport.model_validate_json(json_str)

    assert reconstructed.report_id == report.report_id
    assert reconstructed.source == report.source
    assert reconstructed.latitude == report.latitude
    assert reconstructed.longitude == report.longitude
    assert reconstructed.h3_cell == report.h3_cell
    assert reconstructed.city == report.city


def test_13_preservation_of_raw_payload_and_provenance():
    original_raw = {
        "sensor_id": "S-992",
        "raw_temp_c": 34.5,
        "nested_meta": {"status": "ok", "retry": 0},
    }
    report = WeatherReport(
        report_id="rep_prov_01",
        source="sensor_network",
        source_type="official",
        source_id="S-992",
        timestamp="2026-09-04T10:00:00Z",
        text="Sensor data payload",
        raw_payload=original_raw,
    )

    assert report.source == "sensor_network"
    assert report.source_type == "official"
    assert report.source_id == "S-992"
    assert report.raw_payload == original_raw
    # Verify original dict structure is untouched
    assert report.raw_payload["nested_meta"]["status"] == "ok"
