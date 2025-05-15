"""
Base OCR processor interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, Union, List, Tuple
import io
from PIL import Image


class BaseOCRProcessor(ABC):
    """
    Abstract base class for OCR processors.
    
    This class defines the interface that all OCR processors must implement.
    """
    
    @abstractmethod
    def extract_text(self, image_data: Union[bytes, Image.Image, str]) -> str:
        """
        Extract text from an image using OCR.
        
        Args:
            image_data: Image data as bytes, PIL Image, or file path
            
        Returns:
            Extracted text as a string
        """
        pass
    
    def process_image_bytes(self, image_bytes: bytes) -> str:
        """
        Process image bytes and extract text.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Extracted text as a string
        """
        image = Image.open(io.BytesIO(image_bytes))
        return self.extract_text(image)
