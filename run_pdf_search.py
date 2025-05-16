#!/usr/bin/env python3
"""
Entry point script for the PDF Search Plus application.

This script provides a command-line interface to the PDF Search Plus application,
allowing users to extract text from PDF files and search through them.
"""

import argparse
import sys
import os
import logging
import sqlite3
from pathlib import Path
from pdf_search_plus.main import main
from pdf_search_plus.utils.db import PDFDatabase, PDFMetadata
from pdf_search_plus.core import PDFProcessor
from pdf_search_plus.core.ocr import TesseractOCRProcessor

# Configure logging to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Get the root logger and add the console handler
root_logger = logging.getLogger()
root_logger.addHandler(console_handler)


def setup_database():
    """Set up the database if it doesn't exist or is invalid."""
    db = PDFDatabase()
    db_exists = os.path.exists('pdf_data.db')
    
    # Check if database exists and has the required tables
    if db_exists:
        try:
            # Test if the database has the required tables
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pdf_files'")
                if cursor.fetchone() is None:
                    # Database exists but doesn't have the required tables
                    logging.warning("Database exists but is missing required tables. Recreating database.")
                    os.remove('pdf_data.db')
                    db.create_database()
                    logging.info("Database recreated successfully")
                else:
                    logging.info("Using existing database")
        except sqlite3.Error as e:
            # Database exists but is corrupted or has other issues
            logging.error(f"Database error: {e}. Recreating database.")
            os.remove('pdf_data.db')
            db.create_database()
            logging.info("Database recreated successfully")
    else:
        # Database doesn't exist, create it
        db.create_database()
        logging.info("Database created successfully")
    
    return db


def process_file(file_path, db):
    """Process a single PDF file."""
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return False
    
    if not file_path.lower().endswith('.pdf'):
        logging.error(f"Not a PDF file: {file_path}")
        return False
    
    try:
        ocr_processor = TesseractOCRProcessor()
        pdf_processor = PDFProcessor(ocr_processor, db)
        
        file_name = Path(file_path).stem
        metadata = PDFMetadata(file_name=file_name, file_path=file_path)
        
        pdf_processor.process_pdf(metadata)
        logging.info(f"Successfully processed PDF: {file_path}")
        return True
    except Exception as e:
        logging.error(f"Error processing PDF {file_path}: {e}")
        return False


def process_folder(folder_path, db, max_workers=5):
    """Process all PDF files in a folder."""
    if not os.path.isdir(folder_path):
        logging.error(f"Folder not found: {folder_path}")
        return False
    
    try:
        ocr_processor = TesseractOCRProcessor()
        pdf_processor = PDFProcessor(ocr_processor, db)
        
        pdf_processor.process_folder(folder_path, max_workers=max_workers)
        logging.info(f"Successfully processed folder: {folder_path}")
        return True
    except Exception as e:
        logging.error(f"Error processing folder {folder_path}: {e}")
        return False


def search_database(search_term, db):
    """Search the database for the given term."""
    try:
        # Debug: Print the SQL query
        print("Debugging search query:")
        
        # Get the SQL query from the search_text method
        # This is a hack to get the query without executing it
        original_execute_query = db.execute_query
        
        def debug_execute_query(query, params=(), *args, **kwargs):
            print(f"SQL Query: {query}")
            print(f"Params: {params}")
            return original_execute_query(query, params, *args, **kwargs)
        
        # Replace the execute_query method temporarily
        db.execute_query = debug_execute_query
        
        # Execute the search
        results = db.search_text(search_term, use_fts=True, limit=100, offset=0)
        
        # Restore the original execute_query method
        db.execute_query = original_execute_query
        
        if not results:
            print(f"No results found for '{search_term}'")
            return
        
        print(f"Found {len(results)} results for '{search_term}':")
        for i, result in enumerate(results, 1):
            pdf_id, file_name, page_number, text, source = result
            # Truncate text if too long
            if len(text) > 100:
                text = text[:100] + "..."
            print(f"{i}. {file_name} (Page {page_number}) - {source}")
            print(f"   {text}")
            print()
    except Exception as e:
        logging.error(f"Error searching database: {e}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PDF Search Plus - PDF text extraction and search with OCR",
        epilog="Example: python run_pdf_search.py --verbose"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--process-file",
        metavar="FILE",
        help="Process a single PDF file without launching the GUI"
    )
    parser.add_argument(
        "--process-folder",
        metavar="FOLDER",
        help="Process all PDF files in a folder without launching the GUI"
    )
    parser.add_argument(
        "--search",
        metavar="TERM",
        help="Search for a term in the database without launching the GUI"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Maximum number of worker threads for batch processing (default: 5)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    # Set log level based on verbose flag
    if args.verbose:
        root_logger.setLevel(logging.DEBUG)
        logging.info("Verbose logging enabled")
    
    # Set up the database
    db = setup_database()
    
    # Handle command-line operations
    if args.process_file:
        process_file(args.process_file, db)
    elif args.process_folder:
        process_folder(args.process_folder, db, args.max_workers)
    elif args.search:
        search_database(args.search, db)
    else:
        # Run the GUI application
        main()
