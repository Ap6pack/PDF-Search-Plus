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

    # Maximum image dimensions for OCR (to prevent timeouts)
    # Aggressive limits to prevent timeouts
    MAX_IMAGE_WIDTH = 1000
    MAX_IMAGE_HEIGHT = 1000

    # Skip images larger than this BEFORE optimization (in pixels)
    # Extremely large images take too long even after resizing
    SKIP_ORIGINAL_IMAGE_THRESHOLD = 3000 * 3000  # 9 megapixels

    def __init__(self, config: str = '', timeout: int = 360, skip_large_images: bool = True):
        """
        Initialize the Tesseract OCR processor.

        Args:
            config: Tesseract configuration string (default uses fast settings)
            timeout: OCR processing timeout in seconds (default: 360)
            skip_large_images: Skip images that are very large/complex to prevent timeouts
        """
        # Use faster Tesseract settings if no config provided
        if not config:
            # PSM 3 = Fully automatic page segmentation (default)
            # OEM 1 = Neural nets LSTM engine (faster than legacy)
            config = '--psm 3 --oem 1'

        self.config = config
        self.timeout = timeout
        self.skip_large_images = skip_large_images
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

    def _optimize_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Optimize an image for OCR processing.

        Performs multiple optimizations:
        1. Converts to grayscale (faster OCR, often more accurate)
        2. Resizes if too large (prevents timeouts)
        3. Enhances contrast (improves text recognition)

        Args:
            image: PIL Image to optimize

        Returns:
            Optimized PIL Image
        """
        from PIL import ImageEnhance

        width, height = image.size
        original_size = f"{width}x{height}"

        # Convert to grayscale for faster OCR
        if image.mode != 'L':
            logger.debug(f"Converting image from {image.mode} to grayscale")
            image = image.convert('L')

        # Check if image exceeds maximum dimensions and resize if needed
        if width > self.MAX_IMAGE_WIDTH or height > self.MAX_IMAGE_HEIGHT:
            # Calculate scaling factor to fit within max dimensions
            scale_width = self.MAX_IMAGE_WIDTH / width
            scale_height = self.MAX_IMAGE_HEIGHT / height
            scale = min(scale_width, scale_height)

            # Calculate new dimensions
            new_width = int(width * scale)
            new_height = int(height * scale)

            logger.info(f"Resizing image from {original_size} to {new_width}x{new_height} for OCR")

            # Resize using high-quality resampling
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            logger.debug(f"Image size {original_size} is within limits, no resizing needed")

        # Enhance contrast to improve text recognition
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)  # Increase contrast by 50%

        return image
    
    def extract_text(self, image_data: Union[bytes, Image.Image, str]) -> str:
        """
        Extract text from an image using Tesseract OCR.

        Args:
            image_data: Image data as bytes, PIL Image, or file path

        Returns:
            Extracted text as a string
        """
        import time

        temp_dir = None
        temp_img_path = None
        temp_out_path = None
        user_provided_path = False
        ocr_text = ""
        start_time = time.time()

        try:
            # Handle different input types
            if isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
                original_size = image.size

                # Check if original image is too large BEFORE optimization
                if self.skip_large_images:
                    original_pixel_count = original_size[0] * original_size[1]
                    if original_pixel_count >= self.SKIP_ORIGINAL_IMAGE_THRESHOLD:
                        logger.warning(
                            f"Skipping very large image ({original_size[0]}x{original_size[1]}={original_pixel_count:,} pixels) "
                            f"before optimization to prevent timeout"
                        )
                        return ""

                # Optimize image size before OCR
                image = self._optimize_image_for_ocr(image)

                temp_dir, temp_img_path = self._create_secure_temp_file('.png')
                image.save(temp_img_path)
            elif isinstance(image_data, Image.Image):
                original_size = image_data.size

                # Check if original image is too large BEFORE optimization
                if self.skip_large_images:
                    original_pixel_count = original_size[0] * original_size[1]
                    if original_pixel_count >= self.SKIP_ORIGINAL_IMAGE_THRESHOLD:
                        logger.warning(
                            f"Skipping very large image ({original_size[0]}x{original_size[1]}={original_pixel_count:,} pixels) "
                            f"before optimization to prevent timeout"
                        )
                        return ""

                # Optimize image size before OCR
                image = self._optimize_image_for_ocr(image_data)

                temp_dir, temp_img_path = self._create_secure_temp_file('.png')
                image.save(temp_img_path)
            else:
                # It's already a file path
                temp_img_path = Path(image_data)
                user_provided_path = True

                # Validate the file exists
                if not temp_img_path.exists():
                    raise FileNotFoundError(f"Image file not found: {temp_img_path}")

                # Load the image
                image = Image.open(temp_img_path)
                original_size = image.size

                # Check if original image is too large BEFORE optimization
                if self.skip_large_images:
                    original_pixel_count = original_size[0] * original_size[1]
                    if original_pixel_count >= self.SKIP_ORIGINAL_IMAGE_THRESHOLD:
                        logger.warning(
                            f"Skipping very large image ({original_size[0]}x{original_size[1]}={original_pixel_count:,} pixels) "
                            f"before optimization to prevent timeout"
                        )
                        return ""

                # Optimize the image
                optimized = self._optimize_image_for_ocr(image)

                # If optimization changed the image, save it to a temp file
                if optimized is not image:
                    user_provided_path = False
                    temp_dir, new_temp_path = self._create_secure_temp_file('.png')
                    optimized.save(new_temp_path)
                    temp_img_path = new_temp_path
            
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

            # Log the OCR attempt
            logger.info(f"Starting Tesseract OCR (timeout: {self.timeout}s, config: {self.config})")

            # Run tesseract with timeout
            ocr_start = time.time()
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                timeout=self.timeout  # Use configurable timeout
            )
            ocr_duration = time.time() - ocr_start

            # Check if the output file was created
            if not os.path.exists(str(temp_out_path)):
                logger.warning(f"Tesseract did not create output file: {temp_out_path}")
                return ""

            # Read the output
            with open(temp_out_path, 'r', encoding='utf-8') as f:
                ocr_text = f.read().strip()

            # Log success with timing
            char_count = len(ocr_text)
            logger.info(f"OCR completed in {ocr_duration:.2f}s, extracted {char_count} characters")
        except subprocess.TimeoutExpired:
            logger.error(f"Tesseract OCR process timed out after {self.timeout} seconds")
            logger.info("Consider increasing timeout or checking image complexity")
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
