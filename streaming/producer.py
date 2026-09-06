"""
Stream Producer Module for Track B.
Accepts WeatherReport contract objects, serializes them to JSON, and publishes to Redis Streams.
"""

from typing import Optional

from contracts import WeatherReport
from streaming.broker import StreamBroker

DEFAULT_STREAM_NAME = "stream:weather_reports"


class StreamProducer:
    """
    Publishes WeatherReport instances into Redis Streams stream:weather_reports.
    """

    def __init__(self, broker: Optional[StreamBroker] = None, stream_name: str = DEFAULT_STREAM_NAME):
        self.broker = broker or StreamBroker()
        self.stream_name = stream_name

    def publish_report(self, report: WeatherReport) -> str:
        """
        Serializes WeatherReport object into JSON payload and publishes to Redis Stream.
        Returns the generated message ID.
        """
        payload = report.model_dump_json()
        fields = {"report_id": report.report_id, "payload": payload, "source": report.source}

        if self.broker.is_redis_available():
            client = self.broker.get_client()
            msg_id = client.xadd(self.stream_name, fields)
            return str(msg_id)
        else:
            return self.broker.publish_memory(self.stream_name, fields)
