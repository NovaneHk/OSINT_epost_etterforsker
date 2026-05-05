"""
Cache Manager — Redis primary with in-memory dict fallback.
All methods are synchronous to keep compatibility with the SQLite-based stack.
"""

import time
import json
import logging
from typing import Any, Callable, Optional

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheManager:
    """Thread-safe cache with Redis primary and in-memory TTL fallback."""

    def __init__(self):
        self._redis = None
        self._mem: dict[str, tuple[Any, float]] = {}  # key -> (value, expire_at)
        self._try_connect()

    def _try_connect(self):
        redis_url = getattr(settings, "REDIS_URL", None)
        if not redis_url:
            logger.info("CacheManager: REDIS_URL not set, using in-memory fallback")
            return
        try:
            import redis
            client = redis.Redis.from_url(redis_url, socket_connect_timeout=2, decode_responses=True)
            client.ping()
            self._redis = client
            logger.info("CacheManager: connected to Redis at %s", redis_url)
        except Exception as exc:
            logger.warning("CacheManager: Redis unavailable (%s), using in-memory fallback", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[str]:
        if self._redis:
            try:
                return self._redis.get(key)
            except Exception:
                pass
        # fallback
        entry = self._mem.get(key)
        if entry is None:
            return None
        value, expire_at = entry
        if expire_at < time.time():
            del self._mem[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int = 30) -> None:
        if not isinstance(value, str):
            value = json.dumps(value)
        if self._redis:
            try:
                self._redis.set(key, value, ex=ttl)
                return
            except Exception:
                pass
        self._mem[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        if self._redis:
            try:
                self._redis.delete(key)
            except Exception:
                pass
        self._mem.pop(key, None)

    def get_or_set(self, key: str, factory: Callable[[], Any], ttl: int = 30) -> Any:
        """Return cached value or call factory(), cache it, then return it."""
        cached = self.get(key)
        if cached is not None:
            try:
                return json.loads(cached)
            except (json.JSONDecodeError, TypeError):
                return cached
        value = factory()
        self.set(key, value, ttl=ttl)
        return value

    def clear_prefix(self, prefix: str) -> None:
        """Delete all keys matching prefix (best-effort)."""
        if self._redis:
            try:
                keys = self._redis.keys(f"{prefix}*")
                if keys:
                    self._redis.delete(*keys)
                return
            except Exception:
                pass
        to_delete = [k for k in list(self._mem.keys()) if k.startswith(prefix)]
        for k in to_delete:
            del self._mem[k]


# Global singleton
cache_manager = CacheManager()
