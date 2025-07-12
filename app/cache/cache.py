import json
from typing import Any, Callable, Optional, List
from redis import Redis


class Cache:
    def __init__(self, client: Redis):
        self.client = client

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a cached value from Redis and deserialize it.
        """
        value = self.client.get(key)
        if value is None:
            return None
        return json.loads(value)

    def set(self, key: str, value: Any, ttl: int = 600) -> None:
        """
        Serialize and cache a value in Redis with optional TTL.
        Supports Pydantic v2 models and common Python types.
        """
        # Handle list of Pydantic models
        if isinstance(value, list) and all(hasattr(item, "model_dump") for item in value):
            value = [item.model_dump() for item in value]
        # Handle single Pydantic model
        elif hasattr(value, "model_dump"):
            value = value.model_dump()

        # Use default=str to handle UUID, datetime, etc.
        serialized = json.dumps(value, default=str)
        self.client.set(key, serialized, ex=ttl)

    def delete(self, key: str) -> None:
        """
        Delete a cached key from Redis.
        """
        self.client.delete(key)

    def get_or_set(
        self,
        key: str,
        fallback_func: Callable[[], Any],
        ttl: int = 600
    ) -> Any:
        """
        Attempt to get a value from the cache.
        If not found, call `fallback_func`, cache the result, and return it.
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        data = fallback_func()
        self.set(key, data, ttl)
        return data