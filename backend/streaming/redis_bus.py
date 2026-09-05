"""Redis Pub/Sub event bus for real-time weather intelligence incident updates."""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import redis
import redis.asyncio as aioredis

from contracts.incident import Incident

logger = logging.getLogger(__name__)

INCIDENTS_CHANNEL = "incidents:updates"

_sync_client: redis.Redis | None = None


def get_redis_url() -> str:
    """Resolve Redis connection URL from environment variables or local development default."""
    env_url = os.getenv("REDIS_URL")
    if env_url:
        return env_url
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    db = os.getenv("REDIS_DB", "0")
    return f"redis://{host}:{port}/{db}"


def get_sync_redis() -> redis.Redis:
    """Return reusable synchronous Redis client for event publishing."""
    global _sync_client
    if _sync_client is None:
        _sync_client = redis.from_url(get_redis_url(), decode_responses=True)
    return _sync_client


def publish_incident_update(incident: Incident) -> None:
    """Publish an incident.updated event to the Redis Pub/Sub channel.

    Must be called strictly AFTER a successful PostgreSQL database commit.
    """
    payload = {
        "event": "incident.updated",
        "incident_id": incident.incident_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "incident": incident.model_dump(mode="json"),
    }
    client = get_sync_redis()
    message_str = json.dumps(payload)
    client.publish(INCIDENTS_CHANNEL, message_str)
    logger.info("Published incident %s update to Redis channel %s", incident.incident_id, INCIDENTS_CHANNEL)


async def redis_subscriber_task(manager: Any, stop_event: asyncio.Event) -> None:
    """Continuous async background task listening to Redis Pub/Sub and forwarding to WebSocket clients."""
    redis_url = get_redis_url()
    client = aioredis.from_url(redis_url, decode_responses=True)
    pubsub = client.pubsub()

    try:
        await pubsub.subscribe(INCIDENTS_CHANNEL)
        logger.info("Redis subscriber connected and listening to channel: %s", INCIDENTS_CHANNEL)

        while not stop_event.is_set():
            try:
                # Poll with short timeout to allow responsive shutdown
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    data = message.get("data")
                    if isinstance(data, str):
                        try:
                            event_data = json.loads(data)
                            await manager.broadcast(event_data)
                        except json.JSONDecodeError as jde:
                            logger.error("Failed to decode JSON from Redis message: %s", jde)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as loop_err:
                if not stop_event.is_set():
                    logger.warning("Transient error in Redis subscriber loop: %s", loop_err)
                    await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        logger.info("Redis subscriber task cancelled.")
    except Exception as err:
        logger.exception("Redis subscriber encountered fatal error: %s", err)
    finally:
        try:
            await pubsub.unsubscribe(INCIDENTS_CHANNEL)
            if hasattr(pubsub, "aclose"):
                await pubsub.aclose()
            else:
                await pubsub.close()
            if hasattr(client, "aclose"):
                await client.aclose()
            else:
                await client.close()
        except Exception as close_err:
            logger.debug("Error during Redis pubsub cleanup: %s", close_err)
        logger.info("Redis subscriber shut down cleanly.")
