#!/usr/bin/env python3
"""
Thread-safe in-memory cache for TV show metadata
Provides caching for TMDB metadata to avoid redundant API calls.

Author: Kilo Code
"""

import threading
from typing import Optional, Dict
from tmdb import TVShowMetadata


class TVShowCache:
    """Thread-safe in-memory cache for TV show metadata"""
    
    def __init__(self):
        """
        Initialize the cache
        
        Cache is unbounded (no size limit) and thread-safe.
        """
        self._cache: Dict[str, TVShowMetadata] = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[TVShowMetadata]:
        """
        Get cached TV show metadata by key
        
        Args:
            key: Cache key (folder name or TMDB ID as string)
            
        Returns:
            TVShowMetadata if found, None otherwise
        """
        with self._lock:
            return self._cache.get(key)
    
    def put(self, key: str, value: TVShowMetadata) -> None:
        """
        Store TV show metadata in cache
        
        Args:
            key: Cache key (folder name or TMDB ID as string)
            value: TVShowMetadata to cache
        """
        with self._lock:
            self._cache[key] = value
    
    def clear(self) -> None:
        """Clear all cached entries"""
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """
        Get the number of cached entries
        
        Returns:
            Number of entries in cache
        """
        with self._lock:
            return len(self._cache)
