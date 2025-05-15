#!/usr/bin/env python3
"""
Entry point script for the PDF Search Plus application.

This script provides a command-line interface to the PDF Search Plus application,
allowing users to extract text from PDF files and search through them.
"""

import argparse
import sys
import logging
from pdf_search_plus.main import main

# Configure logging to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Get the root logger and add the console handler
root_logger = logging.getLogger()
root_logger.addHandler(console_handler)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PDF Search Plus - PDF text extraction and search with OCR",
        epilog="Example: python run_pdf_search.py --easyocr"
    )
    parser.add_argument(
        "--easyocr",
        action="store_true",
        help="Use EasyOCR instead of Tesseract for OCR"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    # Set log level based on verbose flag
    if args.verbose:
        root_logger.setLevel(logging.DEBUG)
        logging.info("Verbose logging enabled")
    
    # Run the application
    main(use_easyocr=args.easyocr)
