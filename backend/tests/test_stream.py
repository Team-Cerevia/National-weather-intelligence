"""Integration and unit tests for Redis Pub/Sub and WebSocket real-time incident streaming."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import redis
from starlette.testclient import TestClient
from starlette.websockets import WebSocket

from backend.api.routes.stream import ConnectionManager, stream_manager
from backend.db.session import engine, init_db
from backend.main import app
from backend.streaming import INCIDENTS_CHANNEL, get_redis_url
from contracts.evidence import EvidenceItem, EvidenceRelationship, VerificationStatus, VerificationSummary
from contracts.incident import Incident, IncidentSeverity, IncidentState


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database schema is ready before running stream tests."""
    init_db(engine)


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


def _make_sample_incident(incident_id: str = "inc_stream_test_01") -> Incident:
    """Helper creating a valid canonical Incident."""
    ts = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    ev = EvidenceItem(
        evidence_id=f"ev_{incident_id}",
        report_id=f"rep_{incident_id}",
        source="imd",
        source_type="official",
        relationship=EvidenceRelationship.SUPPORTING,
        confidence_score=0.95,
        reasoning="Consistent radar gauge readings",
        timestamp=ts,
    )
    summary = VerificationSummary(
        verification_status=VerificationStatus.VERIFIED,
        overall_confidence=0.92,
        supporting_count=1,
        contradicting_count=0,
        evidence_items=[ev],
        explanation="Station alert confirmed",
        updated_at=ts,
    )
    return Incident(
        incident_id=incident_id,
        title="Severe Waterlogging in Noida",
        event_category="RAIN",
        state=IncidentState.REPORTED,
        severity=IncidentSeverity.HIGH,
        priority_score=88.0,
        latitude=28.627,
        longitude=77.372,
        first_reported_at=ts,
        last_updated_at=ts,
        report_ids=[f"rep_{incident_id}"],
        verification_summary=summary,
    )


# =====================================================================
# WEBSOCKET CONNECTION & LIFECYCLE TESTS
# =====================================================================


def test_websocket_connection_and_initial_event(client: TestClient):
    """WebSocket connection succeeds, receives initial handshake frame, and disconnects cleanly."""
    with client.websocket_connect("/api/v1/stream") as ws:
        frame = ws.receive_json()
        assert frame["event"] == "connected"
        assert "Connected to real-time weather incident stream" in frame["message"]
        assert "timestamp" in frame


def test_websocket_disconnect_cleanly_unregisters(client: TestClient):
    """Disconnecting a WebSocket client decreases the active connection count cleanly."""
    initial_count = len(stream_manager.active_connections)
    with client.websocket_connect("/api/v1/stream") as ws:
        _ = ws.receive_json()
        assert len(stream_manager.active_connections) == initial_count + 1

    # After exiting context manager, connection is closed
    assert len(stream_manager.active_connections) == initial_count


# =====================================================================
# CONNECTION MANAGER TESTS
# =====================================================================


@pytest.mark.anyio
async def test_connection_manager_broadcast_multiple_clients():
    """ConnectionManager broadcasts payload to multiple connected clients."""
    manager = ConnectionManager()

    ws1: Any = AsyncMock(spec=WebSocket)
    ws2: Any = AsyncMock(spec=WebSocket)

    await manager.connect(ws1)
    await manager.connect(ws2)
    assert len(manager.active_connections) == 2

    test_payload = {"event": "incident.updated", "incident_id": "inc_001"}
    await manager.broadcast(test_payload)

    ws1.send_json.assert_awaited_once_with(test_payload)
    ws2.send_json.assert_awaited_once_with(test_payload)


@pytest.mark.anyio
async def test_connection_manager_dead_client_resilience():
    """A dead client raising an exception during send does not crash broadcast or block healthy clients."""
    manager = ConnectionManager()

    healthy_client: Any = AsyncMock(spec=WebSocket)
    dead_client: Any = AsyncMock(spec=WebSocket)
    dead_client.send_json.side_effect = RuntimeError("Broken pipe / client disconnected")

    await manager.connect(healthy_client)
    await manager.connect(dead_client)
    assert len(manager.active_connections) == 2

    test_payload = {"event": "incident.updated", "incident_id": "inc_resilience_test"}
    # Must not raise exception
    await manager.broadcast(test_payload)

    # Healthy client received message
    healthy_client.send_json.assert_awaited_once_with(test_payload)
    # Dead client was pruned
    assert dead_client not in manager.active_connections
    assert healthy_client in manager.active_connections
    assert len(manager.active_connections) == 1


# =====================================================================
# DATABASE COMMIT ORDERING & REDIS PUBLISH TESTS
# =====================================================================


