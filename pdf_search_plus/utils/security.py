"""
Security utilities for the PDF Search Plus application.

This module provides functions for input validation, sanitization,
and other security-related operations.
"""

import os
import re
import html
import logging
from pathlib import Path
from typing import Optional, Union, Dict, Any, Set

# Configure logging
logger = logging.getLogger(__name__)

# Maximum allowed file size for validation (100 MB)
MAX_FILE_SIZE = 100 * 1024 * 1024


def sanitize_text(text: str) -> str:
    """
    Sanitize text to prevent XSS and other injection attacks.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
        
    # HTML escape to prevent XSS
    sanitized = html.escape(text)
    
    # Remove control characters
    sanitized = ''.join(c for c in sanitized if ord(c) >= 32 or c in '\n\r\t')
    
    return sanitized


def sanitize_search_term(term: str) -> str:
    """
    Sanitize a search term to prevent SQL injection.
    
    Args:
        term: Search term to sanitize
        
    Returns:
        Sanitized search term
    """
    if not term:
        return ""
        
    # Remove SQL injection characters
    sanitized = re.sub(r'[;\'"\\/]', '', term)
    
    # Limit length
    sanitized = sanitized[:100]
    
    return sanitized


def validate_file_path(file_path: Union[str, Path], max_size: int = MAX_FILE_SIZE) -> bool:
    """
    Validate a file path to ensure it exists, is accessible, and is safe.
    
    Args:
        file_path: Path to validate
        max_size: Maximum allowed file size in bytes
        
    Returns:
        True if the path is valid, False otherwise
    """
    if not file_path:
        logger.warning("Empty file path provided")
        return False
        
    try:
        path = Path(file_path).resolve()
        
        # Check if the path exists
        if not path.exists():
            logger.warning(f"File does not exist: {path}")
            return False
            
        # Check if it's a regular file (not a device, socket, etc.)
        if not path.is_file():
            logger.warning(f"Path is not a regular file: {path}")
            return False
            
        # Check if the file is a symbolic link pointing outside the allowed directories
        if path.is_symlink():
            real_path = path.resolve()
            # You can add additional checks here for allowed directories
            logger.info(f"File is a symbolic link: {path} -> {real_path}")
            
        # Check file size
        file_size = path.stat().st_size
        if file_size > max_size:
            logger.warning(f"File too large: {path} ({file_size} bytes)")
            return False
            
        # Check if the path is accessible
        with open(path, 'rb') as f:
            # Just try to read a byte to check access
            f.read(1)
            
        return True
    except (PermissionError, OSError) as e:
        logger.warning(f"Permission or OS error for file {file_path}: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error validating file {file_path}: {e}")
        return False


def validate_folder_path(folder_path: Union[str, Path]) -> bool:
    """
    Validate a folder path to ensure it exists, is accessible, and is safe.
    
    Args:
        folder_path: Path to validate
        
    Returns:
        True if the path is valid, False otherwise
    """
    if not folder_path:
        logger.warning("Empty folder path provided")
        return False
        
    try:
        path = Path(folder_path).resolve()
        
        # Check if the path exists and is a directory
        if not path.exists():
            logger.warning(f"Folder does not exist: {path}")
            return False
            
        if not path.is_dir():
            logger.warning(f"Path is not a directory: {path}")
            return False
            
        # Check if the directory is a symbolic link pointing outside the allowed directories
        if path.is_symlink():
            real_path = path.resolve()
            # You can add additional checks here for allowed directories
            logger.info(f"Folder is a symbolic link: {path} -> {real_path}")
            
        # Check if the path is accessible
        # Try to list the directory to check access
        next(path.iterdir(), None)
        
        return True
    except (PermissionError, OSError) as e:
        logger.warning(f"Permission or OS error for folder {folder_path}: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error validating folder {folder_path}: {e}")
        return False


def validate_pdf_file(file_path: Union[str, Path], max_size: int = MAX_FILE_SIZE) -> bool:
    """
    Validate a PDF file to ensure it exists, is accessible, and is a valid PDF.
    
    Args:
        file_path: Path to validate
        max_size: Maximum allowed file size in bytes
        
    Returns:
        True if the file is a valid PDF, False otherwise
    """
    if not validate_file_path(file_path, max_size):
        return False
        
    try:
        path = Path(file_path).resolve()
        
        # Check file extension
        if path.suffix.lower() != '.pdf':
            logger.warning(f"File does not have .pdf extension: {path}")
            return False
            
        # Check file signature (PDF files start with %PDF)
        with open(path, 'rb') as f:
            signature = f.read(4)
            if signature != b'%PDF':
                logger.warning(f"File does not have valid PDF signature: {path}")
                return False
                
        return True
    except (PermissionError, OSError) as e:
        logger.warning(f"Permission or OS error for PDF file {file_path}: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error validating PDF file {file_path}: {e}")
        return False


def is_safe_filename(filename: str) -> bool:
    """
    Check if a filename is safe (no path traversal, etc.).
    
    Args:
        filename: Filename to check
        
    Returns:
        True if the filename is safe, False otherwise
    """
    if not filename:
        logger.warning("Empty filename provided")
        return False
        
    # Check for path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        logger.warning(f"Filename contains path traversal characters: {filename}")
        return False
        
    # Check for control characters
    if any(ord(c) < 32 for c in filename):
        logger.warning(f"Filename contains control characters: {filename}")
        return False
        
    # Check for reserved filenames on Windows
    reserved: Set[str] = {
        'CON', 'PRN', 'AUX', 'NUL', 
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_without_ext = Path(filename).stem.upper()
    if name_without_ext in reserved:
        logger.warning(f"Filename is a reserved Windows name: {filename}")
        return False
        
    # Check for starting/ending with spaces or periods
    if filename.startswith((' ', '.')) or filename.endswith((' ', '.')):
        logger.warning(f"Filename starts or ends with space or period: {filename}")
        return False
        
    # Check for invalid characters
    if re.search(r'[<>:"|?*]', filename):
        logger.warning(f"Filename contains invalid characters: {filename}")
        return False
        
    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to make it safe.
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return "unnamed"
        
    # Remove path traversal characters
    sanitized = re.sub(r'[/\\]', '_', filename)
    
    # Remove control characters
    sanitized = ''.join(c for c in sanitized if ord(c) >= 32)
    
    # Remove reserved characters
    sanitized = re.sub(r'[<>:"|?*]', '_', sanitized)
    
    # Trim leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Limit length (255 is the max filename length on most filesystems)
    sanitized = sanitized[:255]
    
    # Check for reserved filenames on Windows
    reserved: Set[str] = {
        'CON', 'PRN', 'AUX', 'NUL', 
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_without_ext = Path(sanitized).stem.upper()
    if name_without_ext in reserved:
        # Add an underscore to avoid reserved names
        parts = sanitized.split('.')
        if len(parts) > 1:
            sanitized = f"{parts[0]}_." + '.'.join(parts[1:])
        else:
            sanitized = f"{sanitized}_"
    
    # Ensure the filename is not empty
    if not sanitized:
        sanitized = "unnamed"
        
    return sanitized


def validate_page_number(page_number: int, total_pages: int) -> int:
    """
    Validate and normalize a page number.
    
    Args:
        page_number: Page number to validate
        total_pages: Total number of pages
        
    Returns:
        Normalized page number (between 1 and total_pages)
    """
    if not isinstance(page_number, int):
        try:
            page_number = int(page_number)
        except (ValueError, TypeError):
            logger.warning(f"Invalid page number: {page_number}, defaulting to 1")
            return 1
    
    if page_number < 1:
        logger.warning(f"Page number {page_number} less than 1, defaulting to 1")
        return 1
        
    if total_pages > 0 and page_number > total_pages:
        logger.warning(f"Page number {page_number} greater than total pages {total_pages}, defaulting to {total_pages}")
        return total_pages
        
    return page_number


def validate_zoom_factor(zoom_factor: float, min_zoom: float = 0.5, max_zoom: float = 3.0) -> float:
    """
    Validate and normalize a zoom factor.
    
    Args:
        zoom_factor: Zoom factor to validate
        min_zoom: Minimum allowed zoom factor
        max_zoom: Maximum allowed zoom factor
        
    Returns:
        Normalized zoom factor (between min_zoom and max_zoom)
    """
    if not isinstance(zoom_factor, (int, float)):
        try:
            zoom_factor = float(zoom_factor)
        except (ValueError, TypeError):
            logger.warning(f"Invalid zoom factor: {zoom_factor}, defaulting to 1.0")
            return 1.0
    
    if zoom_factor < min_zoom:
        logger.warning(f"Zoom factor {zoom_factor} less than minimum {min_zoom}, defaulting to {min_zoom}")
        return min_zoom
        
    if zoom_factor > max_zoom:
        logger.warning(f"Zoom factor {zoom_factor} greater than maximum {max_zoom}, defaulting to {max_zoom}")
        return max_zoom
        
    return zoom_factor
