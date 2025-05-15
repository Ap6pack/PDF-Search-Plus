"""
Utility functions and helpers for the PDF Search Plus application.
"""

from pdf_search_plus.utils.db import PDFDatabase, PDFMetadata, create_database, get_connection, execute_query
from pdf_search_plus.utils.security import (
    sanitize_text, sanitize_search_term, validate_file_path, validate_folder_path,
    validate_pdf_file, is_safe_filename, sanitize_filename
)

__all__ = [
    # Database utilities
    'PDFDatabase', 'PDFMetadata', 'create_database', 'get_connection', 'execute_query',
    
    # Security utilities
    'sanitize_text', 'sanitize_search_term', 'validate_file_path', 'validate_folder_path',
    'validate_pdf_file', 'is_safe_filename', 'sanitize_filename'
]
