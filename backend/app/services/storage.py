from __future__ import annotations

import boto3
from botocore.exceptions import ClientError
import redis.asyncio as aioredis

from app.config import settings

_redis: aioredis.Redis | None = None
_s3 = None  # lazily created boto3 S3 client


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


# --- Object storage (S3) for the raw file bytes -----------------------------
# The single point of storage abstraction: files live in S3, while Redis keeps
# only lightweight state (status, rules, reasons, result). Credentials come from
# the environment (aws configure locally, IAM task role in the cloud).

def _s3_client():
    """Create the S3 client once and reuse it (boto3 clients are thread-safe)."""
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3")
    return _s3


def put_file(key: str, data: bytes) -> None:
    """Store raw file bytes in the S3 bucket under the given key."""
    _s3_client().put_object(Bucket=settings.s3_bucket, Key=key, Body=data)


def get_file(key: str) -> bytes | None:
    """Read raw file bytes back from S3; returns None if the object is gone."""
    try:
        resp = _s3_client().get_object(Bucket=settings.s3_bucket, Key=key)
        return resp["Body"].read()
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None
        raise