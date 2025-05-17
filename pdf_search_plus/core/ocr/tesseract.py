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
from typing import Union, Optional, Tuple
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
        self._temp_dirs = []
    
    def _create_secure_temp_directory(self) -> str:
        """
        Create a secure temporary directory with proper permissions.
        
        Returns:
            Path to the temporary directory
        """
        temp_dir = tempfile.mkdtemp(prefix="pdf_search_")
        os.chmod(temp_dir, 0o700)  # Secure permissions for directory
        self._temp_dirs.append(temp_dir)
        return temp_dir
    
    def _create_secure_temp_file(self, suffix: str, temp_dir: Optional[str] = None) -> Tuple[str, Path]:
        """
        Create a secure temporary file with proper permissions.
        
        Args:
            suffix: File suffix (e.g., '.png', '.txt')
            temp_dir: Directory to create the file in, or None to create a new one
            
        Returns:
            Tuple of (temp_dir, temp_file_path)
        """
        if temp_dir is None:
            temp_dir = self._create_secure_temp_directory()
        
        # Create a temporary file with restricted permissions (0o600)
        fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=temp_dir)
        os.close(fd)
        
        # Set secure permissions
        os.chmod(temp_path, 0o600)
        
        return temp_dir, Path(temp_path)
    
    def _cleanup_temp_directories(self):
        """
        Clean up all temporary directories created by this processor.
        """
        for temp_dir in self._temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=False)
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory {temp_dir}: {e}")
        
        # Clear the list of temporary directories
        self._temp_dirs = []
    
    def extract_text(self, image_data: Union[bytes, Image.Image, str]) -> str:
        """
        Extract text from an image using Tesseract OCR.
        
        Args:
            image_data: Image data as bytes, PIL Image, or file path
            
        Returns:
            Extracted text as a string
        """
        temp_dir = None
        temp_img_path = None
        temp_out_path = None
        user_provided_path = False
        ocr_text = ""
        
        try:
            # Handle different input types
            if isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
                temp_dir, temp_img_path = self._create_secure_temp_file('.png')
                image.save(temp_img_path)
            elif isinstance(image_data, Image.Image):
                temp_dir, temp_img_path = self._create_secure_temp_file('.png')
                image_data.save(temp_img_path)
            else:
                # It's already a file path
                temp_img_path = Path(image_data)
                user_provided_path = True
                
                # Validate the file exists
                if not temp_img_path.exists():
                    raise FileNotFoundError(f"Image file not found: {temp_img_path}")
            
            # Create a temporary file for the output in the same directory
            # to ensure it's not deleted before Tesseract can use it
            if temp_dir:
                _, temp_out_path = self._create_secure_temp_file('.txt', temp_dir)
            else:
                temp_dir, temp_out_path = self._create_secure_temp_file('.txt')
            
            # Build the command
            output_base = str(temp_out_path).replace('.txt', '')
            cmd = ['tesseract', str(temp_img_path), output_base]
            
            # Add any config parameters
            if self.config:
                cmd.extend(self.config.split())
            
            # Verify the input file exists before running Tesseract
            if not os.path.exists(str(temp_img_path)):
                raise FileNotFoundError(f"Input image file does not exist: {temp_img_path}")
            
            # Run tesseract with timeout
            result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=True,
                timeout=30  # Add timeout to prevent hanging
            )
            
            # Check if the output file was created
            if not os.path.exists(str(temp_out_path)):
                logger.warning(f"Tesseract did not create output file: {temp_out_path}")
                return ""
            
            # Read the output
            with open(temp_out_path, 'r', encoding='utf-8') as f:
                ocr_text = f.read().strip()
        except subprocess.TimeoutExpired:
            logger.error("Tesseract OCR process timed out")
            return ""
        except subprocess.CalledProcessError as e:
            logger.error(f"Tesseract OCR process failed: {e.stderr.decode() if e.stderr else str(e)}")
            return ""
        except Exception as e:
            logger.error(f"Error in OCR processing: {e}")
            return ""
        finally:
            # Only clean up if we created the temporary files
            # and we're done with them
            if not user_provided_path and temp_dir:
                try:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=False)
                    # Remove from the list of directories to clean up later
                    if temp_dir in self._temp_dirs:
                        self._temp_dirs.remove(temp_dir)
                except Exception as e:
                    logger.error(f"Error cleaning up temporary directory {temp_dir}: {e}")
        
        return ocr_text
    
    def __del__(self):
        """
        Clean up any remaining temporary directories when the processor is destroyed.
        """
        self._cleanup_temp_directories()
