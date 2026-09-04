from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError

from contracts.evidence import (
    EvidenceItem,
    EvidenceRelationship,
    VerificationStatus,
    VerificationSummary,
)


def test_1_valid_supporting_evidence_item():
    ts_utc = datetime(2026, 9, 4, 10, 30, tzinfo=timezone.utc)
    ev = EvidenceItem(
        evidence_id="ev_101",
        report_id="rep_901",
        source="imd",
        source_type="official",
        relationship=EvidenceRelationship.SUPPORTING,
        confidence_score=0.95,
        source_reliability_weight=1.0,
        reasoning="Official IMD radar rainfall data confirms 45mm/hr precipitation in Noida Sector 62.",
        extracted_event="heavy_rain",
        extracted_location="Noida",
        media_proof_urls=["https://imd.gov.in/radar/noida.png"],
        timestamp=ts_utc,
    )

    assert ev.evidence_id == "ev_101"
    assert ev.report_id == "rep_901"
    assert ev.relationship == EvidenceRelationship.SUPPORTING
    assert ev.confidence_score == 0.95
    assert ev.source_reliability_weight == 1.0
    assert "radar rainfall" in ev.reasoning
    assert ev.timestamp == ts_utc


def test_2_valid_contradicting_evidence_item():
    ts_utc = datetime(2026, 9, 4, 10, 32, tzinfo=timezone.utc)
    ev = EvidenceItem(
        evidence_id="ev_102",
        report_id="rep_902",
        source="open_meteo",
        source_type="weather_api",
        relationship=EvidenceRelationship.CONTRADICTING,
        confidence_score=0.90,
        source_reliability_weight=0.9,
        reasoning="Open-Meteo API reports 0.0mm precipitation at coordinates (28.6, 77.3).",
        extracted_event="clear_sky",
        extracted_location="Noida",
        timestamp=ts_utc,
    )

    assert ev.relationship == EvidenceRelationship.CONTRADICTING
    assert ev.extracted_event == "clear_sky"


def test_3_naive_timestamp_rejection():
    naive_ts = datetime(2026, 9, 4, 10, 30)  # Naive datetime
    with pytest.raises(ValidationError) as exc_info:
        EvidenceItem(
            evidence_id="ev_naive",
            report_id="rep_1",
            source="test",
            source_type="test",
            reasoning="Naive timestamp test",
            timestamp=naive_ts,
        )
    assert "timezone-aware" in str(exc_info.value)


def test_4_timezone_aware_timestamp_normalization_to_utc():
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    ts_ist = datetime(2026, 9, 4, 16, 0, tzinfo=ist_tz)

    ev = EvidenceItem(
        evidence_id="ev_tz_norm",
        report_id="rep_1",
        source="test",
        source_type="test",
        reasoning="Timezone normalization test",
        timestamp=ts_ist,
    )

    assert ev.timestamp.tzinfo == timezone.utc
    assert ev.timestamp.hour == 10
    assert ev.timestamp.minute == 30


def test_5_extra_fields_rejected_extra_forbid():
    ts_utc = datetime(2026, 9, 4, 10, 30, tzinfo=timezone.utc)
    with pytest.raises(ValidationError) as exc_info:
        EvidenceItem(
            evidence_id="ev_extra",
            report_id="rep_1",
            source="test",
            source_type="test",
            reasoning="Extra field test",
            timestamp=ts_utc,
            forbidden_field="invalid_extra",  # Extra field
        )
    assert "Extra inputs are not permitted" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_summary_extra:
        VerificationSummary(
            forbidden_summary_field="invalid_extra",
        )
    assert "Extra inputs are not permitted" in str(exc_summary_extra.value)


def test_6_confidence_and_source_reliability_bounds_validation():
    ts_utc = datetime(2026, 9, 4, 10, 30, tzinfo=timezone.utc)

    # confidence_score out of bounds (> 1.0)
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev_err_conf1",
            report_id="rep_1",
            source="test",
            source_type="test",
            confidence_score=1.5,
            reasoning="Test invalid confidence",
            timestamp=ts_utc,
        )

    # confidence_score out of bounds (< 0.0)
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev_err_conf2",
            report_id="rep_1",
            source="test",
            source_type="test",
            confidence_score=-0.1,
            reasoning="Test invalid confidence",
            timestamp=ts_utc,
        )

    # source_reliability_weight out of bounds (> 1.0)
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev_err_rel1",
            report_id="rep_1",
            source="test",
            source_type="test",
            source_reliability_weight=1.2,
            reasoning="Test invalid reliability",
            timestamp=ts_utc,
        )

    # source_reliability_weight out of bounds (< 0.0)
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev_err_rel2",
            report_id="rep_1",
            source="test",
            source_type="test",
            source_reliability_weight=-0.2,
            reasoning="Test invalid reliability",
            timestamp=ts_utc,
        )


def test_7_none_confidence_distinguishable_from_zero():
    ts_utc = datetime(2026, 9, 4, 10, 30, tzinfo=timezone.utc)

    # Unassigned confidence remains None
    ev_none = EvidenceItem(
        evidence_id="ev_none",
        report_id="rep_1",
        source="test",
        source_type="test",
        reasoning="Unassigned score test",
        timestamp=ts_utc,
    )
    assert ev_none.confidence_score is None
    assert ev_none.source_reliability_weight is None

    # Zero confidence score is explicitly 0.0
    ev_zero = EvidenceItem(
        evidence_id="ev_zero",
        report_id="rep_1",
        source="test",
        source_type="test",
        confidence_score=0.0,
        source_reliability_weight=0.0,
        reasoning="Zero score test",
        timestamp=ts_utc,
    )
    assert ev_zero.confidence_score == 0.0
    assert ev_zero.source_reliability_weight == 0.0
    assert ev_none.confidence_score != ev_zero.confidence_score


def test_8_verification_summary_defaults_and_aggregation():
    ts_utc = datetime(2026, 9, 4, 10, 30, tzinfo=timezone.utc)
    ev1 = EvidenceItem(
        evidence_id="ev_1",
        report_id="rep_1",
        source="imd",
        source_type="official",
        relationship=EvidenceRelationship.SUPPORTING,
        confidence_score=0.95,
        reasoning="IMD rain gauge recording",
        timestamp=ts_utc,
    )

    # VerificationSummary defaults
    summary_default = VerificationSummary()
    assert summary_default.verification_status == VerificationStatus.UNVERIFIED
    assert summary_default.overall_confidence is None
    assert summary_default.supporting_count == 0
    assert summary_default.contradicting_count == 0
    assert summary_default.evidence_items == []

    # Populated VerificationSummary
    summary = VerificationSummary(
        verification_status=VerificationStatus.VERIFIED,
        overall_confidence=0.88,
        supporting_count=1,
        supporting_sources=["imd"],
        evidence_items=[ev1],
        explanation="Verified by IMD station.",
    )
    assert summary.verification_status == VerificationStatus.VERIFIED
    assert summary.overall_confidence == 0.88
    assert summary.supporting_count == 1
    assert len(summary.evidence_items) == 1
