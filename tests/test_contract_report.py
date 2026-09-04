from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest
from pydantic import ValidationError

from contracts.weather_report import MediaItem, WeatherReport, DEFAULT_H3_RESOLUTION


def test_1_timezone_aware_timestamp_acceptance():
    # UTC datetime accepted
    ts_utc = datetime(2026, 9, 4, 10, 30, tzinfo=timezone.utc)
    report = WeatherReport(
        report_id="rep_tz_01",
        source="imd",
        source_type="official",
        timestamp=ts_utc,
        text="Timezone test UTC",
    )
    assert report.timestamp == ts_utc

    # Datetime with offset (+05:30) converted to UTC
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    ts_ist = datetime(2026, 9, 4, 16, 0, tzinfo=ist_tz)
    report_ist = WeatherReport(
        report_id="rep_tz_02",
        source="imd",
        source_type="official",
        timestamp=ts_ist,
        text="Timezone test IST",
    )
    assert report_ist.timestamp.tzinfo == timezone.utc
    assert report_ist.timestamp.hour == 10
    assert report_ist.timestamp.minute == 30

    # ISO string with UTC offset auto-parsed into UTC
    report_iso = WeatherReport(
        report_id="rep_tz_03",
        source="imd",
        source_type="official",
        timestamp="2026-09-04T10:30:00+00:00",
        text="Timezone test ISO string",
    )
    assert report_iso.timestamp.tzinfo == timezone.utc


def test_2_naive_timestamp_rejection():
    naive_dt = datetime(2026, 9, 4, 10, 30)  # Naive datetime without tzinfo
    with pytest.raises(ValidationError) as exc_info:
        WeatherReport(
            report_id="rep_err_naive",
            source="imd",
            source_type="official",
            timestamp=naive_dt,
            text="Naive timestamp test",
        )
    assert "timezone-aware" in str(exc_info.value)


def test_3_timezone_aware_received_at():
    # Timezone-aware received_at accepted
    recv_utc = datetime(2026, 9, 4, 10, 35, tzinfo=timezone.utc)
    report = WeatherReport(
        report_id="rep_recv_01",
        source="imd",
        source_type="official",
        timestamp="2026-09-04T10:30:00Z",
        received_at=recv_utc,
        text="Received at test",
    )
    assert report.received_at == recv_utc

    # Naive received_at rejected
    naive_recv = datetime(2026, 9, 4, 10, 35)
    with pytest.raises(ValidationError) as exc_info:
        WeatherReport(
            report_id="rep_recv_err",
            source="imd",
            source_type="official",
            timestamp="2026-09-04T10:30:00Z",
            received_at=naive_recv,
            text="Naive received_at test",
        )
    assert "timezone-aware" in str(exc_info.value)


def test_4_missing_coordinates_h3_remains_none():
    report = WeatherReport(
        report_id="rep_no_geo",
        source="citizen",
        source_type="citizen",
        timestamp="2026-09-04T10:30:00Z",
        text="No coords report",
        latitude=None,
        longitude=None,
    )
    assert report.latitude is None
    assert report.longitude is None
    assert report.h3_cell is None


def test_5_coordinates_h3_cell_derivation():
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


def test_6_invalid_and_inconsistent_supplied_h3_cell():
    import h3

    lat, lon = 28.627, 77.372
    correct_h3 = h3.latlng_to_cell(lat, lon, DEFAULT_H3_RESOLUTION)
    wrong_h3 = "873da1a93fffffd"

    # Supplying consistent h3_cell is accepted
    report_consistent = WeatherReport(
        report_id="rep_h3_ok",
        source="open_meteo",
        source_type="weather_api",
        timestamp="2026-09-04T10:00:00Z",
        text="Consistent H3 cell",
        latitude=lat,
        longitude=lon,
        h3_cell=correct_h3,
    )
    assert report_consistent.h3_cell == correct_h3

    # Supplying inconsistent h3_cell raises ValidationError
    with pytest.raises(ValidationError) as exc_info:
        WeatherReport(
            report_id="rep_h3_bad",
            source="open_meteo",
            source_type="weather_api",
            timestamp="2026-09-04T10:00:00Z",
            text="Inconsistent H3 cell",
            latitude=lat,
            longitude=lon,
            h3_cell=wrong_h3,
        )
    assert "does not match derived cell" in str(exc_info.value)

    # Supplying invalid h3_cell string without coordinates raises ValidationError
    with pytest.raises(ValidationError) as exc_info_invalid:
        WeatherReport(
            report_id="rep_h3_invalid_str",
            source="citizen",
            source_type="citizen",
            timestamp="2026-09-04T10:00:00Z",
            text="Invalid H3 string",
            h3_cell="invalid_h3_cell",
        )
    assert "not a valid H3 cell index" in str(exc_info_invalid.value)


def test_7_h3_derivation_failure_not_silently_swallowed():
    with patch("h3.latlng_to_cell", side_effect=RuntimeError("Simulated H3 C-library error")):
        with pytest.raises(ValidationError) as exc_info:
            WeatherReport(
                report_id="rep_h3_fail",
                source="open_meteo",
                source_type="weather_api",
                timestamp="2026-09-04T10:00:00Z",
                text="H3 derivation failure test",
                latitude=28.627,
                longitude=77.372,
            )
        assert "H3 cell derivation failed" in str(exc_info.value)


def test_8_unexpected_extra_fields_rejected():
    with pytest.raises(ValidationError) as exc_info:
        WeatherReport(
            report_id="rep_extra_01",
            source="imd",
            source_type="official",
            timestamp="2026-09-04T10:00:00Z",
            text="Extra field test",
            unregistered_custom_field="some_value",  # Should be forbidden
        )
    assert "Extra inputs are not permitted" in str(exc_info.value)

    # Raw payload is allowed for source provenance
    report_valid_raw = WeatherReport(
        report_id="rep_raw_ok",
        source="imd",
        source_type="official",
        timestamp="2026-09-04T10:00:00Z",
        text="Raw payload test",
        raw_payload={"unregistered_custom_field": "some_value"},
    )
    assert report_valid_raw.raw_payload == {"unregistered_custom_field": "some_value"}


def test_9_invalid_latitude_and_longitude_bounds():
    with pytest.raises(ValidationError):
        WeatherReport(
            report_id="rep_lat_err",
            source="test",
            source_type="test",
            timestamp="2026-09-04T10:00:00Z",
            text="Lat out of bounds",
            latitude=95.0,
            longitude=77.0,
        )

    with pytest.raises(ValidationError):
        WeatherReport(
            report_id="rep_lon_err",
            source="test",
            source_type="test",
            timestamp="2026-09-04T10:00:00Z",
            text="Lon out of bounds",
            latitude=28.0,
            longitude=-195.0,
        )


def test_10_media_items_and_extra_forbid():
    media = MediaItem(
        url="https://example.com/photo.jpg",
        media_type="image/jpeg",
        caption="Flood photo",
    )
    report = WeatherReport(
        report_id="rep_media_01",
        source="social",
        source_type="social_media",
        timestamp="2026-09-04T10:00:00Z",
        text="Flood photo report",
        media_items=[media],
    )
    assert len(report.media_items) == 1
    assert report.media_items[0].media_type == "image/jpeg"

    # Extra fields on MediaItem are forbidden
    with pytest.raises(ValidationError):
        MediaItem(
            url="https://example.com/photo.jpg",
            unknown_prop="forbidden",
        )


def test_11_serialization_and_deserialization():
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
    assert reconstructed.timestamp == report.timestamp
