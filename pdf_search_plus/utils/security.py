"""
Security utilities for the PDF Search Plus application.

This module provides functions for input validation, sanitization,
and other security-related operations.
"""

import os
import re
import html
from pathlib import Path
from typing import Optional, Union, Dict, Any


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


def validate_file_path(file_path: Union[str, Path]) -> bool:
    """
    Validate a file path to ensure it exists and is accessible.
    
    Args:
        file_path: Path to validate
        
    Returns:
        True if the path is valid, False otherwise
    """
    if not file_path:
        return False
        
    path = Path(file_path)
    
    # Check if the path exists
    if not path.exists():
        return False
        
    # Check if the path is accessible
    try:
        if path.is_file():
            with open(path, 'rb') as f:
                # Just try to read a byte to check access
                f.read(1)
        return True
    except (PermissionError, OSError):
        return False


def validate_folder_path(folder_path: Union[str, Path]) -> bool:
    """
    Validate a folder path to ensure it exists and is accessible.
    
    Args:
        folder_path: Path to validate
        
    Returns:
        True if the path is valid, False otherwise
    """
    if not folder_path:
        return False
        
    path = Path(folder_path)
    
    # Check if the path exists and is a directory
    if not path.exists() or not path.is_dir():
        return False
        
    # Check if the path is accessible
    try:
        # Try to list the directory to check access
        next(path.iterdir(), None)
        return True
    except (PermissionError, OSError):
        return False


def validate_pdf_file(file_path: Union[str, Path]) -> bool:
    """
    Validate a PDF file to ensure it exists, is accessible, and is a valid PDF.
    
    Args:
        file_path: Path to validate
        
    Returns:
        True if the file is a valid PDF, False otherwise
    """
    if not validate_file_path(file_path):
        return False
        
    path = Path(file_path)
    
    # Check file extension
    if path.suffix.lower() != '.pdf':
        return False
        
    # Check file signature (PDF files start with %PDF)
    try:
        with open(path, 'rb') as f:
            signature = f.read(4)
            return signature == b'%PDF'
    except (PermissionError, OSError):
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
        return False
        
    # Check for path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
        
    # Check for control characters
    if any(ord(c) < 32 for c in filename):
        return False
        
    # Check for reserved filenames on Windows
    reserved = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3',
                'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    
    name_without_ext = Path(filename).stem.upper()
    if name_without_ext in reserved:
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
    
    # Limit length
    sanitized = sanitized[:255]
    
    # Ensure the filename is not empty
    if not sanitized:
        sanitized = "unnamed"
        
    return sanitized
