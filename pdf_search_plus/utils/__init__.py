"""
Utility functions and helpers for the PDF Search Plus application.
"""

from pdf_search_plus.utils.db import PDFDatabase, PDFMetadata, create_database, get_connection, execute_query
from pdf_search_plus.utils.security import (
    sanitize_text, sanitize_search_term, validate_file_path, validate_folder_path,
    validate_pdf_file, is_safe_filename, sanitize_filename
)
from pdf_search_plus.utils.cache import (
    LRUCache, DiskCache, memoize, SearchResultCache,
    pdf_cache, image_cache, search_cache, disk_cache
)
from pdf_search_plus.utils.memory import (
    get_memory_usage, log_memory_usage, memory_usage_tracking,
    force_garbage_collection, MemoryCheck, BatchProcessor,
    stream_file_reader, StreamingPDFProcessor, memory_checker
)

__all__ = [
    # Database utilities
    'PDFDatabase', 'PDFMetadata', 'create_database', 'get_connection', 'execute_query',
    
    # Security utilities
    'sanitize_text', 'sanitize_search_term', 'validate_file_path', 'validate_folder_path',
    'validate_pdf_file', 'is_safe_filename', 'sanitize_filename',
    
    # Caching utilities
    'LRUCache', 'DiskCache', 'memoize', 'SearchResultCache',
    'pdf_cache', 'image_cache', 'search_cache', 'disk_cache',
    
    # Memory management utilities
    'get_memory_usage', 'log_memory_usage', 'memory_usage_tracking',
    'force_garbage_collection', 'MemoryCheck', 'BatchProcessor',
    'stream_file_reader', 'StreamingPDFProcessor', 'memory_checker'
]
