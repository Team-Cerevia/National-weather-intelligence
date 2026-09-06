"""
Stream Broker Module for Track B.
Provides a Redis connection manager with fallback to an in-memory queue when Redis is unreachable.
"""

import os
from typing import Any, Dict, List, Optional

import redis


class StreamBroker:
    """
    Manages connections to Redis Streams with an optional in-memory fallback mechanism.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client: Optional[redis.Redis] = None
        self._memory_streams: Dict[str, List[Dict[str, Any]]] = {}

    def get_client(self) -> redis.Redis:
        """Return connected Redis client, creating one if needed."""
        if self._client is None:
            self._client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    def is_redis_available(self) -> bool:
        """Check if Redis server is reachable."""
        try:
            client = self.get_client()
            return bool(client.ping())
        except Exception:
            return False

    def publish_memory(self, stream: str, fields: Dict[str, str]) -> str:
        """Fallback in-memory stream publish."""
        if stream not in self._memory_streams:
            self._memory_streams[stream] = []
        msg_id = f"{len(self._memory_streams[stream]) + 1}-0"
        entry = {"id": msg_id, "fields": fields}
        self._memory_streams[stream].append(entry)
        return msg_id

    def read_memory(self, stream: str) -> List[Dict[str, Any]]:
        """Fallback in-memory stream read."""
        return self._memory_streams.get(stream, [])
