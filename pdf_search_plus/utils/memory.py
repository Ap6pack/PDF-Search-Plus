"""
Memory management utilities for the PDF Search Plus application.

This module provides utilities for managing memory usage, including
streaming processing, batch processing, and garbage collection.
"""

import os
import gc
import sys
import psutil
import logging
import threading
from typing import List, Dict, Any, Callable, Generator, TypeVar, Generic, Optional, Iterator
from contextlib import contextmanager

# Type variables
T = TypeVar('T')

# Configure logging
logger = logging.getLogger(__name__)


def get_memory_usage() -> Dict[str, float]:
    """
    Get current memory usage information.
    
    Returns:
        Dictionary with memory usage information in MB
    """
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    return {
        'rss': memory_info.rss / (1024 * 1024),  # Resident Set Size in MB
        'vms': memory_info.vms / (1024 * 1024),  # Virtual Memory Size in MB
        'percent': process.memory_percent(),      # Percentage of system memory
        'available': psutil.virtual_memory().available / (1024 * 1024)  # Available system memory in MB
    }


def log_memory_usage(message: str = "Memory usage") -> None:
    """
    Log current memory usage.
    
    Args:
        message: Message to include in the log
    """
    memory = get_memory_usage()
    logger.info(
        f"{message}: RSS={memory['rss']:.1f}MB, "
        f"VMS={memory['vms']:.1f}MB, "
        f"{memory['percent']:.1f}% of system memory, "
        f"{memory['available']:.1f}MB available"
    )


@contextmanager
def memory_usage_tracking(message: str = "Operation") -> Iterator[None]:
    """
    Context manager to track memory usage before and after an operation.

    Args:
        message: Description of the operation being tracked

    Yields:
        None
    """
    before = get_memory_usage()
    logger.info(f"{message} starting: RSS={before['rss']:.1f}MB")

    try:
        yield
    finally:
        after = get_memory_usage()
        diff = after['rss'] - before['rss']
        logger.info(
            f"{message} completed: RSS={after['rss']:.1f}MB, "
            f"change: {diff:.1f}MB"
        )


def force_garbage_collection() -> int:
    """
    Force garbage collection to free memory.
    
    Returns:
        Number of objects collected
    """
    # Disable automatic garbage collection during manual collection
    gc.disable()
    
    # Run garbage collection multiple times to ensure all cycles are collected
    collected = 0
    for i in range(3):
        collected += gc.collect(i)
    
    # Re-enable automatic garbage collection
    gc.enable()
    
    logger.debug(f"Garbage collection freed {collected} objects")
    return collected


class MemoryCheck:
    """
    Class to periodically check memory usage and take action if it exceeds a threshold.
    """
    
    def __init__(self, threshold_mb: float = 1000, check_interval: float = 5.0,
                 action: Callable[[], Any] = force_garbage_collection):
        """
        Initialize the memory checker.

        Args:
            threshold_mb: Memory threshold in MB
            check_interval: Check interval in seconds
            action: Function to call when memory usage exceeds the threshold (return value ignored)
        """
        self.threshold_mb = threshold_mb
        self.check_interval = check_interval
        self.action = action
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
    def start(self) -> None:
        """Start the memory checker thread."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._check_loop, daemon=True)
        self.thread.start()
        
    def stop(self) -> None:
        """Stop the memory checker thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
            
    def _check_loop(self) -> None:
        """Main loop for checking memory usage."""
        while self.running:
            memory = get_memory_usage()
            if memory['rss'] > self.threshold_mb:
                logger.warning(
                    f"Memory usage ({memory['rss']:.1f}MB) exceeds threshold "
                    f"({self.threshold_mb:.1f}MB), taking action"
                )
                self.action()
                
            # Sleep for the check interval
            for _ in range(int(self.check_interval * 10)):
                if not self.running:
                    break
                threading.Event().wait(0.1)


class BatchProcessor(Generic[T]):
    """
    Process items in batches to limit memory usage.
    """
    
    def __init__(self, batch_size: int = 10, memory_limit_mb: Optional[float] = None):
        """
        Initialize the batch processor.
        
        Args:
            batch_size: Number of items to process in each batch
            memory_limit_mb: Memory limit in MB, or None for no limit
        """
        self.batch_size = batch_size
        self.memory_limit_mb = memory_limit_mb
        
    def process(self, items: List[T], processor: Callable[[T], Any]) -> List[Any]:
        """
        Process items in batches.
        
        Args:
            items: Items to process
            processor: Function to process each item
            
        Returns:
            List of processing results
        """
        results = []
        
        # Process items in batches
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            
            # Process the batch
            batch_results = [processor(item) for item in batch]
            results.extend(batch_results)
            
            # Check memory usage if a limit is set
            if self.memory_limit_mb:
                memory = get_memory_usage()
                if memory['rss'] > self.memory_limit_mb:
                    logger.warning(
                        f"Memory usage ({memory['rss']:.1f}MB) exceeds limit "
                        f"({self.memory_limit_mb:.1f}MB), forcing garbage collection"
                    )
                    force_garbage_collection()
                    
        return results


def stream_file_reader(file_path: str, chunk_size: int = 1024 * 1024) -> Generator[bytes, None, None]:
    """
    Stream a file in chunks to limit memory usage.
    
    Args:
        file_path: Path to the file
        chunk_size: Size of each chunk in bytes
        
    Yields:
        File chunks
    """
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


class StreamingPDFProcessor:
    """
    Process PDF files in a streaming fashion to limit memory usage.
    
    This class provides methods for processing PDF files page by page
    without loading the entire file into memory.
    """
    
    def __init__(self, max_pages_in_memory: int = 5):
        """
        Initialize the streaming PDF processor.
        
        Args:
            max_pages_in_memory: Maximum number of pages to keep in memory
        """
        self.max_pages_in_memory = max_pages_in_memory
        
    def process_pdf(self, pdf_path: str, page_processor: Callable[[int, Any], None]) -> None:
        """
        Process a PDF file page by page.
        
        Args:
            pdf_path: Path to the PDF file
            page_processor: Function to process each page
        """
        import fitz  # PyMuPDF
        
        # Open the PDF file
        doc = fitz.open(pdf_path)
        
        try:
            # Process pages in batches
            for start_page in range(0, len(doc), self.max_pages_in_memory):
                end_page = min(start_page + self.max_pages_in_memory, len(doc))
                
                # Process each page in the batch
                for page_index in range(start_page, end_page):
                    page = doc.load_page(page_index)
                    page_processor(page_index, page)
                    
                # Force garbage collection after each batch
                force_garbage_collection()
                
        finally:
            # Close the document
            doc.close()


# Global memory checker instance
memory_checker = MemoryCheck(threshold_mb=1000, check_interval=5.0)
