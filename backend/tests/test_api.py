"""Integration tests for FastAPI REST API endpoints with PostgreSQL and PostGIS."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select, text
from starlette.testclient import TestClient

from backend.db.models import EvidenceItemModel, IncidentModel, ReportModel
from backend.db.session import SessionLocal, engine, init_db
from backend.main import app
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
from contracts.weather_report import WeatherReport


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database schema is ready before running API integration tests."""
    init_db(engine)


@pytest.fixture(autouse=True)
def clean_database():
    """Clean all tables between tests to ensure complete test isolation."""
    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE TABLE incident_timeline, evidence_items, incidents, reports RESTART IDENTITY CASCADE;")
        )
    yield


@pytest.fixture
def client():
    """FastAPI TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


def _make_sample_report(report_id: str = "test_rep_001", lat: float = 28.627, lon: float = 77.372) -> WeatherReport:
    """Helper creating a valid canonical WeatherReport."""
    return WeatherReport(
        report_id=report_id,
        source="imd",
        source_type="official",
        source_id="imd_alert_101",
        timestamp=datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc),
        text="Heavy precipitation observed across Noida Sector 62",
        latitude=lat,
        longitude=lon,
        city="Noida",
        district="Gautam Buddha Nagar",
        state="Uttar Pradesh",
        country="India",
        event_category="RAIN",
    )


def _make_sample_incident(
    incident_id: str = "test_inc_001",
    title: str = "Flash Flood in Noida",
    category: str = "RAIN",
    sev: IncidentSeverity = IncidentSeverity.HIGH,
    status: VerificationStatus = VerificationStatus.VERIFIED,
    dt: datetime | None = None,
    lat: float = 28.627,
    lon: float = 77.372,
    city: str = "Noida",
    state_name: str = "Uttar Pradesh",
) -> Incident:
    """Helper creating a valid canonical Incident with evidence and timeline."""
    ts = dt or datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    ev = EvidenceItem(
        evidence_id=f"ev_{incident_id}",
        report_id=f"rep_{incident_id}",
        source="imd",
        source_type="official",
        relationship=EvidenceRelationship.SUPPORTING,
        confidence_score=0.92,
        source_reliability_weight=0.98,
        reasoning="Consistent radar rain gauge measurements exceeding 50mm/hr",
        timestamp=ts,
    )
    summary = VerificationSummary(
        verification_status=status,
        overall_confidence=0.91,
        supporting_count=1,
        contradicting_count=0,
        supporting_sources=["imd"],
        contradicting_sources=[],
        evidence_items=[ev],
        explanation="Verified by multi-station radar",
        updated_at=ts,
    )
    timeline_entry = IncidentTimeline(
        timestamp=ts,
        event_type="created",
        description="Incident formed from alert",
        new_state=IncidentState.REPORTED,
        new_severity=sev,
    )
    return Incident(
        incident_id=incident_id,
        title=title,
        event_category=category,
        state=IncidentState.REPORTED,
        severity=sev,
        priority_score=85.0,
        latitude=lat,
        longitude=lon,
        city=city,
        district="District 1",
        state_name=state_name,
        country="India",
        first_reported_at=ts,
        last_updated_at=ts,
        report_ids=[f"rep_{incident_id}"],
        verification_summary=summary,
        timeline=[timeline_entry],
    )


# =====================================================================
# REPORTS ENDPOINT TESTS
# =====================================================================


def test_post_report_creates_new_report(client: TestClient):
    """POST /api/v1/reports creates new report in PostgreSQL with PostGIS location."""
    report = _make_sample_report()
    payload = report.model_dump(mode="json")

    resp = client.post("/api/v1/reports", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["report_id"] == report.report_id
    assert data["source"] == "imd"
    assert data["latitude"] == report.latitude
    assert data["longitude"] == report.longitude
    assert data["h3_cell"] == report.h3_cell

    # Verify directly in PostgreSQL
    with engine.connect() as conn:
        row = conn.execute(
            select(ReportModel.report_id, ReportModel.city).where(ReportModel.report_id == report.report_id)
        ).fetchone()
        assert row is not None
        assert row.report_id == report.report_id
        assert row.city == "Noida"


def test_post_report_upsert_idempotent(client: TestClient):
    """POST /api/v1/reports with existing ID updates the report without creating duplicates."""
    report = _make_sample_report()
    client.post("/api/v1/reports", json=report.model_dump(mode="json"))

    # Update report text and re-post
    updated_report = report.model_copy(update={"text": "Updated heavy rainfall report with localized flooding."})
    resp = client.post("/api/v1/reports", json=updated_report.model_dump(mode="json"))
    assert resp.status_code == 201
    assert resp.json()["text"] == "Updated heavy rainfall report with localized flooding."

    # Verify single record in PostgreSQL
    with SessionLocal() as session:
        count = session.execute(select(ReportModel)).scalars().all()
        assert len(count) == 1


def test_get_report_by_id(client: TestClient):
    """GET /api/v1/reports/{id} returns existing report or 404."""
    report = _make_sample_report()
    client.post("/api/v1/reports", json=report.model_dump(mode="json"))

    resp = client.get(f"/api/v1/reports/{report.report_id}")
    assert resp.status_code == 200
    assert resp.json()["report_id"] == report.report_id

    # 404 for nonexistent
    resp_404 = client.get("/api/v1/reports/nonexistent_rep_999")
    assert resp_404.status_code == 404
    assert "not found" in resp_404.json()["detail"].lower()


# =====================================================================
# INCIDENTS ENDPOINT TESTS
# =====================================================================


def test_get_incidents_empty_database(client: TestClient):
    """GET /api/v1/incidents returns empty list on empty database."""
    resp = client.get("/api/v1/incidents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_post_incident_creates_record_with_evidence_and_timeline(client: TestClient):
    """POST /api/v1/incidents persists incident, evidence provenance, and evolution timeline."""
    incident = _make_sample_incident()
    payload = incident.model_dump(mode="json")

    resp = client.post("/api/v1/incidents", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["incident_id"] == incident.incident_id
    assert data["title"] == incident.title
    assert data["severity"] == "HIGH"
    assert data["verification_summary"] is not None
    assert len(data["verification_summary"]["evidence_items"]) == 1
    assert data["verification_summary"]["evidence_items"][0]["evidence_id"] == f"ev_{incident.incident_id}"
    assert len(data["timeline"]) == 1

    # Verify directly in PostgreSQL
    with SessionLocal() as session:
        row = session.execute(
            select(IncidentModel).where(IncidentModel.incident_id == incident.incident_id)
        ).scalar_one_or_none()
        assert row is not None
        assert row.title == incident.title
        assert row.severity == "HIGH"
        assert len(row.evidence_items) == 1
        assert len(row.timeline) == 1


def test_post_incident_upsert_prevents_duplicates(client: TestClient):
    """POST /api/v1/incidents twice with same incident_id updates existing record without duplicate."""
    incident = _make_sample_incident()
    payload = incident.model_dump(mode="json")

    # First POST
    r1 = client.post("/api/v1/incidents", json=payload)
    assert r1.status_code == 201

    # Second POST with updated title, severity, and timeline
    updated = incident.model_copy(
        update={
            "title": "Escalated Flash Flood in Noida",
            "severity": IncidentSeverity.CRITICAL,
            "priority_score": 98.0,
        }
    )
    r2 = client.post("/api/v1/incidents", json=updated.model_dump(mode="json"))
    assert r2.status_code == 201
    assert r2.json()["title"] == "Escalated Flash Flood in Noida"
    assert r2.json()["severity"] == "CRITICAL"

    # Confirm only one incident exists in DB
    with SessionLocal() as session:
        incidents = session.execute(select(IncidentModel)).scalars().all()
        assert len(incidents) == 1


def test_get_incident_by_id(client: TestClient):
    """GET /api/v1/incidents/{id} returns requested incident with evidence provenance or 404."""
    incident = _make_sample_incident()
    client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))

    resp = client.get(f"/api/v1/incidents/{incident.incident_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_id"] == incident.incident_id
    assert data["verification_summary"]["verification_status"] == "VERIFIED"
    assert data["verification_summary"]["evidence_items"][0]["reasoning"] == (
        "Consistent radar rain gauge measurements exceeding 50mm/hr"
    )

    # 404 for missing incident
    resp_404 = client.get("/api/v1/incidents/inc_nonexistent_xyz")
    assert resp_404.status_code == 404
    assert "not found" in resp_404.json()["detail"].lower()


def test_get_incidents_filtering(client: TestClient):
    """Test GET /api/v1/incidents with category, severity, status, date, and PostGIS location filters."""
    # Seed 3 distinct incidents
    inc1 = _make_sample_incident(
        incident_id="inc_noida_rain",
        title="Heavy Rain in Noida",
        category="RAIN",
        sev=IncidentSeverity.HIGH,
        status=VerificationStatus.VERIFIED,
        dt=datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc),
        lat=28.627,
        lon=77.372,
        city="Noida",
        state_name="Uttar Pradesh",
    )
    inc2 = _make_sample_incident(
        incident_id="inc_mumbai_flood",
        title="Urban Flood in Mumbai",
        category="FLOOD",
        sev=IncidentSeverity.CRITICAL,
        status=VerificationStatus.SUPPORTED,
        dt=datetime(2026, 9, 5, 14, 0, tzinfo=timezone.utc),
        lat=19.076,
        lon=72.877,
        city="Mumbai",
        state_name="Maharashtra",
    )
    inc3 = _make_sample_incident(
        incident_id="inc_jaipur_heat",
        title="Severe Heatwave in Jaipur",
        category="HEATWAVE",
        sev=IncidentSeverity.MODERATE,
        status=VerificationStatus.UNVERIFIED,
        dt=datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc),
        lat=26.912,
        lon=75.787,
        city="Jaipur",
        state_name="Rajasthan",
    )

    for inc in [inc1, inc2, inc3]:
        res = client.post("/api/v1/incidents", json=inc.model_dump(mode="json"))
        assert res.status_code == 201

    # 1. Category filter
    r_cat = client.get("/api/v1/incidents?event_category=RAIN")
    assert r_cat.status_code == 200
    items = r_cat.json()
    assert len(items) == 1
    assert items[0]["incident_id"] == "inc_noida_rain"

    # 2. Severity filter
    r_sev = client.get("/api/v1/incidents?severity=CRITICAL")
    assert r_sev.status_code == 200
    assert len(r_sev.json()) == 1
    assert r_sev.json()[0]["incident_id"] == "inc_mumbai_flood"

    # 3. Verification status filter
    r_stat = client.get("/api/v1/incidents?verification_status=UNVERIFIED")
    assert r_stat.status_code == 200
    assert len(r_stat.json()) == 1
    assert r_stat.json()[0]["incident_id"] == "inc_jaipur_heat"

    # 4. Date filter
    r_date = client.get("/api/v1/incidents?date=2026-09-04")
    assert r_date.status_code == 200
    assert len(r_date.json()) == 1
    assert r_date.json()[0]["incident_id"] == "inc_noida_rain"

    # 5. Start date filter
    r_start = client.get("/api/v1/incidents?start_date=2026-09-04T00:00:00Z")
    assert r_start.status_code == 200
    ids = {i["incident_id"] for i in r_start.json()}
    assert ids == {"inc_noida_rain", "inc_mumbai_flood"}

    # 6. City / State hierarchy filter
    r_city = client.get("/api/v1/incidents?city=Noida")
    assert r_city.status_code == 200
    assert len(r_city.json()) == 1
    assert r_city.json()[0]["incident_id"] == "inc_noida_rain"

    r_state = client.get("/api/v1/incidents?state=Maharashtra")
    assert r_state.status_code == 200
    assert len(r_state.json()) == 1
    assert r_state.json()[0]["incident_id"] == "inc_mumbai_flood"

    # 7. PostGIS spatial radius filter (Search around Delhi/Noida within 20km)
    r_geo = client.get("/api/v1/incidents?latitude=28.625&longitude=77.37&radius_km=20")
    assert r_geo.status_code == 200
    geo_ids = {i["incident_id"] for i in r_geo.json()}
    assert geo_ids == {"inc_noida_rain"}

    # 8. Partial coordinates validation
    r_partial = client.get("/api/v1/incidents?latitude=28.625")
    assert r_partial.status_code == 400
    assert "Both latitude and longitude must be provided together" in r_partial.json()["detail"]


def test_post_invalid_payload_returns_422(client: TestClient):
    """Malformed request payload is rejected with HTTP 422."""
    resp = client.post("/api/v1/incidents", json={"title": "Missing required fields"})
    assert resp.status_code == 422


# =====================================================================
# ARCHITECTURE AUDIT VERIFICATION TESTS
# =====================================================================


def test_timeline_reconciliation_and_deduplication(client: TestClient):
    """Verify IncidentTimeline records are identified and preserved across upserts without churn or duplicates."""
    ts_a = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    ev_a = IncidentTimeline(
        timestamp=ts_a,
        event_type="created",
        description="Incident formed from station alert",
        new_state=IncidentState.REPORTED,
        new_severity=IncidentSeverity.HIGH,
    )
    incident = _make_sample_incident(incident_id="inc_audit_timeline_01")
    incident.timeline = [ev_a]

    # 1. First POST: Timeline event A is created
    r1 = client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))
    assert r1.status_code == 201

    with SessionLocal() as session:
        inc = session.execute(
            select(IncidentModel).where(IncidentModel.incident_id == "inc_audit_timeline_01")
        ).scalar_one()
        assert len(inc.timeline) == 1
        initial_id = inc.timeline[0].id
        assert inc.timeline[0].event_type == "created"

    # 2. Re-POST identical incident: Event A must NOT be duplicated and its DB ID must remain stable
    r2 = client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))
    assert r2.status_code == 201

    with SessionLocal() as session:
        inc = session.execute(
            select(IncidentModel).where(IncidentModel.incident_id == "inc_audit_timeline_01")
        ).scalar_one()
        assert len(inc.timeline) == 1
        assert inc.timeline[0].id == initial_id  # Stable row ID preserved

    # 3. Add genuinely new event B and re-POST: B is appended, A remains once
    ts_b = datetime(2026, 9, 4, 10, 30, tzinfo=timezone.utc)
    ev_b = IncidentTimeline(
        timestamp=ts_b,
        event_type="severity_escalated",
        description="Severity increased to CRITICAL due to continuous rain",
        previous_severity=IncidentSeverity.HIGH,
        new_severity=IncidentSeverity.CRITICAL,
    )
    incident.timeline = [ev_a, ev_b]
    incident.last_updated_at = ts_b

    r3 = client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))
    assert r3.status_code == 201

    with SessionLocal() as session:
        inc = session.execute(
            select(IncidentModel).where(IncidentModel.incident_id == "inc_audit_timeline_01")
        ).scalar_one()
        assert len(inc.timeline) == 2
        assert inc.timeline[0].id == initial_id  # Original A still intact
        assert inc.timeline[1].event_type == "severity_escalated"


def test_evidence_reconciliation_and_deduplication(client: TestClient):
    """Verify evidence items are reconciled cleanly: duplicate prevention, additions, and removals."""
    ts = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    e1 = EvidenceItem(
        evidence_id="ev_aud_01",
        report_id="rep_aud_01",
        source="imd",
        source_type="official",
        relationship=EvidenceRelationship.SUPPORTING,
        confidence_score=0.90,
        reasoning="IMD rainfall gauge proof",
        timestamp=ts,
    )
    incident = _make_sample_incident(incident_id="inc_audit_ev_01")
    incident.verification_summary = VerificationSummary(
        verification_status=VerificationStatus.SUPPORTED,
        overall_confidence=0.90,
        supporting_count=1,
        contradicting_count=0,
        evidence_items=[e1],
        explanation="Initial evidence",
        updated_at=ts,
    )

    # 1. First POST: E1 created
    client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))
    with SessionLocal() as session:
        inc = session.execute(select(IncidentModel).where(IncidentModel.incident_id == "inc_audit_ev_01")).scalar_one()
        assert len(inc.evidence_items) == 1
        assert inc.evidence_items[0].evidence_id == "ev_aud_01"

    # 2. Re-POST identical incident: E1 exists exactly once
    client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))
    with SessionLocal() as session:
        inc = session.execute(select(IncidentModel).where(IncidentModel.incident_id == "inc_audit_ev_01")).scalar_one()
        assert len(inc.evidence_items) == 1

    # 3. Add E2 and re-POST: Both E1 and E2 exist
    e2 = EvidenceItem(
        evidence_id="ev_aud_02",
        report_id="rep_aud_02",
        source="citizen",
        source_type="citizen",
        relationship=EvidenceRelationship.CORROBORATING,
        confidence_score=0.85,
        reasoning="Citizen video of knee-deep water",
        timestamp=ts,
    )
    incident.verification_summary.evidence_items = [e1, e2]
    incident.verification_summary.supporting_count = 2
    client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))

    with SessionLocal() as session:
        inc = session.execute(select(IncidentModel).where(IncidentModel.incident_id == "inc_audit_ev_01")).scalar_one()
        assert len(inc.evidence_items) == 2
        ev_ids = {e.evidence_id for e in inc.evidence_items}
        assert ev_ids == {"ev_aud_01", "ev_aud_02"}

    # 4. Remove E1 and re-POST: Only E2 remains
    incident.verification_summary.evidence_items = [e2]
    incident.verification_summary.supporting_count = 1
    client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))

    with SessionLocal() as session:
        inc = session.execute(select(IncidentModel).where(IncidentModel.incident_id == "inc_audit_ev_01")).scalar_one()
        assert len(inc.evidence_items) == 1
        assert inc.evidence_items[0].evidence_id == "ev_aud_02"


def test_report_placeholder_safety_and_upgrade(client: TestClient):
    """Verify that report placeholder stubs are never exposed via GET /reports/{id} and upgrade cleanly."""
    # 1. Incident references report rep_unseen_888 that hasn't been ingested yet
    ts = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    ev = EvidenceItem(
        evidence_id="ev_unseen_01",
        report_id="rep_unseen_888",
        source="imd",
        source_type="official",
        relationship=EvidenceRelationship.SUPPORTING,
        confidence_score=0.95,
        reasoning="Radar measurement",
        timestamp=ts,
    )
    incident = _make_sample_incident(incident_id="inc_unseen_01")
    incident.verification_summary.evidence_items = [ev]

    r_inc = client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))
    assert r_inc.status_code == 201

    # 2. Querying GET /api/v1/reports/rep_unseen_888 MUST return 404, not exposing a dummy stub
    r_stub = client.get("/api/v1/reports/rep_unseen_888")
    assert r_stub.status_code == 404

    # 3. Upstream report arrives via POST /api/v1/reports
    real_report = WeatherReport(
        report_id="rep_unseen_888",
        source="imd",
        source_type="official",
        timestamp=ts,
        text="Official IMD radar rainfall rate 60mm/hr",
        latitude=28.627,
        longitude=77.372,
    )
    r_post_rep = client.post("/api/v1/reports", json=real_report.model_dump(mode="json"))
    assert r_post_rep.status_code == 201

    # 4. Now GET /api/v1/reports/rep_unseen_888 returns 200 with the genuine WeatherReport
    r_get_rep = client.get("/api/v1/reports/rep_unseen_888")
    assert r_get_rep.status_code == 200
    assert r_get_rep.json()["text"] == "Official IMD radar rainfall rate 60mm/hr"
    assert r_get_rep.json()["source_type"] == "official"


def test_postgis_geometry_and_coordinate_order(client: TestClient):
    """Verify PostGIS geometry coordinates follow POINT(lon lat) order and SRID 4326."""
    lat = 28.627
    lon = 77.372
    report = _make_sample_report(report_id="rep_postgis_audit_01", lat=lat, lon=lon)
    client.post("/api/v1/reports", json=report.model_dump(mode="json"))

    with engine.connect() as conn:
        res = conn.execute(
            text(
                "SELECT ST_AsText(location) as wkt, ST_SRID(location) as srid, "
                "ST_X(location) as x_lon, ST_Y(location) as y_lat "
                "FROM reports WHERE report_id = 'rep_postgis_audit_01';"
            )
        ).fetchone()

        assert res is not None
        assert res.srid == 4326
        assert f"POINT({lon} {lat})" in res.wkt
        # Verify no reversal: X must be longitude, Y must be latitude
        assert abs(res.x_lon - lon) < 1e-4
        assert abs(res.y_lat - lat) < 1e-4


def test_transaction_rollback_prevents_partial_persistence(client: TestClient):
    """Verify that a controlled DB write failure causes complete rollback with no orphan records."""
    ts = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    ev = EvidenceItem(
        evidence_id="ev_fail_tx_99",
        report_id="rep_fail_tx_99",
        source="imd",
        source_type="official",
        relationship=EvidenceRelationship.SUPPORTING,
        reasoning="Test rollback proof",
        timestamp=ts,
    )
    incident = _make_sample_incident(incident_id="inc_fail_tx_99")
    incident.verification_summary = VerificationSummary(
        verification_status=VerificationStatus.UNVERIFIED,
        evidence_items=[ev],
        updated_at=ts,
    )

    # Force simulated failure on session commit
    with patch("sqlalchemy.orm.Session.commit", side_effect=RuntimeError("Simulated database failure")):
        resp = client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))
        assert resp.status_code == 500

    # Verify no partial records remain in PostgreSQL
    with SessionLocal() as session:
        inc_row = session.execute(
            select(IncidentModel).where(IncidentModel.incident_id == "inc_fail_tx_99")
        ).scalar_one_or_none()
        ev_row = session.execute(
            select(EvidenceItemModel).where(EvidenceItemModel.evidence_id == "ev_fail_tx_99")
        ).scalar_one_or_none()

        assert inc_row is None
        assert ev_row is None