def test_redis_publish_occurs_after_successful_commit(client: TestClient):
    """POST /api/v1/incidents publishes to Redis only AFTER successful DB commit."""
    incident = _make_sample_incident("inc_order_test_01")
    call_order: list[str] = []

    original_commit = None
    from sqlalchemy.orm import Session

    original_commit = Session.commit

    def tracked_commit(self):
        call_order.append("db_commit")
        return original_commit(self)

    def tracked_publish(inc):
        call_order.append("redis_publish")

    with (
        patch.object(Session, "commit", tracked_commit),
        patch("backend.api.routes.incidents.publish_incident_update", side_effect=tracked_publish),
    ):
        resp = client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))
        assert resp.status_code == 201

    # Strict ordering: db_commit must happen before redis_publish
    assert call_order == ["db_commit", "redis_publish"]


def test_no_redis_publish_on_database_rollback(client: TestClient):
    """When a database transaction fails and rolls back, NO Redis event is published."""
    incident = _make_sample_incident("inc_rollback_test_01")

    with (
        patch("sqlalchemy.orm.Session.commit", side_effect=RuntimeError("Simulated DB failure")),
        patch("backend.api.routes.incidents.publish_incident_update") as mock_publish,
    ):
        resp = client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))
        assert resp.status_code == 500
        # Critical invariant: NEVER publish when commit fails
        mock_publish.assert_not_called()


def test_redis_unavailable_resilience(client: TestClient):
    """If Redis publish fails after successful commit, PostgreSQL remains committed and client gets 201."""
    incident = _make_sample_incident("inc_redis_down_test_01")

    with patch(
        "backend.api.routes.incidents.publish_incident_update",
        side_effect=redis.ConnectionError("Redis connection refused"),
    ):
        resp = client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))
        # Database commit succeeded, so response returns 201 and is not rolled back
        assert resp.status_code == 201
        assert resp.json()["incident_id"] == "inc_redis_down_test_01"


# =====================================================================
# LIVE REDIS PUB/SUB & SERIALIZATION INTEGRATION TESTS
# =====================================================================


def test_real_redis_pubsub_integration(client: TestClient):
    """Integration test verifying incident POST publishes canonical event to real Redis container."""
    redis_client = redis.from_url(get_redis_url(), decode_responses=True)
    pubsub = redis_client.pubsub()
    pubsub.subscribe(INCIDENTS_CHANNEL)

    # Wait for subscription confirmation
    sub_msg = pubsub.get_message(timeout=2.0)
    assert sub_msg is not None

    incident = _make_sample_incident("inc_live_redis_01")
    resp = client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))
    assert resp.status_code == 201

    # Read message from Redis channel
    msg = pubsub.get_message(timeout=3.0)
    assert msg is not None
    assert msg["type"] == "message"
    assert msg["channel"] == INCIDENTS_CHANNEL

    event_data = json.loads(msg["data"])
    assert event_data["event"] == "incident.updated"
    assert event_data["incident_id"] == "inc_live_redis_01"
    assert "timestamp" in event_data

    # Verify incident payload validates against canonical Incident contract
    incident_obj = Incident.model_validate(event_data["incident"])
    assert incident_obj.incident_id == "inc_live_redis_01"
    assert incident_obj.title == incident.title
    assert incident_obj.event_category == incident.event_category
    assert incident_obj.severity == IncidentSeverity.HIGH

    pubsub.unsubscribe(INCIDENTS_CHANNEL)
    pubsub.close()


def test_websocket_broadcast_delivery(client: TestClient):
    """Connected WebSocket client receives broadcast event delivered via stream_manager."""
    with client.websocket_connect("/api/v1/stream") as ws:
        init_frame = ws.receive_json()
        assert init_frame["event"] == "connected"

        # Broadcast test incident update
        test_event = {
            "event": "incident.updated",
            "incident_id": "inc_broadcast_live_01",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "incident": {"incident_id": "inc_broadcast_live_01", "title": "Test Broadcast"},
        }
        asyncio.run(stream_manager.broadcast(test_event))

        received = ws.receive_json()
        assert received["event"] == "incident.updated"
        assert received["incident_id"] == "inc_broadcast_live_01"
        assert received["incident"]["title"] == "Test Broadcast"


def test_end_to_end_post_incident_redis_websocket_broadcast(client: TestClient):
    """End-to-end test: POST /api/v1/incidents -> Redis Pub/Sub -> WebSocket client receives event."""
    with client.websocket_connect("/api/v1/stream") as ws:
        init_frame = ws.receive_json()
        assert init_frame["event"] == "connected"

        incident = _make_sample_incident("inc_e2e_stream_01")
        resp = client.post("/api/v1/incidents", json=incident.model_dump(mode="json"))
        assert resp.status_code == 201

        # The Redis subscriber forwards published message to WebSocket client
        event = ws.receive_json()
        assert event["event"] == "incident.updated"
        assert event["incident_id"] == "inc_e2e_stream_01"
        assert event["incident"]["title"] == incident.title
