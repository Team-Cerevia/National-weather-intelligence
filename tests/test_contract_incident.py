from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from contracts.evidence import (
    EvidenceItem,
    EvidenceRelationship,
    VerificationStatus,
    VerificationSummary,
)
from contracts.incident import (
    Incident,
    IncidentSeverity,
    IncidentState,
    IncidentTimeline,
)


def test_1_valid_complete_incident():
    ev = EvidenceItem(
        evidence_id="ev_001",
        report_id="rep_001",
        source="imd",
        source_type="official",
        relationship=EvidenceRelationship.SUPPORTING,
        confidence_score=0.95,
        reasoning="Official IMD radar rainfall confirmation",
        timestamp=datetime(2026, 9, 4, 10, 30, tzinfo=timezone.utc),
    )

    summary = VerificationSummary(
        verification_status=VerificationStatus.VERIFIED,
        overall_confidence=0.92,
        supporting_count=1,
        supporting_sources=["imd"],
        evidence_items=[ev],
        explanation="Verified by IMD weather station",
    )
    timeline_entry = IncidentTimeline(
        event_type="created",
        description="Incident formed from initial IMD alert",
        new_state=IncidentState.REPORTED,
        new_severity=IncidentSeverity.HIGH,
        report_id="rep_001",
    )

    incident = Incident(
        incident_id="inc_noida_flood_01",
        title="Severe Flooding in Noida Sector 62",
        event_category="FLOOD",
        state=IncidentState.VERIFIED,
        severity=IncidentSeverity.HIGH,
        priority_score=85.5,
        latitude=28.627,
        longitude=77.372,
        h3_cells=["873da1a93ffffff"],
        city="Noida",
        district="Gautam Buddha Nagar",
        state_name="Uttar Pradesh",
        report_ids=["rep_001", "rep_002"],
        verification_summary=summary,
        timeline=[timeline_entry],
    )

    assert incident.incident_id == "inc_noida_flood_01"
    assert incident.event_category == "FLOOD"
    assert incident.state == IncidentState.VERIFIED
    assert incident.severity == IncidentSeverity.HIGH
    assert incident.priority_score == 85.5
    assert len(incident.h3_cells) == 1
    assert len(incident.report_ids) == 2
    assert incident.verification_summary.verification_status == VerificationStatus.VERIFIED
    assert len(incident.timeline) == 1


def test_2_minimal_valid_incident():
    incident = Incident(
        incident_id="inc_min_01",
        title="Heavy Rain Reported",
        event_category="RAIN",
    )

    assert incident.incident_id == "inc_min_01"
    assert incident.state == IncidentState.REPORTED
    assert incident.severity == IncidentSeverity.MODERATE
    assert incident.priority_score is None
    assert incident.latitude is None
    assert incident.longitude is None
    assert incident.h3_cells == []
    assert incident.report_ids == []
    assert incident.verification_summary is None
    assert incident.timeline == []


def test_3_incident_state_transitions():
    timeline = [
        IncidentTimeline(
            event_type="created",
            description="Initial report",
            new_state=IncidentState.REPORTED,
        ),
        IncidentTimeline(
            event_type="state_change",
            description="Multi-source verification completed",
            previous_state=IncidentState.REPORTED,
            new_state=IncidentState.VERIFIED,
        ),
    ]

    incident = Incident(
        incident_id="inc_state_01",
        title="Thunderstorm Alert",
        event_category="THUNDERSTORM",
        state=IncidentState.VERIFIED,
        timeline=timeline,
    )

    assert incident.state == IncidentState.VERIFIED
    assert len(incident.timeline) == 2
    assert incident.timeline[1].previous_state == IncidentState.REPORTED
    assert incident.timeline[1].new_state == IncidentState.VERIFIED


def test_4_priority_score_bounds_validation():
    with pytest.raises(ValidationError):
        Incident(
            incident_id="inc_err_score",
            title="Score Test",
            event_category="RAIN",
            priority_score=150.0,  # Invalid > 100
        )

    with pytest.raises(ValidationError):
        Incident(
            incident_id="inc_err_score2",
            title="Score Test",
            event_category="RAIN",
            priority_score=-5.0,  # Invalid < 0
        )


