"""
OCR (Optical Character Recognition) functionality for extracting text from images.
"""

from pdf_search_plus.core.ocr.base import BaseOCRProcessor
from pdf_search_plus.core.ocr.tesseract import TesseractOCRProcessor
from pdf_search_plus.core.ocr.easyocr import EasyOCRProcessor

__all__ = ['BaseOCRProcessor', 'TesseractOCRProcessor', 'EasyOCRProcessor']
