"""
Tesseract OCR processor implementation.
"""

import io
import pytesseract
from PIL import Image
from typing import Union

from pdf_search_plus.core.ocr.base import BaseOCRProcessor


class TesseractOCRProcessor(BaseOCRProcessor):
    """
    OCR processor using Tesseract.
    """
    
    def __init__(self, config: str = ''):
        """
        Initialize the Tesseract OCR processor.
        
        Args:
            config: Tesseract configuration string
        """
        self.config = config
    
    def extract_text(self, image_data: Union[bytes, Image.Image, str]) -> str:
        """
        Extract text from an image using Tesseract OCR.
        
        Args:
            image_data: Image data as bytes, PIL Image, or file path
            
        Returns:
            Extracted text as a string
        """
        if isinstance(image_data, bytes):
            image = Image.open(io.BytesIO(image_data))
        elif isinstance(image_data, str):
            image = Image.open(image_data)
        else:
            image = image_data
            
        ocr_text = pytesseract.image_to_string(image, config=self.config)
        return ocr_text.strip()
