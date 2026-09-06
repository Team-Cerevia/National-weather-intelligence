"""
Dead-Letter Queue (DLQ) Module for Track B.
Handles failed stream message processing with retries and routes unrecoverable messages to stream:dlq:weather_reports.
"""

import json
import logging
from typing import Dict, Optional

from streaming.broker import StreamBroker

DEFAULT_DLQ_STREAM_NAME = "stream:dlq:weather_reports"
MAX_RETRIES = 3


class DeadLetterQueue:
    """
    Manages failed event routing to a Dead-Letter Queue stream.
    """

    def __init__(
        self,
        broker: Optional[StreamBroker] = None,
        dlq_stream: str = DEFAULT_DLQ_STREAM_NAME,
        max_retries: int = MAX_RETRIES,
    ):
        self.broker = broker or StreamBroker()
        self.dlq_stream = dlq_stream
        self.max_retries = max_retries
        self._retry_counts: Dict[str, int] = {}

    def handle_failure(self, msg_id: str, fields: Dict[str, str], error_reason: str) -> str:
        """
        Increments retry count for msg_id. If retry limit exceeded, routes to DLQ stream.
        """
        current_retries = self._retry_counts.get(msg_id, 0) + 1
        self._retry_counts[msg_id] = current_retries

        if current_retries >= self.max_retries:
            dlq_fields = {
                "original_msg_id": msg_id,
                "error": error_reason,
                "retries": str(current_retries),
                "original_payload": json.dumps(fields),
            }
            logging.warning(f"Routing msg {msg_id} to DLQ stream {self.dlq_stream} after {current_retries} retries")

            if self.broker.is_redis_available():
                client = self.broker.get_client()
                dlq_id = client.xadd(self.dlq_stream, dlq_fields)
                return str(dlq_id)
            else:
                return self.broker.publish_memory(self.dlq_stream, dlq_fields)

        return ""
