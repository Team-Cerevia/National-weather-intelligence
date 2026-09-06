"""
Stream Consumer Module for Track B.
Provides Consumer Group worker with ACK handling and deserialization of WeatherReport events.
"""

import logging
from typing import Callable, Dict, List, Optional

from contracts import WeatherReport
from streaming.broker import StreamBroker
from streaming.dlq import DeadLetterQueue

logger = logging.getLogger(__name__)

DEFAULT_STREAM_NAME = "stream:weather_reports"
DEFAULT_GROUP_NAME = "weather_processors"


class StreamConsumer:
    """
    Consumes WeatherReport events from Redis stream using Consumer Groups with ACK confirmation.
    """

    def __init__(
        self,
        broker: Optional[StreamBroker] = None,
        dlq: Optional[DeadLetterQueue] = None,
        stream_name: str = DEFAULT_STREAM_NAME,
        group_name: str = DEFAULT_GROUP_NAME,
        consumer_name: str = "worker-1",
    ):
        self.broker = broker or StreamBroker()
        self.dlq = dlq or DeadLetterQueue(broker=self.broker)
        self.stream_name = stream_name
        self.group_name = group_name
        self.consumer_name = consumer_name
        self._ensure_group()

    def _ensure_group(self) -> None:
        """Create consumer group if it does not already exist."""
        if self.broker.is_redis_available():
            client = self.broker.get_client()
            try:
                client.xgroup_create(self.stream_name, self.group_name, id="0", mkstream=True)
            except Exception as e:
                # BusyGroup error expected if group already exists
                if "BUSYGROUP" not in str(e):
                    logger.debug(f"Consumer group notice: {e}")

    def read_and_process(
        self,
        handler: Callable[[WeatherReport], None],
        count: int = 10,
        block_ms: int = 1000,
    ) -> List[str]:
        """
        Reads pending messages from stream, deserializes WeatherReport, invokes handler, and sends XACK.
        Failed messages are routed to DLQ.
        Returns list of successfully processed message IDs.
        """
        processed_ids: List[str] = []

        if self.broker.is_redis_available():
            client = self.broker.get_client()
            entries = client.xreadgroup(
                groupname=self.group_name,
                consumername=self.consumer_name,
                streams={self.stream_name: ">"},
                count=count,
                block=block_ms,
            )

            if not entries:
                return processed_ids

            for stream_key, messages in entries:
                for msg_id, fields in messages:
                    success = self._process_single_message(msg_id, fields, handler)
                    if success:
                        client.xack(self.stream_name, self.group_name, msg_id)
                        processed_ids.append(msg_id)
        else:
            # Fallback memory reading
            memory_entries = self.broker.read_memory(self.stream_name)
            for entry in memory_entries:
                msg_id = entry["id"]
                fields = entry["fields"]
                if self._process_single_message(msg_id, fields, handler):
                    processed_ids.append(msg_id)

        return processed_ids

    def _process_single_message(
        self,
        msg_id: str,
        fields: Dict[str, str],
        handler: Callable[[WeatherReport], None],
    ) -> bool:
        """Helper to deserialize, invoke handler, and pass to DLQ on exception."""
        try:
            payload_str = fields.get("payload")
            if not payload_str:
                raise ValueError("Missing payload in stream event")
            report = WeatherReport.model_validate_json(payload_str)
            handler(report)
            return True
        except Exception as err:
            logger.error(f"Error processing stream msg {msg_id}: {err}")
            self.dlq.handle_failure(msg_id, fields, str(err))
            return False
