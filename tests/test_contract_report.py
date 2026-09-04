from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest
from pydantic import ValidationError

from contracts.weather_report import MediaItem, WeatherReport, DEFAULT_H3_RESOLUTION


def test_1_timezone_aware_timestamp_acceptance():
    ts_utc = datetime(2026, 9, 4, 10, 30, tzinfo=timezone.utc)
    report = WeatherReport(
        report_id="rep_tz_01",
        source="imd",
        source_type="official",
        timestamp=ts_utc,
        text="Timezone test UTC",
    )
    assert report.timestamp == ts_utc

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

    report_iso = WeatherReport(
        report_id="rep_tz_03",
        source="imd",
        source_type="official",
        timestamp="2026-09-04T10:30:00+00:00",
        text="Timezone test ISO string",
    )
    assert report_iso.timestamp.tzinfo == timezone.utc


def test_2_naive_timestamp_rejection():
    naive_dt = datetime(2026, 9, 4, 10, 30)
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


def test_4_missing_coords_and_missing_h3_accepted():
    # Invariant 4: latitude/longitude absent + h3_cell absent -> accept
    report = WeatherReport(
        report_id="rep_no_geo",
        source="citizen",
        source_type="citizen",
        timestamp="2026-09-04T10:30:00Z",
        text="No coords report",
        latitude=None,
        longitude=None,
        h3_cell=None,
    )
    assert report.latitude is None
    assert report.longitude is None
    assert report.h3_cell is None


def test_5_standalone_h3_cell_without_coordinates_rejected():
    # Invariant 5: latitude/longitude absent + h3_cell present -> reject
    import h3

    valid_cell_res7 = h3.latlng_to_cell(28.627, 77.372, 7)
    with pytest.raises(ValidationError) as exc_info:
        WeatherReport(
            report_id="rep_standalone_h3",
            source="citizen",
            source_type="citizen",
            timestamp="2026-09-04T10:30:00Z",
            text="Standalone H3 without lat/lon",
            latitude=None,
            longitude=None,
            h3_cell=valid_cell_res7,
        )
    assert "Standalone h3_cell without coordinates is forbidden" in str(exc_info.value)


def test_6_coordinates_h3_cell_auto_derivation():
    # Invariant 1: latitude + longitude present + h3_cell absent -> auto derive h3_cell
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


def test_7_matching_h3_cell_accepted():
    # Invariant 2: latitude + longitude present + matching h3_cell -> accept
    import h3

    lat, lon = 28.627, 77.372
    correct_h3 = h3.latlng_to_cell(lat, lon, DEFAULT_H3_RESOLUTION)

    report = WeatherReport(
        report_id="rep_h3_match",
        source="open_meteo",
        source_type="weather_api",
        timestamp="2026-09-04T10:00:00Z",
        text="Matching H3 report",
        latitude=lat,
        longitude=lon,
        h3_cell=correct_h3,
    )
    assert report.h3_cell == correct_h3


def test_8_mismatching_h3_cell_rejected():
    # Invariant 3: latitude + longitude present + mismatching h3_cell -> reject
    import h3

    lat, lon = 28.627, 77.372
    wrong_h3 = h3.latlng_to_cell(19.076, 72.877, 7)  # Mumbai H3 cell instead of Noida

    with pytest.raises(ValidationError) as exc_info:
        WeatherReport(
            report_id="rep_h3_mismatch",
            source="open_meteo",
            source_type="weather_api",
            timestamp="2026-09-04T10:00:00Z",
            text="Mismatching H3 report",
            latitude=lat,
            longitude=lon,
            h3_cell=wrong_h3,
        )
    assert "does not match derived cell" in str(exc_info.value)


def test_9_h3_resolution_other_than_7_rejected():
    # Invariant 6: supplied H3 at resolution other than 7 -> reject
    import h3

    lat, lon = 28.627, 77.372
    h3_res_8 = h3.latlng_to_cell(lat, lon, 8)  # Resolution 8 cell

    with pytest.raises(ValidationError) as exc_info:
        WeatherReport(
            report_id="rep_h3_res8",
            source="open_meteo",
            source_type="weather_api",
            timestamp="2026-09-04T10:00:00Z",
            text="Resolution 8 H3 report",
            latitude=lat,
            longitude=lon,
            h3_cell=h3_res_8,
        )
    assert "has resolution 8, but resolution 7 is required" in str(exc_info.value)


def test_10_h3_derivation_failure_not_silently_swallowed():
    with patch("h3.latlng_to_cell", side_effect=RuntimeError("C-library error")):
        with pytest.raises(ValidationError) as exc_info:
            WeatherReport(
                report_id="rep_h3_fail",
                source="open_meteo",
                source_type="weather_api",
                timestamp="2026-09-04T10:00:00Z",
                text="H3 failure test",
                latitude=28.627,
                longitude=77.372,
            )
        assert "H3 cell derivation failed" in str(exc_info.value)


def test_11_unexpected_extra_fields_rejected():
    with pytest.raises(ValidationError) as exc_info:
        WeatherReport(
            report_id="rep_extra_01",
            source="imd",
            source_type="official",
            timestamp="2026-09-04T10:00:00Z",
            text="Extra field test",
            unregistered_field="forbidden",
        )
    assert "Extra inputs are not permitted" in str(exc_info.value)


def test_12_serialization_and_deserialization():
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
    assert reconstructed.h3_cell == report.h3_cell
    assert reconstructed.timestamp == report.timestamp
