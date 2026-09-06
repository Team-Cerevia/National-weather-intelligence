"""Comprehensive Unit Tests for Track C Intelligence Pipeline."""

from datetime import datetime, timedelta, timezone

from contracts.evidence import VerificationStatus
from contracts.weather_report import WeatherReport
from intelligence.incident_engine import IncidentEngine
from intelligence.nlp_extractor import NLPExtractor
from intelligence.orchestrator import IntelligenceOrchestrator


def test_nlp_extractor_event_classification():
    """Test 1: NLP Extractor correctly classifies weather event categories."""
    extractor = NLPExtractor()

    assert extractor.extract_event_category("Heavy rain and downpour in Delhi") == "RAIN"
    assert extractor.extract_event_category("Severe waterlogging near metro station") == "WATERLOGGING"
    assert extractor.extract_event_category("Massive flooding in Yamuna basin") == "FLOOD"
    assert extractor.extract_event_category("Extreme heatwave with loo winds") == "HEATWAVE"
    assert extractor.extract_event_category("Dense fog reducing visibility to 10 meters") == "FOG"
    assert extractor.extract_event_category("Random chatter about sports") == "OTHER"


def test_nlp_extractor_negation_detection():
    """Test 2: NLP Extractor detects negation and false alarms."""
    extractor = NLPExtractor()

    assert extractor.is_negated("No rain in Noida today") is True
    assert extractor.is_negated("False alarm regarding heatwave") is True
    assert extractor.is_negated("Clear sky after morning drizzle") is True
    assert extractor.is_negated("Heavy downpour inundating streets") is False


def test_nlp_extractor_metric_parsing():
    """Test 3: NLP Extractor parses quantitative metrics."""
    extractor = NLPExtractor()

    metrics = extractor.extract_metrics("Rainfall observed: 45.5 mm with wind speed 80 km/h and temp 32°C")
    assert metrics["rainfall_mm"] == 45.5
    assert metrics["wind_speed_kmh"] == 80.0
    assert metrics["temperature_c"] == 32.0


def test_nlp_onnx_embedding():
    """Test 3b: ONNX Embedding Engine generates normalized 384-d vectors."""
    extractor = NLPExtractor()
    embedding = extractor.compute_embedding("Heavy rainfall and storm in Mumbai")

    assert isinstance(embedding, list)
    assert len(embedding) == 384
    # Ensure non-zero normalized vector
    assert any(val != 0.0 for val in embedding)

    """Test 4: IncidentEngine correlates spatio-temporally proximate reports."""
    engine = IncidentEngine(time_window_hours=6.0)
    now = datetime.now(timezone.utc)

    report1 = WeatherReport(
        report_id="r1",
        source="imd",
        source_type="official",
        timestamp=now,
        text="Heavy rainfall alert in Delhi: 40mm observed",
        latitude=28.6139,
        longitude=77.2090,
        city="Delhi",
    )

    report2 = WeatherReport(
        report_id="r2",
        source="twitter",
        source_type="social_media",
        timestamp=now + timedelta(minutes=30),
        text="Waterlogging reported near Connaught Place Delhi after heavy rain",
        latitude=28.6250,
        longitude=77.2180,
        city="Delhi",
    )

    incidents = engine.correlate_reports([report1, report2])
    assert len(incidents) == 1
    incident = incidents[0]

    assert incident.event_category in ["RAIN", "WATERLOGGING", "FLOOD"]
    assert len(incident.report_ids) == 2
    assert "r1" in incident.report_ids
    assert "r2" in incident.report_ids


def test_incident_engine_spatial_separation():
    """Test 5: Reports far apart geographically (Delhi vs Mumbai) create separate incidents."""
    engine = IncidentEngine(time_window_hours=6.0)
    now = datetime.now(timezone.utc)

    r_delhi = WeatherReport(
        report_id="rd",
        source="imd",
        source_type="official",
        timestamp=now,
        text="Heavy rainfall in Delhi",
        latitude=28.6139,
        longitude=77.2090,
        city="Delhi",
    )

    r_mumbai = WeatherReport(
        report_id="rm",
        source="imd",
        source_type="official",
        timestamp=now,
        text="Heavy rainfall in Mumbai",
        latitude=19.0760,
        longitude=72.8777,
        city="Mumbai",
    )

    incidents = engine.correlate_reports([r_delhi, r_mumbai])
    assert len(incidents) == 2


