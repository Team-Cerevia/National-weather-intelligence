"""
Unit tests for Track B Stream Broker, Producer, Consumer, DLQ, and Replayer.
"""

from datetime import datetime, timezone

import pytest

from contracts import WeatherReport
from streaming.broker import StreamBroker
from streaming.consumer import StreamConsumer
from streaming.dlq import DeadLetterQueue
from streaming.producer import StreamProducer
from streaming.replay import StreamReplayer


@pytest.fixture
def dummy_report():
    return WeatherReport(
        report_id="rep-stream-101",
        source="test-stream-source",
        source_type="official",
        timestamp=datetime.now(timezone.utc),
        latitude=28.6139,
        longitude=77.2090,
        text="Heavy rainfall in Delhi stream test",
        event_category="RAIN",
    )


def test_broker_memory_fallback():
    broker = StreamBroker(redis_url="redis://invalid_host_6379:6379/0")
    assert not broker.is_redis_available()

    msg_id = broker.publish_memory("stream:test", {"key": "val"})
    assert msg_id == "1-0"

    read_data = broker.read_memory("stream:test")
    assert len(read_data) == 1
    assert read_data[0]["fields"]["key"] == "val"


def test_producer_publish(dummy_report):
    broker = StreamBroker(redis_url="redis://invalid_host_6379:6379/0")
    producer = StreamProducer(broker=broker, stream_name="stream:test_prod")

    msg_id = producer.publish_report(dummy_report)
    assert msg_id is not None
    assert len(msg_id) > 0


def test_consumer_processing(dummy_report):
    broker = StreamBroker(redis_url="redis://invalid_host_6379:6379/0")
    producer = StreamProducer(broker=broker, stream_name="stream:test_cons")
    producer.publish_report(dummy_report)

    received_reports = []

    def sample_handler(report: WeatherReport):
        received_reports.append(report)

    consumer = StreamConsumer(broker=broker, stream_name="stream:test_cons")
    processed = consumer.read_and_process(sample_handler)

    assert len(processed) == 1
    assert len(received_reports) == 1
    assert received_reports[0].report_id == "rep-stream-101"


def test_dlq_routing():
    broker = StreamBroker(redis_url="redis://invalid_host_6379:6379/0")
    dlq = DeadLetterQueue(broker=broker, dlq_stream="stream:test_dlq", max_retries=2)

    # 1st failure - under max_retries
    res1 = dlq.handle_failure("msg-1", {"payload": "invalid"}, "Corrupt JSON")
    assert res1 == ""

    # 2nd failure - max_retries reached, routed to DLQ
    res2 = dlq.handle_failure("msg-1", {"payload": "invalid"}, "Corrupt JSON")
    assert res2 != ""

    dlq_data = broker.read_memory("stream:test_dlq")
    assert len(dlq_data) == 1
    assert dlq_data[0]["fields"]["original_msg_id"] == "msg-1"


def test_stream_replay(dummy_report):
    broker = StreamBroker(redis_url="redis://invalid_host_6379:6379/0")
    producer = StreamProducer(broker=broker, stream_name="stream:test_replay")
    producer.publish_report(dummy_report)

    replayed = []

    def replay_handler(report: WeatherReport):
        replayed.append(report)

    replayer = StreamReplayer(broker=broker, stream_name="stream:test_replay")
    ids = replayer.replay(replay_handler)

    assert len(ids) == 1
    assert len(replayed) == 1
    assert replayed[0].report_id == "rep-stream-101"
