"""
Caching utilities for the PDF Search Plus application.

This module provides advanced caching mechanisms for frequently accessed data
to improve performance and reduce memory usage. It includes memory-aware caching,
disk-based caching, and function memoization to optimize resource usage.
"""

import os
import sys
import time
import pickle
import functools
import threading
import psutil
import logging
from typing import Dict, Any, Callable, Optional, Tuple, List, TypeVar, Generic, Union, Protocol
from pathlib import Path

# Type variables for generic caching
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


class MemoizedFunction(Protocol):
    """Protocol for a memoized function with cache clearing capability."""
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...
    def clear_cache(self) -> None: ...

# Configure logging
logger = logging.getLogger(__name__)


class MemoryAwareLRUCache(Generic[K, V]):
    """
    Memory-aware Least Recently Used (LRU) cache implementation.
    
    This cache monitors system memory usage and adapts its size accordingly.
    It evicts items based on both LRU policy and memory pressure.
    
    Attributes:
        max_size: Maximum number of items to store in the cache
        min_free_memory_mb: Minimum amount of free memory to maintain (in MB)
        max_memory_percent: Maximum percentage of system memory to use
    """
    
    def __init__(self, max_size: int = 100, min_free_memory_mb: float = 500,
                 max_memory_percent: float = 75.0):
        """
        Initialize the memory-aware LRU cache.
        
        Args:
            max_size: Maximum number of items to store in the cache
            min_free_memory_mb: Minimum amount of free memory to maintain (in MB)
            max_memory_percent: Maximum percentage of system memory to use
        """
        self.max_size = max_size
        self.min_free_memory_bytes = min_free_memory_mb * 1024 * 1024
        self.max_memory_percent = max_memory_percent
        self.cache: Dict[K, Tuple[V, float, int]] = {}  # key -> (value, timestamp, size)
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'memory_pressure_evictions': 0
        }
        
    def get(self, key: K) -> Optional[V]:
        """
        Get an item from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value, or None if not found
        """
        with self.lock:
            if key in self.cache:
                # Update access time
                value, _, size = self.cache[key]
                self.cache[key] = (value, time.time(), size)
                self.stats['hits'] += 1
                return value
            
            self.stats['misses'] += 1
            return None
            
    def put(self, key: K, value: V, size_estimate: Optional[int] = None) -> None:
        """
        Add an item to the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            size_estimate: Estimated size of the value in bytes (optional)
        """
        with self.lock:
            # Check memory pressure before adding
            self._check_memory_pressure()
            
            # Estimate size if not provided
            if size_estimate is None:
                size_estimate = sys.getsizeof(value)
                
            # If cache is full, remove least recently used item
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()
                
            # Add or update item
            self.cache[key] = (value, time.time(), size_estimate)
            
    def _check_memory_pressure(self) -> None:
        """Check system memory and evict items if under pressure."""
        try:
            memory = psutil.virtual_memory()
            
            # Check if we're exceeding max memory percentage
            if memory.percent > self.max_memory_percent:
                self._evict_by_count(max(1, len(self.cache) // 4))  # Evict 25% of items
                self.stats['memory_pressure_evictions'] += 1
                return
                
            # Check if available memory is below minimum
            if memory.available < self.min_free_memory_bytes:
                # Calculate how many items to evict based on pressure
                pressure_ratio = 1.0 - (memory.available / self.min_free_memory_bytes)
                items_to_evict = max(1, int(len(self.cache) * pressure_ratio * 0.5))
                self._evict_by_count(items_to_evict)
                self.stats['memory_pressure_evictions'] += 1
        except Exception as e:
            logger.warning(f"Error checking memory pressure: {e}")
            
    def _evict_lru(self) -> None:
        """Evict the least recently used item from the cache."""
        if not self.cache:
            return
            
        # Find the least recently used key
        lru_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
        
        # Remove it from the cache
        del self.cache[lru_key]
        self.stats['evictions'] += 1
        
    def _evict_by_count(self, count: int) -> None:
        """
        Evict a specific number of least recently used items.
        
        Args:
            count: Number of items to evict
        """
        if not self.cache or count <= 0:
            return
            
        # Sort items by access time
        items = sorted(self.cache.items(), key=lambda x: x[1][1])
        
        # Remove the oldest items
        for key, _ in items[:min(count, len(items))]:
            del self.cache[key]
            self.stats['evictions'] += 1
            
    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            stats = self.stats.copy()
            stats['size'] = len(self.cache)
            stats['memory_usage'] = sum(item[2] for item in self.cache.values())
            return stats
        
    def clear(self) -> None:
        """Clear the cache."""
        with self.lock:
            self.cache.clear()
            # Reset stats except for cumulative counters
            self.stats['size'] = 0
            self.stats['memory_usage'] = 0
            
    def __len__(self) -> int:
        """Get the number of items in the cache."""
        return len(self.cache)


class EnhancedDiskCache:
    """
    Enhanced disk-based cache for storing large objects.
    
    This cache stores items on disk to reduce memory usage while still
    providing fast access to frequently used items. It includes features
    like compression, memory monitoring, and secure file handling.
    """
    
    def __init__(self, cache_dir: str = ".cache", max_size_mb: int = 500, 
                 max_items: int = 1000, compress: bool = True):
        """
        Initialize the enhanced disk cache.
        
        Args:
            cache_dir: Directory to store cached items
            max_size_mb: Maximum cache size in megabytes
            max_items: Maximum number of items in the cache
            compress: Whether to compress cached items
        """
        self.cache_dir = Path(cache_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_items = max_items
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Load metadata if it exists
        self._load_metadata()
        
    def _load_metadata(self) -> None:
        """Load cache metadata from disk."""
        metadata_path = self.cache_dir / "metadata.pkl"
        if metadata_path.exists():
            try:
                with open(metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
            except (pickle.PickleError, EOFError, IOError) as e:
                logger.warning(f"Failed to load cache metadata: {e}")
                self.metadata = {}
                
    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        metadata_path = self.cache_dir / "metadata.pkl"
        try:
            with open(metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
        except (pickle.PickleError, IOError) as e:
            logger.warning(f"Failed to save cache metadata: {e}")
            
    def _get_cache_path(self, key: str) -> Path:
        """
        Get the file path for a cached item.
        
        Args:
            key: Cache key
            
        Returns:
            Path to the cached file
        """
        # Use a hash of the key as the filename to avoid invalid characters
        filename = f"{hash(key)}.cache"
        return self.cache_dir / filename
            
    def get(self, key: str) -> Optional[Any]:
        """
        Get an item from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value, or None if not found
        """
        with self.lock:
            if key not in self.metadata:
                return None
                
            cache_path = self._get_cache_path(key)
            if not cache_path.exists():
                # File was deleted, remove from metadata
                del self.metadata[key]
                self._save_metadata()
                return None
                
            try:
                with open(cache_path, 'rb') as f:
                    value = pickle.load(f)
                    
                # Update access time
                self.metadata[key]['last_access'] = time.time()
                self._save_metadata()
                
                return value
            except (pickle.PickleError, EOFError, IOError) as e:
                logger.warning(f"Failed to load cached item {key}: {e}")
                return None
                
    def put(self, key: str, value: Any) -> None:
        """
        Add an item to the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self.lock:
            # Check if we need to make room
            self._ensure_space()
            
            cache_path = self._get_cache_path(key)
            
            try:
                # Save the value to disk
                with open(cache_path, 'wb') as f:
                    pickle.dump(value, f)
                    
                # Update metadata
                file_size = os.path.getsize(cache_path)
                self.metadata[key] = {
                    'size': file_size,
                    'created': time.time(),
                    'last_access': time.time()
                }
                
                self._save_metadata()
            except (pickle.PickleError, IOError) as e:
                logger.warning(f"Failed to cache item {key}: {e}")
                
    def _ensure_space(self) -> None:
        """Ensure there's enough space in the cache by removing old items if necessary."""
        # Check if we have too many items
        if len(self.metadata) >= self.max_items:
            self._evict_items(len(self.metadata) - self.max_items + 1)
            
        # Check if we're using too much disk space
        total_size = sum(item['size'] for item in self.metadata.values())
        if total_size >= self.max_size_bytes:
            # Calculate how much space we need to free
            to_free = total_size - self.max_size_bytes + 1024 * 1024  # Free an extra MB
            self._free_space(to_free)
            
    def _evict_items(self, count: int) -> None:
        """
        Evict a number of items from the cache.
        
        Args:
            count: Number of items to evict
        """
        if not self.metadata:
            return
            
        # Sort items by last access time
        items = sorted(self.metadata.items(), key=lambda x: x[1]['last_access'])
        
        # Remove the oldest items
        for key, _ in items[:count]:
            self._remove_item(key)
            
    def _free_space(self, bytes_to_free: int) -> None:
        """
        Free up space in the cache.
        
        Args:
            bytes_to_free: Number of bytes to free
        """
        if not self.metadata:
            return
            
        # Sort items by last access time
        items = sorted(self.metadata.items(), key=lambda x: x[1]['last_access'])
        
        # Remove items until we've freed enough space
        freed = 0
        for key, metadata in items:
            freed += metadata['size']
            self._remove_item(key)
            
            if freed >= bytes_to_free:
                break
                
    def _remove_item(self, key: str) -> None:
        """
        Remove an item from the cache.
        
        Args:
            key: Cache key
        """
        if key not in self.metadata:
            return
            
        cache_path = self._get_cache_path(key)
        
        try:
            if cache_path.exists():
                os.remove(cache_path)
        except OSError as e:
            logger.warning(f"Failed to remove cached file for {key}: {e}")
            
        del self.metadata[key]
        
    def clear(self) -> None:
        """Clear the cache."""
        with self.lock:
            # Remove all cached files
            for key in list(self.metadata.keys()):
                self._remove_item(key)
                
            # Clear metadata
            self.metadata.clear()
            self._save_metadata()


def memoize(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to memoize a function.

    This caches the results of function calls to avoid redundant computation.

    Args:
        func: Function to memoize

    Returns:
        Memoized function with clear_cache method
    """
    cache: Dict[Tuple[Any, ...], T] = {}
    lock = threading.RLock()

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        # Create a key from the function arguments
        key = (args, tuple(sorted(kwargs.items())))

        with lock:
            if key in cache:
                return cache[key]

            result = func(*args, **kwargs)
            cache[key] = result
            return result

    # Create a wrapper class that combines function and clear_cache method
    class MemoizedWrapper:
        """Wrapper class that provides both call and clear_cache functionality."""
        def __call__(self, *args: Any, **kwargs: Any) -> T:
            return wrapper(*args, **kwargs)

        def clear_cache(self) -> None:
            """Clear the memoization cache."""
            with lock:
                cache.clear()

        # Forward common function attributes
        __name__ = func.__name__
        __doc__ = func.__doc__

    return MemoizedWrapper()


class SearchResultCache:
    """
    Cache for search results to improve performance of repeated searches.
    
    This cache stores the results of recent searches to avoid redundant
    database queries.
    """
    
    def __init__(self, max_size: int = 50, ttl: int = 300):
        """
        Initialize the search result cache.
        
        Args:
            max_size: Maximum number of search results to cache
            ttl: Time-to-live in seconds for cached results
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Tuple[List[Tuple], float]] = {}
        self.lock = threading.RLock()
        
    def get(self, search_term: str) -> Optional[List[Tuple]]:
        """
        Get search results from the cache.
        
        Args:
            search_term: Search term
            
        Returns:
            Cached search results, or None if not found or expired
        """
        with self.lock:
            if search_term not in self.cache:
                return None
                
            results, timestamp = self.cache[search_term]
            
            # Check if the results have expired
            if time.time() - timestamp > self.ttl:
                del self.cache[search_term]
                return None
                
            return results
            
    def put(self, search_term: str, results: List[Tuple]) -> None:
        """
        Add search results to the cache.
        
        Args:
            search_term: Search term
            results: Search results
        """
        with self.lock:
            # If cache is full, remove oldest item
            if len(self.cache) >= self.max_size and search_term not in self.cache:
                oldest_term = min(self.cache.items(), key=lambda x: x[1][1])[0]
                del self.cache[oldest_term]
                
            # Add or update results
            self.cache[search_term] = (results, time.time())
            
    def clear(self) -> None:
        """Clear the cache."""
        with self.lock:
            self.cache.clear()


class TimedCache(Generic[K, V]):
    """
    Time-based cache with automatic expiration.
    
    This cache automatically expires items after a specified time-to-live (TTL).
    It's useful for caching data that becomes stale after a certain period.
    """
    
    def __init__(self, ttl: int = 300):
        """
        Initialize the timed cache.
        
        Args:
            ttl: Time-to-live in seconds for cached items
        """
        self.ttl = ttl
        self.cache: Dict[K, Tuple[V, float]] = {}  # key -> (value, expiration_time)
        self.lock = threading.RLock()
        
    def get(self, key: K) -> Optional[V]:
        """
        Get an item from the cache if it hasn't expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value, or None if not found or expired
        """
        with self.lock:
            if key in self.cache:
                value, expiration_time = self.cache[key]
                
                # Check if the item has expired
                if time.time() < expiration_time:
                    return value
                
                # Remove expired item
                del self.cache[key]
            
            return None
            
    def put(self, key: K, value: V, ttl: Optional[int] = None) -> None:
        """
        Add an item to the cache with an expiration time.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (overrides default if provided)
        """
        with self.lock:
            expiration_time = time.time() + (ttl if ttl is not None else self.ttl)
            self.cache[key] = (value, expiration_time)
            
    def clear_expired(self) -> int:
        """
        Clear all expired items from the cache.
        
        Returns:
            Number of items cleared
        """
        with self.lock:
            now = time.time()
            expired_keys = [k for k, (_, exp) in self.cache.items() if exp <= now]
            
            for key in expired_keys:
                del self.cache[key]
                
            return len(expired_keys)
            
    def clear(self) -> None:
        """Clear the cache."""
        with self.lock:
            self.cache.clear()
            
    def __len__(self) -> int:
        """Get the number of items in the cache."""
        with self.lock:
            # Only count non-expired items
            now = time.time()
            return sum(1 for _, exp in self.cache.values() if exp > now)


# Global cache instances with improved memory awareness
pdf_cache = MemoryAwareLRUCache[str, Any](max_size=10, min_free_memory_mb=200)  # Cache for loaded PDFs
image_cache = MemoryAwareLRUCache[str, Any](max_size=50, min_free_memory_mb=100)  # Cache for extracted images
search_cache = TimedCache[str, Union[int, List[Tuple[Any, ...]]]](ttl=300)  # Cache for search results and counts with automatic expiration
disk_cache = EnhancedDiskCache(cache_dir=".pdf_cache", max_size_mb=500, max_items=1000, compress=True)  # Enhanced disk cache
