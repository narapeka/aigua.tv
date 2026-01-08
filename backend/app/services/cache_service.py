"""
Cache Service
Thread-safe job result caching with Redis support
"""

import json
import threading
from typing import Optional, Dict, Any
from datetime import timedelta


class CacheService:
    """
    Thread-safe cache service for job results

    Supports both Redis (production) and in-memory dict (development)
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize cache service

        Args:
            redis_url: Optional Redis URL (e.g., redis://localhost:6379)
                      If None, uses in-memory cache
        """
        self.use_redis = False
        self.redis = None

        if redis_url:
            try:
                import redis
                self.redis = redis.from_url(redis_url, decode_responses=True)
                self.use_redis = True
                print(f"✓ Connected to Redis at {redis_url}")
            except ImportError:
                print("⚠ Redis not installed, falling back to in-memory cache")
                self.use_redis = False
            except Exception as e:
                print(f"⚠ Failed to connect to Redis: {e}, falling back to in-memory cache")
                self.use_redis = False

        if not self.use_redis:
            self.cache: Dict[str, Any] = {}
            self._lock = threading.Lock()
            print("✓ Using in-memory cache")

    def set_job(self, job_id: str, data: Dict[str, Any], ttl: int = 3600) -> None:
        """
        Store job result with TTL

        Args:
            job_id: Job identifier
            data: Job data dict
            ttl: Time to live in seconds (default 1 hour)
        """
        if self.use_redis:
            self.redis.setex(
                f"job:{job_id}",
                timedelta(seconds=ttl),
                json.dumps(data)
            )
        else:
            with self._lock:
                self.cache[job_id] = data

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve job result

        Args:
            job_id: Job identifier

        Returns:
            Job data dict or None if not found
        """
        if self.use_redis:
            data = self.redis.get(f"job:{job_id}")
            if data:
                return json.loads(data)
            return None
        else:
            with self._lock:
                return self.cache.get(job_id)

    def update_job(self, job_id: str, data: Dict[str, Any], ttl: int = 3600) -> None:
        """
        Update existing job data

        Args:
            job_id: Job identifier
            data: Updated job data dict
            ttl: Time to live in seconds (default 1 hour)
        """
        self.set_job(job_id, data, ttl)

    def delete_job(self, job_id: str) -> None:
        """
        Delete job data

        Args:
            job_id: Job identifier
        """
        if self.use_redis:
            self.redis.delete(f"job:{job_id}")
        else:
            with self._lock:
                self.cache.pop(job_id, None)

    def exists(self, job_id: str) -> bool:
        """
        Check if job exists in cache

        Args:
            job_id: Job identifier

        Returns:
            True if job exists
        """
        if self.use_redis:
            return bool(self.redis.exists(f"job:{job_id}"))
        else:
            with self._lock:
                return job_id in self.cache

    def clear_all(self) -> None:
        """Clear all cached jobs (use with caution)"""
        if self.use_redis:
            # Delete all keys with job: prefix
            for key in self.redis.scan_iter("job:*"):
                self.redis.delete(key)
        else:
            with self._lock:
                self.cache.clear()


# Global cache instance
_cache_instance: Optional[CacheService] = None


def get_cache_service(redis_url: Optional[str] = None) -> CacheService:
    """
    Get or create cache service singleton

    Args:
        redis_url: Optional Redis URL (only used on first call)

    Returns:
        CacheService instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService(redis_url=redis_url)
    return _cache_instance
