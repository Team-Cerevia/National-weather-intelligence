"""
Replay Engine Module for Track B.
Provides capabilities to replay past stream events from a specific point in time or message ID.
"""

from typing import Callable, List, Optional

from contracts import WeatherReport
from streaming.broker import StreamBroker

DEFAULT_STREAM_NAME = "stream:weather_reports"


class StreamReplayer:
    """
    Replays stream events from a starting message ID or start offset.
    """

    def __init__(self, broker: Optional[StreamBroker] = None, stream_name: str = DEFAULT_STREAM_NAME):
        self.broker = broker or StreamBroker()
        self.stream_name = stream_name

    def replay(
        self,
        handler: Callable[[WeatherReport], None],
        start_id: str = "0-0",
        count: int = 100,
    ) -> List[str]:
        """
        Reads events from stream starting at start_id and invokes handler for each valid report.
        Returns list of replayed message IDs.
        """
        replayed_ids: List[str] = []

        if self.broker.is_redis_available():
            client = self.broker.get_client()
            entries = client.xrange(self.stream_name, min=start_id, max="+", count=count)
            for msg_id, fields in entries:
                payload_str = fields.get("payload")
                if payload_str:
                    report = WeatherReport.model_validate_json(payload_str)
                    handler(report)
                    replayed_ids.append(msg_id)
        else:
            entries = self.broker.read_memory(self.stream_name)
            for entry in entries:
                msg_id = entry["id"]
                fields = entry["fields"]
                payload_str = fields.get("payload")
                if payload_str:
                    report = WeatherReport.model_validate_json(payload_str)
                    handler(report)
                    replayed_ids.append(msg_id)

        return replayed_ids
