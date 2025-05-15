"""
EasyOCR processor implementation.
"""

import io
import numpy as np
import easyocr
from PIL import Image
from typing import Union, List, Optional

from pdf_search_plus.core.ocr.base import BaseOCRProcessor


class EasyOCRProcessor(BaseOCRProcessor):
    """
    OCR processor using EasyOCR.
    """
    
    def __init__(self, languages: List[str] = None):
        """
        Initialize the EasyOCR processor.
        
        Args:
            languages: List of language codes to use for OCR
        """
        if languages is None:
            languages = ['en']
        self.languages = languages
        self.reader = easyocr.Reader(languages)
    
    def extract_text(self, image_data: Union[bytes, Image.Image, str, np.ndarray]) -> str:
        """
        Extract text from an image using EasyOCR.
        
        Args:
            image_data: Image data as bytes, PIL Image, file path, or numpy array
            
        Returns:
            Extracted text as a string
        """
        # Convert to numpy array if needed
        if isinstance(image_data, bytes):
            image = Image.open(io.BytesIO(image_data))
            image_np = np.array(image)
        elif isinstance(image_data, Image.Image):
            image_np = np.array(image_data)
        elif isinstance(image_data, str):
            # It's a file path
            image_np = image_data  # EasyOCR can handle file paths directly
        else:
            # Assume it's already a numpy array
            image_np = image_data
            
        # Perform OCR
        ocr_result = self.reader.readtext(image_np)
        
        # Extract text from results
        if ocr_result:
            ocr_text = " ".join([text[1] for text in ocr_result])
            return ocr_text.strip()
        
        return ""
