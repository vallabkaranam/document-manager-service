import json
import inspect
import asyncio
from typing import Any, Callable, Awaitable, Optional, Union
from redis import Redis

# Type hint for a sync or async fallback function
FallbackFunc = Union[Callable[[], Any], Callable[[], Awaitable[Any]]]


class Cache:
    """
    A Redis-based caching utility that supports both synchronous and asynchronous fallback functions,
    and handles serialization of Pydantic models, UUIDs, and datetimes.
    """

    def __init__(self, client: Redis):
        """
        Initialize the Cache instance with a Redis client.
        """
        self.client = client

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a cached value from Redis and deserialize it from JSON.
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

    async def get_or_set(
        self,
        key: str,
        fallback_func: FallbackFunc,
        ttl: int = 600
    ) -> Any:
        """
        Attempt to get a value from the cache.
        If not found, call `fallback_func` (sync or async), cache the result, and return it.

        Supports:
        - async functions (awaited)
        - sync functions (run in background using asyncio.to_thread)
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        # Dynamically resolve async or sync fallback
        if inspect.iscoroutinefunction(fallback_func):
            result = await fallback_func()
        else:
            result = await asyncio.to_thread(fallback_func)

        self.set(key, result, ttl)
        return result