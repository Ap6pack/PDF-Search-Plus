"""
Caching utilities for the PDF Search Plus application.

This module provides caching mechanisms for frequently accessed data
to improve performance and reduce memory usage.
"""

import os
import time
import pickle
import functools
import threading
from typing import Dict, Any, Callable, Optional, Tuple, List, TypeVar, Generic
from pathlib import Path
import logging

# Type variables for generic caching
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

# Configure logging
logger = logging.getLogger(__name__)


class LRUCache(Generic[K, V]):
    """
    Least Recently Used (LRU) cache implementation.
    
    This cache has a maximum size and evicts the least recently used items
    when the cache is full and a new item is added.
    """
    
    def __init__(self, max_size: int = 100):
        """
        Initialize the LRU cache.
        
        Args:
            max_size: Maximum number of items to store in the cache
        """
        self.max_size = max_size
        self.cache: Dict[K, V] = {}
        self.access_times: Dict[K, float] = {}
        self.lock = threading.RLock()
        
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
                self.access_times[key] = time.time()
                return self.cache[key]
            return None
            
    def put(self, key: K, value: V) -> None:
        """
        Add an item to the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self.lock:
            # If cache is full, remove least recently used item
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()
                
            # Add or update item
            self.cache[key] = value
            self.access_times[key] = time.time()
            
    def _evict_lru(self) -> None:
        """Evict the least recently used item from the cache."""
        if not self.access_times:
            return
            
        # Find the least recently used key
        lru_key = min(self.access_times.items(), key=lambda x: x[1])[0]
        
        # Remove it from the cache
        del self.cache[lru_key]
        del self.access_times[lru_key]
        
    def clear(self) -> None:
        """Clear the cache."""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            
    def __len__(self) -> int:
        """Get the number of items in the cache."""
        return len(self.cache)


class DiskCache:
    """
    Disk-based cache for storing large objects.
    
    This cache stores items on disk to reduce memory usage while still
    providing fast access to frequently used items.
    """
    
    def __init__(self, cache_dir: str = ".cache", max_size_mb: int = 500, 
                 max_items: int = 1000):
        """
        Initialize the disk cache.
        
        Args:
            cache_dir: Directory to store cached items
            max_size_mb: Maximum cache size in megabytes
            max_items: Maximum number of items in the cache
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


def memoize(func: Callable) -> Callable:
    """
    Decorator to memoize a function.
    
    This caches the results of function calls to avoid redundant computation.
    
    Args:
        func: Function to memoize
        
    Returns:
        Memoized function
    """
    cache: Dict[Tuple, Any] = {}
    lock = threading.RLock()
    
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Create a key from the function arguments
        key = (args, tuple(sorted(kwargs.items())))
        
        with lock:
            if key in cache:
                return cache[key]
                
            result = func(*args, **kwargs)
            cache[key] = result
            return result
            
    # Add a method to clear the cache
    def clear_cache() -> None:
        with lock:
            cache.clear()
            
    wrapper.clear_cache = clear_cache  # type: ignore
    
    return wrapper


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


# Global cache instances
pdf_cache = LRUCache[str, Any](max_size=10)  # Cache for loaded PDFs
image_cache = LRUCache[str, Any](max_size=50)  # Cache for extracted images
search_cache = SearchResultCache(max_size=50, ttl=300)  # Cache for search results
disk_cache = DiskCache(cache_dir=".pdf_cache", max_size_mb=500, max_items=1000)  # Disk cache for large objects
