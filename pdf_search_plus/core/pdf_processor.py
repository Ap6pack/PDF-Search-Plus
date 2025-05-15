"""
PDF processor for extracting text and images from PDF files.
"""

import os
import io
import fitz  # PyMuPDF
from PIL import Image
import logging
from typing import Optional, List, Dict, Any, Tuple, Iterator
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from pdf_search_plus.core.ocr.base import BaseOCRProcessor
from pdf_search_plus.utils.db import PDFDatabase, PDFMetadata


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
    
    def process_pdf(self, metadata: PDFMetadata) -> None:
        """
        Process a single PDF file, extracting text and images.
        
        Args:
            metadata: PDF metadata
        """
        try:
            # Check if already processed
            if self.db.is_pdf_processed(metadata):
                self.logger.info(f"Skipping already processed file: {metadata.file_name}")
                return
            
            # Insert PDF metadata and get ID
            pdf_id = self.db.insert_pdf_file(metadata)
            
            # Process each page
            with fitz.open(metadata.file_path) as pdf_file:
                for page_index, page in enumerate(pdf_file):
                    page_number = page_index + 1
                    self.process_page(metadata.file_path, page, page_number, pdf_id)
            
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
        """
        path = Path(folder_path)
        if not path.exists():
            self.logger.error(f"Folder not found: {folder_path}")
            return
        
        pdf_files = list(path.glob("*.pdf"))
        self.logger.info(f"Found {len(pdf_files)} PDF files in {folder_path}")
        
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
