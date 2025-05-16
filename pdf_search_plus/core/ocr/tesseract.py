"""
Tesseract OCR processor implementation.
"""

import io
import subprocess
import tempfile
import os
import logging
import shutil
from pathlib import Path
from PIL import Image
from typing import Union, Optional
from contextlib import contextmanager

from pdf_search_plus.core.ocr.base import BaseOCRProcessor

# Configure logging
logger = logging.getLogger(__name__)


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
    
    @contextmanager
    def _create_secure_temp_file(self, suffix: str) -> Path:
        """
        Create a secure temporary file with proper permissions.
        
        Args:
            suffix: File suffix (e.g., '.png', '.txt')
            
        Yields:
            Path to the temporary file
        """
        temp_dir = tempfile.mkdtemp(prefix="pdf_search_")
        try:
            # Create a temporary file with restricted permissions (0o600)
            fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=temp_dir)
            os.close(fd)
            
            # Set secure permissions
            os.chmod(temp_path, 0o600)
            
            yield Path(temp_path)
        finally:
            # Clean up the temporary directory and all its contents
            try:
                shutil.rmtree(temp_dir, ignore_errors=False)
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory {temp_dir}: {e}")
    
    def extract_text(self, image_data: Union[bytes, Image.Image, str]) -> str:
        """
        Extract text from an image using Tesseract OCR.
        
        Args:
            image_data: Image data as bytes, PIL Image, or file path
            
        Returns:
            Extracted text as a string
        """
        temp_img_path: Optional[Path] = None
        temp_out_path: Optional[Path] = None
        user_provided_path = False
        
        try:
            # Handle different input types
            if isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
                with self._create_secure_temp_file('.png') as temp_path:
                    temp_img_path = temp_path
                    image.save(temp_img_path)
            elif isinstance(image_data, Image.Image):
                with self._create_secure_temp_file('.png') as temp_path:
                    temp_img_path = temp_path
                    image_data.save(temp_img_path)
            else:
                # It's already a file path
                temp_img_path = Path(image_data)
                user_provided_path = True
                
                # Validate the file exists
                if not temp_img_path.exists():
                    raise FileNotFoundError(f"Image file not found: {temp_img_path}")
            
            # Create a temporary file for the output
            with self._create_secure_temp_file('.txt') as temp_path:
                temp_out_path = temp_path
                
                # Build the command
                output_base = str(temp_out_path).replace('.txt', '')
                cmd = ['tesseract', str(temp_img_path), output_base]
                
                # Add any config parameters
                if self.config:
                    cmd.extend(self.config.split())
                
                # Run tesseract with timeout
                result = subprocess.run(
                    cmd, 
                    check=True, 
                    capture_output=True,
                    timeout=30  # Add timeout to prevent hanging
                )
                
                # Check if the output file was created
                if not temp_out_path.exists():
                    logger.warning(f"Tesseract did not create output file: {temp_out_path}")
                    return ""
                
                # Read the output
                with open(temp_out_path, 'r', encoding='utf-8') as f:
                    ocr_text = f.read()
                
                return ocr_text.strip()
        except subprocess.TimeoutExpired:
            logger.error("Tesseract OCR process timed out")
            return ""
        except subprocess.CalledProcessError as e:
            logger.error(f"Tesseract OCR process failed: {e.stderr.decode() if e.stderr else str(e)}")
            return ""
        except Exception as e:
            logger.error(f"Error in OCR processing: {e}")
            return ""
