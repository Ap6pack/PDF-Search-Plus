"""
Tesseract OCR processor implementation.
"""

import io
import subprocess
import tempfile
import os
from PIL import Image
from typing import Union

from pdf_search_plus.core.ocr.base import BaseOCRProcessor


class TesseractOCRProcessor(BaseOCRProcessor):
    """
    OCR processor using Tesseract.
    
    This implementation uses direct subprocess calls to tesseract
    instead of the pytesseract library to avoid dependency conflicts.
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
        # Create a temporary file for the image if needed
        if isinstance(image_data, bytes):
            image = Image.open(io.BytesIO(image_data))
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_img:
                temp_img_path = temp_img.name
                image.save(temp_img_path)
        elif isinstance(image_data, Image.Image):
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_img:
                temp_img_path = temp_img.name
                image_data.save(temp_img_path)
        else:
            # It's already a file path
            temp_img_path = image_data
            
        # Create a temporary file for the output
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_out:
            temp_out_path = temp_out.name
            
        try:
            # Build the command
            cmd = ['tesseract', temp_img_path, temp_out_path.replace('.txt', '')]
            
            # Add any config parameters
            if self.config:
                cmd.extend(self.config.split())
                
            # Run tesseract
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Read the output
            with open(temp_out_path, 'r', encoding='utf-8') as f:
                ocr_text = f.read()
                
            return ocr_text.strip()
        finally:
            # Clean up temporary files
            if isinstance(image_data, (bytes, Image.Image)):
                os.unlink(temp_img_path)
            os.unlink(temp_out_path)
