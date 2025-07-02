import hashlib
import time
from typing import Any, Dict, Optional, Callable
from functools import wraps
import threading

class CacheManager:
    def __init__(self, max_size: int = 5000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.access_times = {}
        self.creation_times = {}
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0, 'misses': 0, 'evictions': 0, 'size': 0
        }
    
    def _generate_key(self, *args, **kwargs) -> str:
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_expired(self, key: str) -> bool:
        if key not in self.creation_times:
            return True
        return time.time() - self.creation_times[key] > self.ttl_seconds
    
    def _evict_lru(self):
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove_key(lru_key)
        self.stats['evictions'] += 1
    
    def _remove_key(self, key: str):
        if key in self.cache:
            del self.cache[key]
        if key in self.access_times:
            del self.access_times[key]
        if key in self.creation_times:
            del self.creation_times[key]
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache and not self._is_expired(key):
                self.access_times[key] = time.time()
                self.stats['hits'] += 1
                return self.cache[key]
            
            if key in self.cache:
                self._remove_key(key)
            
            self.stats['misses'] += 1
            return None
    
    def set(self, key: str, value: Any):
        with self.lock:
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            current_time = time.time()
            self.cache[key] = value
            self.access_times[key] = current_time
            self.creation_times[key] = current_time
            self.stats['size'] = len(self.cache)
    
    def cached_method(self, ttl: Optional[int] = None):
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"{func.__name__}_{self._generate_key(*args, **kwargs)}"
                
                result = self.get(cache_key)
                if result is not None:
                    return result
                
                result = func(*args, **kwargs)
                self.set(cache_key, result)
                return result
            
            return wrapper
        return decorator
    
    def clear(self):
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.creation_times.clear()
            self.stats = {'hits': 0, 'misses': 0, 'evictions': 0, 'size': 0}
    
    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                **self.stats,
                'hit_rate_percent': round(hit_rate, 2),
                'total_requests': total_requests
            }
    
    def cleanup_expired(self):
        with self.lock:
            expired_keys = [
                key for key in self.creation_times.keys()
                if self._is_expired(key)
            ]
            
            for key in expired_keys:
                self._remove_key(key)
            
            self.stats['size'] = len(self.cache)
            return len(expired_keys)

class MultiCacheManager:
    def __init__(self):
        self.caches = {}
        self.default_cache = CacheManager()
    
    def get_cache(self, name: str, max_size: int = 1000, ttl_seconds: int = 3600) -> CacheManager:
        if name not in self.caches:
            self.caches[name] = CacheManager(max_size, ttl_seconds)
        return self.caches[name]
    
    def get_global_stats(self) -> Dict[str, Any]:
        stats = {}
        for name, cache in self.caches.items():
            stats[name] = cache.get_stats()
        return stats
    
    def cleanup_all(self):
        total_cleaned = 0
        for cache in self.caches.values():
            total_cleaned += cache.cleanup_expired()
        return total_cleaned

global_cache_manager = MultiCacheManager()

def get_cache(cache_name: str = "default", max_size: int = 1000, ttl_seconds: int = 3600) -> CacheManager:
    return global_cache_manager.get_cache(cache_name, max_size, ttl_seconds)

def cached(cache_name: str = "default", ttl: int = 3600):
    cache = get_cache(cache_name, ttl_seconds=ttl)
    return cache.cached_method(ttl)