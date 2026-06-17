import hashlib
import json
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger()

# Upstash is optional — if not configured, the cache silently no-ops so the
# app still runs locally without a Redis instance.
_redis = None
if settings.upstash_redis_rest_url and settings.upstash_redis_rest_token:
    from upstash_redis.asyncio import Redis

    _redis = Redis(
        url=settings.upstash_redis_rest_url,
        token=settings.upstash_redis_rest_token,
    )


def cache_key(namespace: str, *parts: str) -> str:
    """Deterministic cache key: 'fin:<namespace>:<sha256(parts)>'."""
    raw = "|".join(str(p).strip().lower() for p in parts)
    return f"fin:{namespace}:" + hashlib.sha256(raw.encode()).hexdigest()


async def get_json(key: str) -> Any | None:
    """Return a cached JSON value if present, else None. Never raises."""
    if _redis is None:
        return None
    try:
        value = await _redis.get(key)
        if value:
            logger.info("cache.hit", key=key[:40])
            return json.loads(value)
    except Exception as e:
        logger.warning("cache.get_error", error=str(e))
    return None


async def set_json(key: str, value: Any, ttl_seconds: int) -> None:
    """Cache a JSON-serializable value with a TTL. Never raises."""
    if _redis is None:
        return
    try:
        await _redis.setex(key, ttl_seconds, json.dumps(value, default=str))
        logger.info("cache.set", key=key[:40], ttl=ttl_seconds)
    except Exception as e:
        # Cache failure must never break the main flow.
        logger.warning("cache.set_error", error=str(e))
