from __future__ import annotations

import redis.asyncio as aioredis

from app.config import settings

_redis: aioredis.Redis | None = None


def init_redis() -> aioredis.Redis:
    """Called once at application startup (lifespan in main.py)."""
    global _redis
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis is not initialized - call init_redis() in lifespan")
    return _redis


async def close_redis() -> None:
    if _redis is not None:
        await _redis.aclose()


async def ping() -> bool:
    return await get_redis().ping()

async def set_value(key: str, value: str, ttl: int | None = None) -> None:
    await get_redis().set(key, value, ex=ttl)


async def get_value(key: str) -> str | None:
    return await get_redis().get(key)