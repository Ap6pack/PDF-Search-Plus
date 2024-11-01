import os
import io
import fitz  # PyMuPDF
from PIL import Image
import easyocr
import sqlite3
from sqlite3 import Connection, Cursor
import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from typing import List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from contextlib import contextmanager

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='pdf_processor.log', filemode='a')


@dataclass
class PDFMetadata:
    """Store PDF metadata in a structured way"""
    file_name: str
    file_path: str
    id: Optional[int] = None

@contextmanager
def get_database_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect('pdf_data.db')
    try:
        yield conn
    finally:
        conn.close()

class PDFProcessor:
    def __init__(self):
        self.reader = easyocr.Reader(['en'])
    
    def insert_pdf_file(self, conn: Connection, metadata: PDFMetadata) -> int:
        """Insert metadata of the PDF file into the database."""
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pdf_files (file_name, file_path) VALUES (?, ?)",
            (metadata.file_name, metadata.file_path)
        )
        conn.commit()
        return cursor.lastrowid

    def insert_page_text(self, conn: Connection, pdf_id: int, page_number: int, text: str) -> None:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pages (pdf_id, page_number, text) VALUES (?, ?, ?)",
            (pdf_id, page_number, text)
        )
        conn.commit()

    def insert_image_metadata(
        self, conn: Connection, pdf_id: int, page_number: int,
        image_name: str, image_ext: str
    ) -> None:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO images (pdf_id, page_number, image_name, image_ext) VALUES (?, ?, ?, ?)",
            (pdf_id, page_number, image_name, image_ext)
        )
        conn.commit()

    def insert_image_ocr_text(
        self, conn: Connection, pdf_id: int, page_number: int, ocr_text: str
    ) -> None:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ocr_text (pdf_id, page_number, ocr_text) VALUES (?, ?, ?)",
            (pdf_id, page_number, ocr_text)
        )
        conn.commit()

    def extract_text_and_save(
        self, page: fitz.Page, page_number: int, conn: Connection, pdf_id: int
    ) -> None:
        """Extract and save text from a PDF page"""
        try:
            text = page.get_text()
            self.insert_page_text(conn, pdf_id, page_number, text)
        except Exception as e:
            logger.error(f"Error extracting text from page {page_number}: {e}")
            raise

    def process_image(
        self, image_bytes: bytes, image_ext: str
    ) -> Tuple[np.ndarray, Optional[str]]:
        """Process a single image and extract OCR text"""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image_np = np.array(image)
            ocr_result = self.reader.readtext(image_np)
            ocr_text = " ".join([text[1] for text in ocr_result])
            return image_np, ocr_text if ocr_text.strip() else None
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return None, None

    def extract_images_and_save(
        self, page: fitz.Page, page_number: int, conn: Connection, pdf_id: int
    ) -> None:
        """Extract and save images from a PDF page"""
        try:
            image_list = page.get_images(full=True)
            for image_index, img in enumerate(image_list, start=1):
                xref = img[0]
                base_image = page.parent.extract_image(xref)
                
                image_name = f"image_page{page_number}_{image_index}"
                self.insert_image_metadata(
                    conn, pdf_id, page_number, image_name, base_image["ext"]
                )

                _, ocr_text = self.process_image(base_image["image"], base_image["ext"])
                if ocr_text:
                    self.insert_image_ocr_text(conn, pdf_id, page_number, ocr_text)
                    logger.info(f"OCR text extracted from image {image_name}")

        except Exception as e:
            logger.error(f"Error extracting images from page {page_number}: {e}")
            raise

    def is_pdf_processed(self, conn: Connection, metadata: PDFMetadata) -> bool:
        """Check if the PDF file has already been processed"""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM pdf_files WHERE file_name = ? AND file_path = ?",
            (metadata.file_name, metadata.file_path)
        )
        return cursor.fetchone() is not None

    def process_pdf(self, metadata: PDFMetadata) -> None:
        """Process a single PDF file"""
        try:
            with get_database_connection() as conn:
                if self.is_pdf_processed(conn, metadata):
                    logger.info(f"Skipping already processed file: {metadata.file_name}")
                    return

                pdf_id = self.insert_pdf_file(conn, metadata)
                with fitz.open(metadata.file_path) as pdf_file:
                    for page_index, page in enumerate(pdf_file):
                        page_number = page_index + 1
                        self.extract_text_and_save(page, page_number, conn, pdf_id)
                        self.extract_images_and_save(page, page_number, conn, pdf_id)

                logger.info(f"Successfully processed PDF: {metadata.file_path}")

        except Exception as e:
            logger.error(f"Error processing PDF {metadata.file_path}: {e}")
            messagebox.showerror("Error", f"An error occurred while processing the PDF: {e}")
            raise

class PDFProcessorUI:
    def __init__(self):
        self.processor = PDFProcessor()
        self.root = tk.Tk()
        self.root.withdraw()

    def process_folder(self, folder_path: Path) -> None:
        """Process all PDF files in a folder"""
        if not folder_path.exists():
            logger.error(f"Folder not found: {folder_path}")
            return

        pdf_files = list(folder_path.glob("*.pdf"))
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(
                    self.processor.process_pdf,
                    PDFMetadata(f.name, str(f))
                ): f for f in pdf_files
            }

            for future in as_completed(futures):
                pdf_path = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Failed to process {pdf_path}: {e}")

    def run(self):
        """Run the PDF processor UI"""
        scan_type = messagebox.askquestion(
            "Select Scanning Type",
            "Do you want to scan a folder (mass scanning)?"
        )

        try:
            if scan_type == 'yes':
                folder_path = filedialog.askdirectory(
                    title="Select Folder with PDFs for Mass Scanning"
                )
                if folder_path:
                    self.process_folder(Path(folder_path))
            else:
                pdf_path = filedialog.askopenfilename(
                    title="Select PDF File",
                    filetypes=[("PDF Files", "*.pdf")]
                )
                if pdf_path:
                    metadata = PDFMetadata(
                        Path(pdf_path).name,
                        pdf_path
                    )
                    self.processor.process_pdf(metadata)
        
            logger.info("Processing completed successfully")
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            messagebox.showerror("Error", f"Processing failed: {e}")

def main():
    processor_ui = PDFProcessorUI()
    processor_ui.run()

if __name__ == "__main__":
    main()