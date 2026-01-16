"""
PDF Search Plus - A Python application for extracting and searching text in PDF files.

This package provides tools for processing PDF files, extracting text and images,
applying OCR, and searching through the extracted content.
"""

from pdf_search_plus.core import PDFProcessor
from pdf_search_plus.core.ocr import TesseractOCRProcessor
from pdf_search_plus.gui import PDFSearchApp
from pdf_search_plus.utils.db import PDFDatabase, PDFMetadata

__version__ = "2.4.5"
