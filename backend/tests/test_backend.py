"""Unit tests for backend persistence layer, database models, and session configuration."""

import os
from datetime import datetime, timezone

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from backend.db.models import (
    GeometryPoint,
    IncidentModel,
    ReportModel,
)
from backend.db.session import Base, get_database_url
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
from contracts.weather_report import MediaItem, WeatherReport


def test_database_url_configuration() -> None:
    """Verify get_database_url uses environment variable or defaults to development postgres."""
    default_url = get_database_url()
    assert "postgresql+psycopg://" in default_url
    assert "weather_user" in default_url
    assert "weather_db" in default_url

    custom_url = "postgresql://my_user:my_pwd@db.host.internal:5433/prod_weather"
    old_env = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = custom_url
        resolved = get_database_url()
        assert resolved == "postgresql+psycopg://my_user:my_pwd@db.host.internal:5433/prod_weather"
    finally:
        if old_env is not None:
            os.environ["DATABASE_URL"] = old_env
        else:
            os.environ.pop("DATABASE_URL", None)


def test_geometry_point_processor() -> None:
    """Verify PostGIS geometry type bind processor formats WKT coordinates with SRID 4326."""
    geom = GeometryPoint()
    assert geom.get_col_spec() == "geometry(Point, 4326)"

    binder = geom.bind_processor(postgresql.dialect())
    assert binder(None) is None
    assert binder((77.25, 28.625)) == "SRID=4326;POINT(77.25 28.625)"
    assert binder("SRID=4326;POINT(77.25 28.625)") == "SRID=4326;POINT(77.25 28.625)"


def test_report_model_bidirectional_contract_mapping() -> None:
    """Verify WeatherReport <-> ReportModel round-trip preserves all canonical fields."""
    ts_utc = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    recv_utc = datetime(2026, 9, 4, 10, 2, tzinfo=timezone.utc)

    media = MediaItem(url="https://example.com/flood.jpg", media_type="image/jpeg", caption="Flood water")
    report = WeatherReport(
        report_id="rep_noida_001",
        source="imd",
        source_type="official",
        source_id="imd_alert_882",
        timestamp=ts_utc,
        received_at=recv_utc,
        text="Heavy rainfall alert in Noida",
        latitude=28.627,
        longitude=77.372,
        city="Noida",
        district="Gautam Buddha Nagar",
        state="Uttar Pradesh",
        country="India",
        event_category="RAIN",
        url="https://imd.gov.in/bulletin/882",
        media_urls=["https://example.com/flood.jpg"],
        media_items=[media],
        hashtags=["#NoidaRain", "#IMD"],
        language="en",
        raw_payload={"radar_intensity": 45.5},
        schema_version="1.0",
    )

    model = ReportModel.from_contract(report)
    assert model.report_id == "rep_noida_001"
    assert model.source == "imd"
    assert model.source_type == "official"
    assert model.source_id == "imd_alert_882"
    assert model.timestamp == ts_utc
    assert model.received_at == recv_utc
    assert model.latitude == 28.627
    assert model.longitude == 77.372
    assert model.location == "SRID=4326;POINT(77.372 28.627)"
    assert model.h3_cell == report.h3_cell
    assert model.city == "Noida"
    assert model.district == "Gautam Buddha Nagar"
    assert model.state == "Uttar Pradesh"
    assert len(model.media_items) == 1
    assert model.hashtags == ["#NoidaRain", "#IMD"]

    restored = model.to_contract()
    assert restored == report