def test_incident_engine_temporal_separation():
    """Test 6: Reports outside time window (> 6 hours) do not cluster into old incident."""
    engine = IncidentEngine(time_window_hours=6.0)
    now = datetime.now(timezone.utc)

    r_early = WeatherReport(
        report_id="re",
        source="imd",
        source_type="official",
        timestamp=now,
        text="Heavy rainfall in Delhi",
        latitude=28.6139,
        longitude=77.2090,
        city="Delhi",
    )

    r_late = WeatherReport(
        report_id="rl",
        source="imd",
        source_type="official",
        timestamp=now + timedelta(hours=12),
        text="Heavy rainfall in Delhi",
        latitude=28.6139,
        longitude=77.2090,
        city="Delhi",
    )

    incidents = engine.correlate_reports([r_early, r_late])
    assert len(incidents) == 2


def test_incident_engine_event_incompatibility():
    """Test 7: Incompatible events (HEATWAVE vs RAIN) at same location create separate incidents."""
    engine = IncidentEngine(time_window_hours=6.0)
    now = datetime.now(timezone.utc)

    r_rain = WeatherReport(
        report_id="r_rain",
        source="imd",
        source_type="official",
        timestamp=now,
        text="Heavy rainfall in Delhi",
        latitude=28.6139,
        longitude=77.2090,
        city="Delhi",
    )

    r_heat = WeatherReport(
        report_id="r_heat",
        source="imd",
        source_type="official",
        timestamp=now + timedelta(minutes=10),
        text="Extreme heatwave with loo in Delhi",
        latitude=28.6139,
        longitude=77.2090,
        city="Delhi",
    )

    incidents = engine.correlate_reports([r_rain, r_heat])
    assert len(incidents) == 2


def test_evidence_engine_provenance_scoring():
    """Test 8: EvidenceEngine calculates confidence score and evidence summary."""
    orchestrator = IntelligenceOrchestrator()
    now = datetime.now(timezone.utc)

    report_official = WeatherReport(
        report_id="r_official",
        source="imd",
        source_type="official",
        timestamp=now,
        text="Official IMD Heavy Rainfall Warning for Delhi NCR",
        latitude=28.6139,
        longitude=77.2090,
        city="Delhi",
    )

    report_social = WeatherReport(
        report_id="r_social",
        source="twitter",
        source_type="social_media",
        timestamp=now + timedelta(minutes=15),
        text="Streets flooded near Delhi metro! Heavy downpour!",
        latitude=28.6150,
        longitude=77.2100,
        city="Delhi",
    )

    incidents = orchestrator.process_reports([report_official, report_social])
    assert len(incidents) == 1

    incident = incidents[0]
    summary = incident.verification_summary

    assert summary is not None
    assert summary.verification_status == VerificationStatus.SUPPORTED
    assert summary.overall_confidence >= 0.70
    assert summary.supporting_count == 2
    assert summary.contradicting_count == 0
    assert "imd" in summary.supporting_sources
    assert len(summary.evidence_items) == 2


def test_evidence_engine_negation_contradiction():
    """Test 9: Contradicting/negated reports lower overall confidence score and mark evidence as CONTRADICTING."""
    now = datetime.now(timezone.utc)

    orchestrator = IntelligenceOrchestrator()
    r_support = WeatherReport(
        report_id="rs",
        source="twitter",
        source_type="social_media",
        timestamp=now,
        text="Heavy flooding in Delhi!",
        latitude=28.6139,
        longitude=77.2090,
    )
    r_contradict = WeatherReport(
        report_id="rc",
        source="twitter",
        source_type="social_media",
        timestamp=now + timedelta(minutes=5),
        text="Fake alert! No flood in Delhi, road is clear",
        latitude=28.6139,
        longitude=77.2090,
    )

    incidents = orchestrator.process_reports([r_support, r_contradict])
    assert len(incidents) == 1

    summary = incidents[0].verification_summary
    assert summary is not None
    assert summary.contradicting_count == 1
    assert summary.overall_confidence <= 0.50


def test_image_deduplication_and_phash():
    """Test 10: ImageDeduplicator correctly computes pHash and detects duplicate images."""
    from intelligence.vision.image_dedup import ImageDeduplicator

    # Duplicate exact or near-identical hashes
    hash1 = ImageDeduplicator.compute_phash("mock_image_data_stream_1")
    hash2 = ImageDeduplicator.compute_phash("mock_image_data_stream_1")
    hash3 = ImageDeduplicator.compute_phash("completely_different_image_stream_999")

    assert ImageDeduplicator.is_duplicate(hash1, hash2) is True
    assert ImageDeduplicator.is_duplicate(hash1, hash3) is False


def test_nlp_location_ner_extraction():
    """Test 11: NLPExtractor extracts location Named Entities (NER) from text."""
    extractor = NLPExtractor()

    locations1 = extractor.extract_locations_ner("Heavy waterlogging reported in Delhi and Gurgaon after downpour")
    assert "Delhi" in locations1 or "Gurgaon" in locations1

    locations2 = extractor.extract_locations_ner("Cyclonic storm approaching near Mumbai coastline")
    assert "Mumbai" in locations2
