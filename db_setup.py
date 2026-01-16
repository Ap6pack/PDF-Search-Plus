"""
Database setup script for PDF Search Plus.
"""

import os
from pdf_search_plus.utils.db import PDFDatabase

def setup_database(db_name="pdf_data.db"):
    """
    Set up the database with the latest schema.
    
    Args:
        db_name: Name of the database file to create
    """
    # Remove existing database if it exists
    if os.path.exists(db_name):
        try:
            os.remove(db_name)
            print(f"Removed existing database: {db_name}")
        except Exception as e:
            print(f"Warning: Could not remove existing database: {e}")
    
    # Create a new database with the latest schema
    # Note: Explicitly passing db_name to support custom database names
    # Other parts of the application use PDFDatabase() without arguments (relies on default)
    db = PDFDatabase(db_name)
    db.create_database()
    print(f"Database {db_name} created successfully with the latest schema.")

if __name__ == "__main__":
    setup_database()
