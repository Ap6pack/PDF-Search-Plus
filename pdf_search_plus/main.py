"""
Main entry point for the PDF Search Plus application.
"""

import os
import argparse
import tkinter as tk
from tkinter import filedialog, messagebox
import logging
import threading
from pathlib import Path
from typing import Optional

from pdf_search_plus.core import PDFProcessor
from pdf_search_plus.core.ocr import TesseractOCRProcessor, EasyOCRProcessor
from pdf_search_plus.gui import PDFSearchApp
from pdf_search_plus.utils.db import PDFDatabase, PDFMetadata


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='pdf_search_plus.log',
    filemode='a'
)
logger = logging.getLogger(__name__)


class PDFSearchPlusApp:
    """
    Main application class for PDF Search Plus.
    
    This class manages the main application window and provides
    access to the PDF processing and search functionality.
    """
    
    def __init__(self, use_easyocr: bool = False):
        """
        Initialize the application.
        
        Args:
            use_easyocr: Whether to use EasyOCR instead of Tesseract
        """
        self.use_easyocr = use_easyocr
        self.db = PDFDatabase()
        
        # Create the OCR processor
        if use_easyocr:
            self.ocr_processor = EasyOCRProcessor()
            logger.info("Using EasyOCR for text extraction")
        else:
            self.ocr_processor = TesseractOCRProcessor()
            logger.info("Using Tesseract for text extraction")
        
        # Create the PDF processor
        self.pdf_processor = PDFProcessor(self.ocr_processor, self.db)
        
        # Set up the database
        self.setup_database()
        
        # Create the main window
        self.root = tk.Tk()
        self.root.title("PDF Search Plus")
        self.root.geometry("400x200")
        
        # Create the main application frame
        self.create_main_window()
    
    def setup_database(self) -> None:
        """Set up the database if it doesn't exist."""
        if not os.path.exists('pdf_data.db'):
            self.db.create_database()
            logger.info("Database created successfully")
    
    def create_main_window(self) -> None:
        """Create the main application window."""
        # Create a frame for the buttons
        frame = tk.Frame(self.root)
        frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        # Add a title label
        title_label = tk.Label(
            frame, 
            text="PDF Search Plus", 
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(pady=10)
        
        # Add a subtitle with OCR engine info
        ocr_engine = "EasyOCR" if self.use_easyocr else "Tesseract"
        subtitle_label = tk.Label(
            frame,
            text=f"Using {ocr_engine} for OCR",
            font=("Helvetica", 10)
        )
        subtitle_label.pack(pady=5)
        
        # Add buttons for processing and searching
        button_frame = tk.Frame(frame)
        button_frame.pack(pady=10)
        
        process_button = tk.Button(
            button_frame,
            text="Process PDF",
            command=self.show_processing_dialog,
            width=15,
            height=2
        )
        process_button.grid(row=0, column=0, padx=10, pady=5)
        
        search_button = tk.Button(
            button_frame,
            text="Search PDFs",
            command=self.show_search_window,
            width=15,
            height=2
        )
        search_button.grid(row=0, column=1, padx=10, pady=5)
        
        # Add a status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = tk.Label(
            self.root, 
            textvariable=self.status_var, 
            bd=1, 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def process_pdf_file(self, pdf_path: str) -> None:
        """
        Process a single PDF file.
        
        Args:
            pdf_path: Path to the PDF file
        """
        try:
            self.status_var.set(f"Processing: {Path(pdf_path).name}...")
            
            # Create metadata
            metadata = PDFMetadata(
                file_name=Path(pdf_path).stem,
                file_path=pdf_path
            )
            
            # Process the PDF
            self.pdf_processor.process_pdf(metadata)
            
            logger.info(f"Successfully processed PDF: {pdf_path}")
            self.status_var.set(f"Processed: {Path(pdf_path).name}")
            messagebox.showinfo("Success", f"Successfully processed PDF: {Path(pdf_path).name}")
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            self.status_var.set("Error processing PDF")
            messagebox.showerror("Error", f"An error occurred while processing the PDF: {e}")
    
    def process_pdf_folder(self, folder_path: str) -> None:
        """
        Process all PDF files in a folder.
        
        Args:
            folder_path: Path to the folder
        """
        try:
            self.status_var.set(f"Processing folder: {Path(folder_path).name}...")
            
            # Process the folder
            self.pdf_processor.process_folder(folder_path)
            
            logger.info(f"Successfully processed folder: {folder_path}")
            self.status_var.set(f"Processed folder: {Path(folder_path).name}")
            messagebox.showinfo("Success", "Successfully processed all PDFs in the folder")
        except Exception as e:
            logger.error(f"Error processing folder {folder_path}: {e}")
            self.status_var.set("Error processing folder")
            messagebox.showerror("Error", f"An error occurred while processing the folder: {e}")
    
    def show_processing_dialog(self) -> None:
        """Show a dialog to select a PDF file or folder for processing."""
        scan_type = messagebox.askquestion(
            "Select Scanning Type", 
            "Do you want to scan a folder (mass scanning)?"
        )
        
        if scan_type == 'yes':
            folder_path = filedialog.askdirectory(
                title="Select Folder with PDFs for Mass Scanning"
            )
            if folder_path:
                # Process the folder in a separate thread to avoid freezing the UI
                threading.Thread(
                    target=self.process_pdf_folder,
                    args=(folder_path,)
                ).start()
        else:
            pdf_path = filedialog.askopenfilename(
                title="Select PDF File",
                filetypes=[("PDF Files", "*.pdf")]
            )
            if pdf_path:
                # Process the PDF in a separate thread to avoid freezing the UI
                threading.Thread(
                    target=self.process_pdf_file,
                    args=(pdf_path,)
                ).start()
    
    def show_search_window(self) -> None:
        """Show the PDF search window."""
        search_window = tk.Toplevel(self.root)
        search_window.title("PDF Search")
        search_window.geometry("1000x700")
        
        # Create the search app with the same database
        search_app = PDFSearchApp(search_window, self.db)
        
        # Make the window modal
        search_window.transient(self.root)
        search_window.grab_set()
        
        # Wait for the window to be closed
        self.root.wait_window(search_window)
    
    def run(self) -> None:
        """Run the application."""
        self.root.mainloop()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PDF Search Plus - PDF text extraction and search with OCR"
    )
    parser.add_argument(
        "--easyocr",
        action="store_true",
        help="Use EasyOCR instead of Tesseract for OCR"
    )
    return parser.parse_args()


def main(use_easyocr: bool = False) -> None:
    """
    Main entry point for the application.
    
    Args:
        use_easyocr: Whether to use EasyOCR instead of Tesseract
    """
    try:
        app = PDFSearchPlusApp(use_easyocr=use_easyocr)
        app.run()
    except Exception as e:
        logger.error(f"Application error: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")


if __name__ == "__main__":
    args = parse_args()
    main(use_easyocr=args.easyocr)
