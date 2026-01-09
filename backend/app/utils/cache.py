"""Caching utilities for LLM responses and rate limiting."""
import hashlib
import json
from typing import Any
from app.config import settings

# In-memory fallback cache if Redis is unavailable
_memory_cache: dict[str, tuple[Any, float]] = {}


class CacheManager:
    """Manages caching with Redis or in-memory fallback."""

    def __init__(self):
        """Initialize cache manager with Redis or in-memory fallback."""
        self.redis_client = None
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection if available."""
        if not settings.redis_url:
            return

        try:
            import redis
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2
            )
            # Test connection
            self.redis_client.ping()
        except Exception as e:
            print(f"Redis connection failed, using in-memory cache: {e}")
            self.redis_client = None

    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                print(f"Redis get error: {e}")

        # Fallback to memory cache
        import time
        if key in _memory_cache:
            value, expiry = _memory_cache[key]
            if time.time() < expiry:
                return value
            else:
                del _memory_cache[key]

        return None

    def set(self, key: str, value: Any, ttl: int | None = None):
        """Set value in cache with optional TTL (seconds)."""
        if ttl is None:
            ttl = settings.cache_ttl_seconds

        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, json.dumps(value))
                return
            except Exception as e:
                print(f"Redis set error: {e}")

        # Fallback to memory cache
        import time
        _memory_cache[key] = (value, time.time() + ttl)

    def delete(self, key: str):
        """Delete value from cache."""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                return
            except Exception as e:
                print(f"Redis delete error: {e}")

        # Fallback to memory cache
        if key in _memory_cache:
            del _memory_cache[key]

    def clear(self):
        """Clear all cache."""
        if self.redis_client:
            try:
                self.redis_client.flushdb()
                return
            except Exception as e:
                print(f"Redis clear error: {e}")

        # Fallback to memory cache
        _memory_cache.clear()

    @staticmethod
    def generate_llm_cache_key(
        provider: str,
        model: str,
        prompt: str,
        temperature: float = 0.0
    ) -> str:
        """Generate cache key for LLM response."""
        key_data = f"{provider}:{model}:{temperature}:{prompt}"
        hash_value = hashlib.sha256(key_data.encode()).hexdigest()
        return f"llm_cache:{hash_value}"


# Global cache instance
cache = CacheManager()
