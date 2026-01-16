"""
Main entry point for the PDF Search Plus application.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox
import logging
import threading
import sqlite3
from pathlib import Path
from typing import Optional

from pdf_search_plus.core import PDFProcessor
from pdf_search_plus.core.ocr import TesseractOCRProcessor
from pdf_search_plus.gui import PDFSearchApp
from pdf_search_plus.utils.db import PDFDatabase, PDFMetadata
from pdf_search_plus.utils.security import (
    validate_file_path, validate_folder_path, validate_pdf_file,
    sanitize_filename
)


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
    
    def __init__(self):
        """
        Initialize the application.
        """
        self.db = PDFDatabase()
        
        # Create the OCR processor
        self.ocr_processor = TesseractOCRProcessor()
        logger.info("Using Tesseract for text extraction")
        
        # Create the PDF processor
        self.pdf_processor = PDFProcessor(self.ocr_processor, self.db)
        
        # Set up the database
        self.setup_database()
        
        # Keep track of background threads
        self.background_threads = []
        
        # Create the main window
        self.root = tk.Tk()
        self.root.title("PDF Search Plus")
        self.root.geometry("400x200")
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create the main application frame
        self.create_main_window()
    
    def setup_database(self) -> None:
        """Set up the database if it doesn't exist or is invalid."""
        db_exists = os.path.exists('pdf_data.db')
        
        # Check if database exists and has the required tables
        if db_exists:
            try:
                # Test if the database has the required tables
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pdf_files'")
                    if cursor.fetchone() is None:
                        # Database exists but doesn't have the required tables
                        logger.warning("Database exists but is missing required tables. Recreating database.")
                        os.remove('pdf_data.db')
                        self.db.create_database()
                        logger.info("Database recreated successfully")
                    else:
                        logger.info("Using existing database")
            except sqlite3.Error as e:
                # Database exists but is corrupted or has other issues
                logger.error(f"Database error: {e}. Recreating database.")
                os.remove('pdf_data.db')
                self.db.create_database()
                logger.info("Database recreated successfully")
        else:
            # Database doesn't exist, create it
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
        subtitle_label = tk.Label(
            frame,
            text="Using Tesseract for OCR",
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
        # Validate the file path
        if not validate_file_path(pdf_path):
            error_msg = f"Invalid file path: {pdf_path}"
            logger.error(error_msg)
            self.status_var.set("Error: Invalid file path")
            messagebox.showerror("Invalid File", error_msg)
            return
            
        # Validate that the file is a valid PDF
        if not validate_pdf_file(pdf_path):
            error_msg = f"Not a valid PDF file: {pdf_path}"
            logger.error(error_msg)
            self.status_var.set("Error: Invalid PDF file")
            messagebox.showerror("Invalid PDF", error_msg)
            return
            
        try:
            # Update status
            file_name = sanitize_filename(Path(pdf_path).stem)
            self.status_var.set(f"Processing: {file_name}...")
            
            # Create metadata with sanitized filename
            metadata = PDFMetadata(
                file_name=file_name,
                file_path=pdf_path
            )
            
            # Process the PDF
            self.pdf_processor.process_pdf(metadata)
            
            # Update status and log success
            logger.info(f"Successfully processed PDF: {pdf_path}")
            self.status_var.set(f"Processed: {file_name}")
            messagebox.showinfo("Success", f"Successfully processed PDF: {file_name}")
        except ValueError as e:
            # Handle validation errors
            logger.error(f"Validation error processing PDF {pdf_path}: {e}")
            self.status_var.set("Error: Invalid PDF file")
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            # Handle other errors
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            self.status_var.set("Error processing PDF")
            messagebox.showerror("Error", "An error occurred while processing the PDF file.")
    
    def process_pdf_folder(self, folder_path: str) -> None:
        """
        Process all PDF files in a folder.
        
        Args:
            folder_path: Path to the folder
        """
        # Validate the folder path
        if not validate_folder_path(folder_path):
            error_msg = f"Invalid folder path: {folder_path}"
            logger.error(error_msg)
            self.status_var.set("Error: Invalid folder path")
            messagebox.showerror("Invalid Folder", error_msg)
            return
            
        try:
            # Update status
            folder_name = sanitize_filename(Path(folder_path).name)
            self.status_var.set(f"Processing folder: {folder_name}...")
            
            # Process the folder
            self.pdf_processor.process_folder(folder_path)
            
            # Update status and log success
            logger.info(f"Successfully processed folder: {folder_path}")
            self.status_var.set(f"Processed folder: {folder_name}")
            messagebox.showinfo("Success", "Successfully processed all PDFs in the folder")
        except ValueError as e:
            # Handle validation errors
            logger.error(f"Validation error processing folder {folder_path}: {e}")
            self.status_var.set("Error: Invalid folder")
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            # Handle other errors
            logger.error(f"Error processing folder {folder_path}: {e}")
            self.status_var.set("Error processing folder")
            messagebox.showerror("Error", "An error occurred while processing the folder.")
    
    def show_processing_dialog(self) -> None:
        """Show a dialog to select a PDF file or folder for processing."""
        scan_type = messagebox.askquestion(
            "Select Scanning Type", 
            "Do you want to scan a folder (mass scanning)?"
        )
        
        if scan_type == 'yes':
            # Select a folder for batch processing
            folder_path = filedialog.askdirectory(
                title="Select Folder with PDFs for Mass Scanning"
            )
            
            if not folder_path:
                # User cancelled the dialog
                return
                
            # Validate the folder path
            if not validate_folder_path(folder_path):
                error_msg = f"Invalid folder path: {folder_path}"
                logger.error(error_msg)
                messagebox.showerror("Invalid Folder", error_msg)
                return
                
            # Check if the folder contains any PDF files
            pdf_files = list(Path(folder_path).glob("*.pdf"))
            if not pdf_files:
                warning_msg = f"No PDF files found in the selected folder: {folder_path}"
                logger.warning(warning_msg)
                messagebox.showwarning("No PDFs Found", warning_msg)
                return
                
            # Process the folder in a separate thread to avoid freezing the UI
            thread = threading.Thread(
                target=self.process_pdf_folder,
                args=(folder_path,),
                daemon=True  # Make thread a daemon so it exits when main thread exits
            )
            self.background_threads.append(thread)
            thread.start()
        else:
            # Select a single PDF file
            pdf_path = filedialog.askopenfilename(
                title="Select PDF File",
                filetypes=[("PDF Files", "*.pdf")]
            )
            
            if not pdf_path:
                # User cancelled the dialog
                return
                
            # Validate the file path
            if not validate_file_path(pdf_path):
                error_msg = f"Invalid file path: {pdf_path}"
                logger.error(error_msg)
                messagebox.showerror("Invalid File", error_msg)
                return
                
            # Validate that the file is a valid PDF
            if not validate_pdf_file(pdf_path):
                error_msg = f"Not a valid PDF file: {pdf_path}"
                logger.error(error_msg)
                messagebox.showerror("Invalid PDF", error_msg)
                return
                
            # Process the PDF in a separate thread to avoid freezing the UI
            thread = threading.Thread(
                target=self.process_pdf_file,
                args=(pdf_path,),
                daemon=True  # Make thread a daemon so it exits when main thread exits
            )
            self.background_threads.append(thread)
            thread.start()
    
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
    
    def on_closing(self):
        """Handle window closing event."""
        logger.info("Application closing, cleaning up resources...")
        
        # Clean up any resources
        try:
            # Join any non-daemon threads with a timeout
            for thread in self.background_threads:
                if thread.is_alive() and not thread.daemon:
                    logger.info(f"Waiting for background thread to finish...")
                    thread.join(0.5)  # Wait for 0.5 seconds max
            
            # Clean up the OCR processor resources
            if hasattr(self.ocr_processor, '_cleanup_temp_directories'):
                self.ocr_processor._cleanup_temp_directories()
            
            logger.info("Cleanup completed, closing application")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        # Destroy the root window
        self.root.destroy()
    
    def run(self) -> None:
        """Run the application."""
        try:
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            # Ensure cleanup happens even if mainloop exits unexpectedly
            logger.info("Main loop exited, performing final cleanup")
            
            # Force cleanup of any remaining resources
            if hasattr(self.ocr_processor, '_cleanup_temp_directories'):
                self.ocr_processor._cleanup_temp_directories()


def main() -> None:
    """
    Main entry point for the application.
    """
    try:
        app = PDFSearchPlusApp()
        app.run()
    except Exception as e:
        logger.error(f"Application error: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")


if __name__ == "__main__":
    main()