def test_incident_model_bidirectional_contract_mapping() -> None:
    """Verify Incident <-> IncidentModel round-trip preserves all provenance and timeline fields."""
    ts_now = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    ts_update = datetime(2026, 9, 4, 10, 30, tzinfo=timezone.utc)

    ev = EvidenceItem(
        evidence_id="ev_001",
        report_id="rep_noida_001",
        source="imd",
        source_type="official",
        relationship=EvidenceRelationship.SUPPORTING,
        confidence_score=0.95,
        source_reliability_weight=1.0,
        reasoning="Radar rain gauge measurement of 45mm/hr",
        extracted_event="heavy_rain",
        extracted_location="Noida",
        media_proof_urls=["https://example.com/proof.jpg"],
        timestamp=ts_now,
    )

    summary = VerificationSummary(
        verification_status=VerificationStatus.VERIFIED,
        overall_confidence=0.92,
        supporting_count=1,
        contradicting_count=0,
        supporting_sources=["imd"],
        contradicting_sources=[],
        evidence_items=[ev],
        explanation="Verified by IMD radar station",
        updated_at=ts_update,
    )

    timeline_entry = IncidentTimeline(
        timestamp=ts_now,
        event_type="created",
        description="Incident created from IMD alert",
        previous_state=None,
        new_state=IncidentState.REPORTED,
        previous_severity=None,
        new_severity=IncidentSeverity.HIGH,
        report_id="rep_noida_001",
    )

    incident = Incident(
        incident_id="inc_delhi_flood_01",
        title="Severe Waterlogging in Noida Sector 62",
        event_category="FLOOD",
        state=IncidentState.VERIFIED,
        severity=IncidentSeverity.HIGH,
        priority_score=88.5,
        latitude=28.627,
        longitude=77.372,
        h3_cells=["873da1a93ffffff"],
        city="Noida",
        district="Gautam Buddha Nagar",
        state_name="Uttar Pradesh",
        country="India",
        first_reported_at=ts_now,
        last_updated_at=ts_update,
        report_ids=["rep_noida_001"],
        verification_summary=summary,
        timeline=[timeline_entry],
    )

    model = IncidentModel.from_contract(incident)
    assert model.incident_id == "inc_delhi_flood_01"
    assert model.title == "Severe Waterlogging in Noida Sector 62"
    assert model.event_category == "FLOOD"
    assert model.state == "VERIFIED"
    assert model.severity == "HIGH"
    assert model.priority_score == 88.5
    assert model.state_name == "Uttar Pradesh"
    assert model.location == "SRID=4326;POINT(77.372 28.627)"
    assert model.verification_status == "VERIFIED"
    assert model.overall_confidence == 0.92
    assert len(model.evidence_items) == 1
    assert len(model.timeline) == 1

    restored = model.to_contract()
    assert restored == incident


def test_postgresql_postgis_ddl_compilation() -> None:
    """Verify SQLAlchemy compiles valid PostgreSQL DDL with PostGIS geometry and GiST indexes."""
    pg_dialect = postgresql.dialect()

    # Verify incidents table DDL
    inc_ddl = str(CreateTable(IncidentModel.__table__).compile(dialect=pg_dialect))
    assert "CREATE TABLE incidents" in inc_ddl
    assert "location geometry(Point, 4326)" in inc_ddl
    assert "first_reported_at TIMESTAMP WITH TIME ZONE" in inc_ddl
    assert "PRIMARY KEY (incident_id)" in inc_ddl

    # Verify reports table DDL
    rep_ddl = str(CreateTable(ReportModel.__table__).compile(dialect=pg_dialect))
    assert "CREATE TABLE reports" in rep_ddl
    assert "location geometry(Point, 4326)" in rep_ddl
    assert "timestamp TIMESTAMP WITH TIME ZONE" in rep_ddl
    assert "PRIMARY KEY (report_id)" in rep_ddl

    # Verify GiST indexes
    inc_indexes = [str(CreateIndex(idx).compile(dialect=pg_dialect)) for idx in IncidentModel.__table__.indexes]
    assert any("USING gist (location)" in sql for sql in inc_indexes)

    rep_indexes = [str(CreateIndex(idx).compile(dialect=pg_dialect)) for idx in ReportModel.__table__.indexes]
    assert any("USING gist (location)" in sql for sql in rep_indexes)

    # Verify foreign key relationships in sorted tables
    sorted_table_names = [t.name for t in Base.metadata.sorted_tables]
    assert sorted_table_names.index("incidents") < sorted_table_names.index("evidence_items")
    assert sorted_table_names.index("incidents") < sorted_table_names.index("incident_timeline")
