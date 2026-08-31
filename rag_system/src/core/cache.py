# src/core/cache.py - simple LRU cache
import hashlib
import json
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Optional, Any

class SimpleCache:
    """Simple LRU cache"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()

    def _get_key(self, query: str, context: dict) -> str:
        """Generate cache key"""
        key_str = f"{query}_{json.dumps(context, sort_keys=True)}"
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()

    def get(self, query: str, context: dict) -> Optional[Any]:
        """Get from cache"""
        key = self._get_key(query, context)
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                # Move to the end (LRU)
                self.cache.move_to_end(key)
                return value
            else:
                del self.cache[key]
        return None

    def set(self, query: str, context: dict, value: Any):
        """Set cache"""
        key = self._get_key(query, context)
        self.cache[key] = (value, datetime.now())
        self.cache.move_to_end(key)

        # If it exceeds the max size, remove the oldest
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self):
        """Clear the cache"""
        self.cache.clear()

# Global cache instance
query_cache = SimpleCache(max_size=50, ttl_seconds=300)  # 5-minute TTL
