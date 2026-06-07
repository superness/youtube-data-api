import json
from typing import Any
from redis import Redis


def get_cached(r: Redis, key: str) -> Any | None:
    val = r.get(key)
    return json.loads(val) if val else None


def set_cached(r: Redis, key: str, data: Any, ttl: int) -> None:
    r.setex(key, ttl, json.dumps(data))
