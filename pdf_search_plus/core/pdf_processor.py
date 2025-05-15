"""
PDF processor for extracting text and images from PDF files.
"""

import os
import io
import gc
import fitz  # PyMuPDF
from PIL import Image
import logging
import time
from typing import Optional, List, Dict, Any, Tuple, Iterator, Callable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

from pdf_search_plus.core.ocr.base import BaseOCRProcessor
from pdf_search_plus.utils.db import PDFDatabase, PDFMetadata
from pdf_search_plus.utils.security import (
    sanitize_text, validate_file_path, validate_folder_path,
    validate_pdf_file, sanitize_filename
)
from pdf_search_plus.utils.cache import (
    pdf_cache, image_cache, disk_cache, memoize
)
from pdf_search_plus.utils.memory import (
    log_memory_usage, memory_usage_tracking, force_garbage_collection,
    BatchProcessor, StreamingPDFProcessor
)


class PDFProcessor:
    """
    Process PDF files to extract text and images.
    
    This class handles the extraction of text and images from PDF files,
    applies OCR to images, and stores the results in a database.
    """
    
    def __init__(self, ocr_processor: BaseOCRProcessor, db: Optional[PDFDatabase] = None):
        """
        Initialize the PDF processor.
        
        Args:
            ocr_processor: OCR processor to use for image text extraction
            db: Database manager, or None to create a new one
        """
        self.ocr_processor = ocr_processor
        self.db = db or PDFDatabase()
        self.logger = logging.getLogger(__name__)
    
    def extract_text_from_page(self, page: fitz.Page) -> str:
        """
        Extract text from a PDF page.
        
        Args:
            page: PDF page
            
        Returns:
            Extracted text
        """
        return page.get_text()
    
    def extract_images_from_page(self, page: fitz.Page) -> List[Dict[str, Any]]:
        """
        Extract images from a PDF page.
        
        Args:
            page: PDF page
            
        Returns:
            List of extracted images with metadata
        """
        result = []
        image_list = page.get_images(full=True)
        
        for image_index, img in enumerate(image_list, start=1):
            xref = img[0]
            base_image = page.parent.extract_image(xref)
            
            result.append({
                'index': image_index,
                'image_bytes': base_image["image"],
                'ext': base_image["ext"]
            })
            
        return result
    
    def process_page(self, pdf_path: str, page: fitz.Page, page_number: int, pdf_id: int) -> None:
        """
        Process a single PDF page, extracting text and images.
        
        Args:
            pdf_path: Path to the PDF file
            page: PDF page
            page_number: Page number
            pdf_id: ID of the PDF file in the database
        """
        try:
            # Extract and save text
            text = self.extract_text_from_page(page)
            self.db.insert_page_text(pdf_id, page_number, text)
            
            # Extract and process images
            images = self.extract_images_from_page(page)
            for img in images:
                image_name = f"image_page{page_number}_{img['index']}"
                
                # Save image metadata
                self.db.insert_image_metadata(
                    pdf_id, page_number, image_name, img['ext']
                )
                
                # Apply OCR and save text
                ocr_text = self.ocr_processor.process_image_bytes(img['image_bytes'])
                if ocr_text:
                    self.db.insert_image_ocr_text(pdf_id, page_number, ocr_text)
                    self.logger.info(f"OCR text extracted from image {image_name} in {pdf_path}")
        
        except Exception as e:
            self.logger.error(f"Error processing page {page_number} of {pdf_path}: {e}")
            raise
    
    @memoize
    def get_pdf_info(self, pdf_path: str) -> Dict[str, Any]:
        """
        Get information about a PDF file.
        
        This method is memoized to avoid repeatedly opening the same PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with PDF information
        """
        with fitz.open(pdf_path) as doc:
            return {
                'page_count': len(doc),
                'metadata': doc.metadata,
                'file_size': os.path.getsize(pdf_path)
            }
    
    def is_large_pdf(self, pdf_path: str, threshold_mb: int = 50) -> bool:
        """
        Check if a PDF file is considered large.
        
        Args:
            pdf_path: Path to the PDF file
            threshold_mb: Size threshold in MB
            
        Returns:
            True if the PDF is large, False otherwise
        """
        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        return file_size_mb > threshold_mb
    
    def process_pdf(self, metadata: PDFMetadata) -> None:
        """
        Process a single PDF file, extracting text and images.
        
        Args:
            metadata: PDF metadata
            
        Raises:
            ValueError: If the file path is invalid or the file is not a valid PDF
        """
        # Validate the file path
        if not validate_file_path(metadata.file_path):
            error_msg = f"Invalid file path: {metadata.file_path}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Validate that the file is a valid PDF
        if not validate_pdf_file(metadata.file_path):
            error_msg = f"Not a valid PDF file: {metadata.file_path}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
            
        try:
            # Check if already processed
            if self.db.is_pdf_processed(metadata):
                self.logger.info(f"Skipping already processed file: {metadata.file_name}")
                return
            
            # Insert PDF metadata and get ID
            pdf_id = self.db.insert_pdf_file(metadata)
            
            # Check if this is a cached PDF
            cached_pdf = pdf_cache.get(metadata.file_path)
            if cached_pdf:
                self.logger.info(f"Using cached PDF: {metadata.file_path}")
                # Process the cached PDF
                # ... (implementation would depend on what we cache)
            
            # Log memory usage before processing
            log_memory_usage(f"Before processing PDF: {metadata.file_name}")
            
            # Check if this is a large PDF
            if self.is_large_pdf(metadata.file_path):
                self.logger.info(f"Processing large PDF using streaming: {metadata.file_path}")
                
                # Use streaming processor for large PDFs
                with memory_usage_tracking(f"Processing large PDF: {metadata.file_name}"):
                    streaming_processor = StreamingPDFProcessor(max_pages_in_memory=5)
                    
                    def process_page_callback(page_index: int, page: fitz.Page) -> None:
                        page_number = page_index + 1
                        
                        # Extract text and sanitize it
                        text = sanitize_text(self.extract_text_from_page(page))
                        self.db.insert_page_text(pdf_id, page_number, text)
                        
                        # Extract and process images
                        images = self.extract_images_from_page(page)
                        
                        # Process images in batches to limit memory usage
                        batch_processor = BatchProcessor(batch_size=5)
                        
                        def process_image(img: Dict[str, Any]) -> None:
                            image_name = sanitize_filename(f"image_page{page_number}_{img['index']}")
                            
                            # Check if this image is cached
                            image_key = f"{metadata.file_path}_{page_number}_{img['index']}"
                            cached_ocr = image_cache.get(image_key)
                            
                            if cached_ocr:
                                # Use cached OCR result
                                self.logger.info(f"Using cached OCR result for {image_name}")
                                self.db.insert_image_metadata(
                                    pdf_id, page_number, image_name, img['ext']
                                )
                                self.db.insert_image_ocr_text(pdf_id, page_number, cached_ocr)
                            else:
                                # Save image metadata
                                self.db.insert_image_metadata(
                                    pdf_id, page_number, image_name, img['ext']
                                )
                                
                                # Apply OCR, sanitize the text, and save it
                                ocr_text = self.ocr_processor.process_image_bytes(img['image_bytes'])
                                if ocr_text:
                                    sanitized_ocr_text = sanitize_text(ocr_text)
                                    self.db.insert_image_ocr_text(pdf_id, page_number, sanitized_ocr_text)
                                    
                                    # Cache the OCR result
                                    image_cache.put(image_key, sanitized_ocr_text)
                                    
                                    self.logger.info(f"OCR text extracted from image {image_name}")
                        
                        # Process images in batches
                        batch_processor.process(images, process_image)
                        
                        # Force garbage collection after processing each page
                        force_garbage_collection()
                    
                    # Process the PDF using streaming
                    streaming_processor.process_pdf(metadata.file_path, process_page_callback)
            else:
                # For smaller PDFs, process normally
                with memory_usage_tracking(f"Processing PDF: {metadata.file_name}"):
                    with fitz.open(metadata.file_path) as pdf_file:
                        # Cache the PDF for future use
                        pdf_cache.put(metadata.file_path, {
                            'page_count': len(pdf_file),
                            'metadata': pdf_file.metadata
                        })
                        
                        for page_index, page in enumerate(pdf_file):
                            page_number = page_index + 1
                            
                            # Extract text and sanitize it
                            text = sanitize_text(self.extract_text_from_page(page))
                            self.db.insert_page_text(pdf_id, page_number, text)
                            
                            # Extract and process images
                            images = self.extract_images_from_page(page)
                            for img in images:
                                image_name = sanitize_filename(f"image_page{page_number}_{img['index']}")
                                
                                # Save image metadata
                                self.db.insert_image_metadata(
                                    pdf_id, page_number, image_name, img['ext']
                                )
                                
                                # Apply OCR, sanitize the text, and save it
                                ocr_text = self.ocr_processor.process_image_bytes(img['image_bytes'])
                                if ocr_text:
                                    sanitized_ocr_text = sanitize_text(ocr_text)
                                    self.db.insert_image_ocr_text(pdf_id, page_number, sanitized_ocr_text)
                                    
                                    # Cache the OCR result
                                    image_key = f"{metadata.file_path}_{page_number}_{img['index']}"
                                    image_cache.put(image_key, sanitized_ocr_text)
                                    
                                    self.logger.info(f"OCR text extracted from image {image_name}")
            
            # Log memory usage after processing
            log_memory_usage(f"After processing PDF: {metadata.file_name}")
            
            self.logger.info(f"Successfully processed PDF: {metadata.file_path}")
        
        except Exception as e:
            self.logger.error(f"Error processing PDF {metadata.file_path}: {e}")
            raise
    
    def process_folder(self, folder_path: str, max_workers: int = 5) -> None:
        """
        Process all PDF files in a folder.
        
        Args:
            folder_path: Path to the folder
            max_workers: Maximum number of worker threads
            
        Raises:
            ValueError: If the folder path is invalid
        """
        # Validate the folder path
        if not validate_folder_path(folder_path):
            error_msg = f"Invalid folder path: {folder_path}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        path = Path(folder_path)
        pdf_files = list(path.glob("*.pdf"))
        self.logger.info(f"Found {len(pdf_files)} PDF files in {folder_path}")
        
        # Validate each PDF file before processing
        valid_pdf_files = []
        for pdf_file in pdf_files:
            if validate_pdf_file(pdf_file):
                valid_pdf_files.append(pdf_file)
            else:
                self.logger.warning(f"Skipping invalid PDF file: {pdf_file}")
        
        self.logger.info(f"Processing {len(valid_pdf_files)} valid PDF files out of {len(pdf_files)} found")
        
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.process_pdf,
                    PDFMetadata(file_name=pdf_file.stem, file_path=str(pdf_file))
                ): pdf_file for pdf_file in pdf_files
            }
            
            for future in as_completed(futures):
                pdf_path = futures[future]
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Failed to process {pdf_path}: {e}")
        
        self.logger.info(f"Completed processing folder: {folder_path}")
    
    def get_pdf_metadata(self, pdf_path: str) -> PDFMetadata:
        """
        Create PDF metadata from a file path.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            PDF metadata
        """
        path = Path(pdf_path)
        return PDFMetadata(
            file_name=path.stem,
            file_path=str(path)
        )
