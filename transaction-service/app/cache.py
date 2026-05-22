import json
import os
from typing import Any, Optional

import redis


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0"
)

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)


def get_cache(key: str) -> Optional[Any]:
    try:
        cached_value = redis_client.get(key)

        if cached_value is None:
            print(f"[Redis] Cache miss: {key}")
            return None

        print(f"[Redis] Cache hit: {key}")
        return json.loads(cached_value)

    except Exception as error:
        print(f"[Redis] Failed to get cache key={key}: {error}")
        return None


def set_cache(key: str, value: Any, ttl_seconds: int = 60) -> None:
    try:
        redis_client.setex(
            key,
            ttl_seconds,
            json.dumps(value)
        )
        print(f"[Redis] Cache set: {key}, ttl={ttl_seconds}s")

    except Exception as error:
        print(f"[Redis] Failed to set cache key={key}: {error}")


def delete_cache(key: str) -> None:
    try:
        redis_client.delete(key)
        print(f"[Redis] Cache deleted: {key}")

    except Exception as error:
        print(f"[Redis] Failed to delete cache key={key}: {error}")