def test_5_incident_serialization_deserialization():
    incident = Incident(
        incident_id="inc_serde_01",
        title="Heatwave Warning",
        event_category="HEATWAVE",
        state=IncidentState.ESCALATING,
        severity=IncidentSeverity.CRITICAL,
        priority_score=95.0,
        city="Delhi",
        state_name="Delhi",
    )

    json_str = incident.model_dump_json()
    reconstructed = Incident.model_validate_json(json_str)

    assert reconstructed.incident_id == incident.incident_id
    assert reconstructed.title == incident.title
    assert reconstructed.state == IncidentState.ESCALATING
    assert reconstructed.severity == IncidentSeverity.CRITICAL
    assert reconstructed.priority_score == 95.0
    assert reconstructed.city == "Delhi"


def test_6_valid_h3_cells_accepted():
    incident = Incident(
        incident_id="inc_h3_valid",
        title="Valid H3 Cells Test",
        event_category="RAIN",
        h3_cells=["873da1a93ffffff"],
    )
    assert incident.h3_cells == ["873da1a93ffffff"]


def test_7_invalid_h3_cell_rejected():
    with pytest.raises(ValidationError):
        Incident(
            incident_id="inc_h3_invalid",
            title="Invalid H3 Cell Test",
            event_category="RAIN",
            h3_cells=["not_a_valid_h3_cell"],
        )


def test_8_wrong_h3_resolution_rejected():
    with pytest.raises(ValidationError):
        Incident(
            incident_id="inc_h3_wrong_res",
            title="Wrong H3 Res Test",
            event_category="RAIN",
            h3_cells=["863da1a97ffffff"],  # Resolution 6 cell
        )


def test_9_partial_coordinates_rejected():
    with pytest.raises(ValidationError):
        Incident(
            incident_id="inc_partial_lat",
            title="Partial Coords Test",
            event_category="FLOOD",
            latitude=28.627,
            longitude=None,
        )

    with pytest.raises(ValidationError):
        Incident(
            incident_id="inc_partial_lon",
            title="Partial Coords Test",
            event_category="FLOOD",
            latitude=None,
            longitude=77.372,
        )


def test_10_both_coordinates_absent_accepted():
    incident = Incident(
        incident_id="inc_no_coords",
        title="No Coords Test",
        event_category="FOG",
        latitude=None,
        longitude=None,
    )
    assert incident.latitude is None
    assert incident.longitude is None


def test_11_both_coordinates_present_accepted():
    incident = Incident(
        incident_id="inc_with_coords",
        title="With Coords Test",
        event_category="CYCLONE",
        latitude=13.0827,
        longitude=80.2707,
    )
    assert incident.latitude == 13.0827
    assert incident.longitude == 80.2707


def test_12_invalid_temporal_ordering_rejected():
    with pytest.raises(ValidationError):
        Incident(
            incident_id="inc_temporal_err",
            title="Invalid Temporal Ordering Test",
            event_category="HEATWAVE",
            first_reported_at=datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc),
            last_updated_at=datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc),  # earlier than first_reported_at
        )


def test_13_valid_temporal_ordering_accepted():
    t1 = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    incident = Incident(
        incident_id="inc_temporal_ok",
        title="Valid Temporal Ordering Test",
        event_category="HEATWAVE",
        first_reported_at=t1,
        last_updated_at=t2,
    )
    assert incident.first_reported_at == t1
    assert incident.last_updated_at == t2


def test_14_timezone_normalization():
    # Naive datetime should be rejected
    with pytest.raises(ValidationError):
        Incident(
            incident_id="inc_tz_naive",
            title="Naive Time Test",
            event_category="RAIN",
            first_reported_at=datetime(2026, 9, 4, 10, 0),  # Naive
        )

    # IST datetime (UTC+5:30) should be normalized to UTC
    from datetime import timedelta
    from datetime import timezone as tz

    ist = tz(timedelta(hours=5, minutes=30))
    t_ist = datetime(2026, 9, 4, 15, 30, tzinfo=ist)
    incident = Incident(
        incident_id="inc_tz_ist",
        title="IST Time Test",
        event_category="RAIN",
        first_reported_at=t_ist,
        last_updated_at=t_ist,
    )
    assert incident.first_reported_at == datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    assert incident.first_reported_at.tzinfo == timezone.utc

