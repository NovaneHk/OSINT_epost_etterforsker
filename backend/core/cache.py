"""Redis caching implementation"""
from typing import Optional, Any
import json
import redis
from datetime import timedelta

class RedisCache:
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True
        )

    def set(self, key: str, value: Any, expire_seconds: int = 3600):
        """Store value in cache with expiration"""
        try:
            serialized_value = json.dumps(value)
            self.redis_client.setex(
                name=key,
                time=timedelta(seconds=expire_seconds),
                value=serialized_value
            )
            return True
        except Exception as e:
            print(f"Redis set error: {str(e)}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache"""
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            print(f"Redis get error: {str(e)}")
        return None

    def delete(self, key: str) -> bool:
        """Remove key from cache"""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            print(f"Redis delete error: {str(e)}")
            return False

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter, useful for rate limiting"""
        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            print(f"Redis increment error: {str(e)}")
            return None

    def set_rate_limit(self, key: str, limit: int, window_seconds: int):
        """Set up rate limiting for a key"""
        try:
            current = self.increment(key)
            if current == 1:  # First request in window
                self.redis_client.expire(key, window_seconds)
            return current <= limit
        except Exception as e:
            print(f"Redis rate limit error: {str(e)}")
            return False