from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from contracts.evidence import (
    EvidenceItem,
    EvidenceRelationship,
    VerificationStatus,
    VerificationSummary,
)


def test_1_valid_supporting_evidence_item():
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
    )

    assert ev.evidence_id == "ev_101"
    assert ev.report_id == "rep_901"
    assert ev.relationship == EvidenceRelationship.SUPPORTING
    assert ev.confidence_score == 0.95
    assert ev.source_reliability_weight == 1.0
    assert "radar rainfall" in ev.reasoning
    assert ev.media_proof_urls == ["https://imd.gov.in/radar/noida.png"]


def test_2_valid_contradicting_evidence_item():
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
    )

    assert ev.relationship == EvidenceRelationship.CONTRADICTING
    assert ev.extracted_event == "clear_sky"


def test_3_confidence_bounds_validation():
    # Unassigned scores default to None (avoiding hardcoded fake 1.0 assumptions)
    ev_unassigned = EvidenceItem(
        evidence_id="ev_none",
        report_id="rep_none",
        source="citizen",
        source_type="citizen",
        reasoning="Raw citizen report under review",
    )
    assert ev_unassigned.confidence_score is None
    assert ev_unassigned.source_reliability_weight is None

    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev_err",
            report_id="rep_1",
            source="test",
            source_type="test",
            confidence_score=1.5,  # Out of range > 1.0
            reasoning="Test invalid confidence",
        )

    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev_err2",
            report_id="rep_1",
            source="test",
            source_type="test",
            confidence_score=-0.1,  # Out of range < 0.0
            reasoning="Test invalid confidence",
        )



def test_4_verification_summary_aggregation():
    ev1 = EvidenceItem(
        evidence_id="ev_1",
        report_id="rep_1",
        source="imd",
        source_type="official",
        relationship=EvidenceRelationship.SUPPORTING,
        confidence_score=0.95,
        reasoning="IMD rain gauge recording",
    )
    ev2 = EvidenceItem(
        evidence_id="ev_2",
        report_id="rep_2",
        source="citizen",
        source_type="citizen",
        relationship=EvidenceRelationship.SUPPORTING,
        confidence_score=0.80,
        reasoning="Citizen photo showing flooded street",
        media_proof_urls=["https://example.com/photo.jpg"],
    )

    summary = VerificationSummary(
        verification_status=VerificationStatus.VERIFIED,
        overall_confidence=0.88,
        supporting_count=2,
        contradicting_count=0,
        supporting_sources=["imd", "citizen"],
        contradicting_sources=[],
        evidence_items=[ev1, ev2],
        explanation="Verified by 1 official weather station reading and 1 geotagged citizen photo.",
    )

    assert summary.verification_status == VerificationStatus.VERIFIED
    assert summary.overall_confidence == 0.88
    assert summary.supporting_count == 2
    assert len(summary.evidence_items) == 2
    assert "official weather station" in summary.explanation

    # Uncalculated summary defaults overall_confidence to None
    summary_default = VerificationSummary()
    assert summary_default.overall_confidence is None



def test_5_verification_summary_serialization():
    ev = EvidenceItem(
        evidence_id="ev_serde",
        report_id="rep_100",
        source="x",
        source_type="social_media",
        relationship=EvidenceRelationship.CORROBORATING,
        confidence_score=0.75,
        reasoning="Multiple tweets mention waterlogging at Sector 62 metro station.",
    )
    summary = VerificationSummary(
        verification_status=VerificationStatus.SUPPORTED,
        overall_confidence=0.75,
        supporting_count=1,
        supporting_sources=["x"],
        evidence_items=[ev],
        explanation="Corroborated by social media trend.",
    )

    json_str = summary.model_dump_json()
    reconstructed = VerificationSummary.model_validate_json(json_str)

    assert reconstructed.verification_status == VerificationStatus.SUPPORTED
    assert reconstructed.overall_confidence == 0.75
    assert len(reconstructed.evidence_items) == 1
    assert reconstructed.evidence_items[0].evidence_id == "ev_serde"
