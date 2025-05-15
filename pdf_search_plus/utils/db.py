"""
Database utilities for the PDF Search Plus application.
"""

import sqlite3
import contextlib
from typing import Optional, List, Tuple, Dict, Any, Union
from dataclasses import dataclass


@dataclass
class PDFMetadata:
    """Store PDF metadata in a structured way"""
    file_name: str
    file_path: str
    id: Optional[int] = None


class PDFDatabase:
    """
    Database manager for PDF Search Plus.
    
    This class provides methods for interacting with the SQLite database
    used to store PDF data, including text and OCR results.
    """
    
    def __init__(self, db_name: str = "pdf_data.db"):
        """
        Initialize the database manager.
        
        Args:
            db_name: Name of the database file
        """
        self.db_name = db_name
    
    @contextlib.contextmanager
    def get_connection(self) -> sqlite3.Connection:
        """
        Context manager for database connections.
        
        Yields:
            A SQLite connection object
        """
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()
    
    def create_database(self) -> None:
        """Create the SQLite database and tables for storing PDF data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create tables if they don't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pdf_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pdf_id INTEGER,
                    page_number INTEGER,
                    text TEXT,
                    FOREIGN KEY(pdf_id) REFERENCES pdf_files(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pdf_id INTEGER,
                    page_number INTEGER,
                    image_name TEXT,
                    image_ext TEXT,
                    FOREIGN KEY(pdf_id) REFERENCES pdf_files(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ocr_text (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pdf_id INTEGER,
                    page_number INTEGER,
                    ocr_text TEXT,
                    FOREIGN KEY(pdf_id) REFERENCES pdf_files(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE VIEW IF NOT EXISTS summary AS
                SELECT 
                    f.file_name || '.pdf' AS file_name,
                    GROUP_CONCAT(
                        COALESCE(p.text, '') || ' ' || COALESCE(o.ocr_text, ''), 
                        ' '
                    ) AS combined_text
                FROM 
                    pdf_files f
                LEFT JOIN 
                    pages p ON f.id = p.pdf_id
                LEFT JOIN 
                    ocr_text o ON f.id = o.pdf_id AND p.page_number = o.page_number
                GROUP BY 
                    f.file_name
            ''')

            conn.commit()
            print("Database and tables created successfully with foreign key constraints.")
    
    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Tuple]]:
        """
        Execute a SQL query and return the results.
        
        Args:
            query: SQL query to execute
            params: Parameters for the query
            
        Returns:
            Query results as a list of tuples, or None for non-SELECT queries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if query.strip().upper().startswith("SELECT"):
                return cursor.fetchall()
            
            conn.commit()
            return None
    
    def insert_pdf_file(self, metadata: PDFMetadata) -> int:
        """
        Insert metadata of the PDF file into the database.
        
        Args:
            metadata: PDF metadata
            
        Returns:
            ID of the inserted PDF file
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO pdf_files (file_name, file_path) VALUES (?, ?)",
                (metadata.file_name, metadata.file_path)
            )
            conn.commit()
            return cursor.lastrowid
    
    def insert_page_text(self, pdf_id: int, page_number: int, text: str) -> None:
        """
        Insert text of a PDF page into the database.
        
        Args:
            pdf_id: ID of the PDF file
            page_number: Page number
            text: Extracted text
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO pages (pdf_id, page_number, text) VALUES (?, ?, ?)",
                (pdf_id, page_number, text)
            )
            conn.commit()
    
    def insert_image_metadata(self, pdf_id: int, page_number: int, image_name: str, image_ext: str) -> None:
        """
        Insert metadata of an extracted image into the database.
        
        Args:
            pdf_id: ID of the PDF file
            page_number: Page number
            image_name: Name of the image
            image_ext: Image extension
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO images (pdf_id, page_number, image_name, image_ext) VALUES (?, ?, ?, ?)",
                (pdf_id, page_number, image_name, image_ext)
            )
            conn.commit()
    
    def insert_image_ocr_text(self, pdf_id: int, page_number: int, ocr_text: str) -> None:
        """
        Insert OCR text extracted from an image into the database.
        
        Args:
            pdf_id: ID of the PDF file
            page_number: Page number
            ocr_text: Extracted OCR text
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ocr_text (pdf_id, page_number, ocr_text) VALUES (?, ?, ?)",
                (pdf_id, page_number, ocr_text)
            )
            conn.commit()
    
    def is_pdf_processed(self, metadata: PDFMetadata) -> bool:
        """
        Check if the PDF file has already been processed.
        
        Args:
            metadata: PDF metadata
            
        Returns:
            True if the PDF file has already been processed, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM pdf_files WHERE file_name = ? AND file_path = ?",
                (metadata.file_name, metadata.file_path)
            )
            return cursor.fetchone() is not None
    
    def get_pdf_path(self, pdf_id: int) -> Optional[str]:
        """
        Get the file path for a PDF by ID.
        
        Args:
            pdf_id: ID of the PDF file
            
        Returns:
            Path to the PDF file, or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM pdf_files WHERE id = ?", (pdf_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def search_text(self, search_term: str) -> List[Tuple]:
        """
        Search for text in both PDF text and OCR text.
        
        Args:
            search_term: Text to search for
            
        Returns:
            List of matching results
        """
        search_term = search_term.lower()
        query = """
        SELECT pdf_files.id, pdf_files.file_name, pages.page_number, pages.text, 'PDF Text' as source
        FROM pages 
        JOIN pdf_files ON pages.pdf_id = pdf_files.id 
        WHERE LOWER(pages.text) LIKE ?
        UNION
        SELECT pdf_files.id, pdf_files.file_name, ocr_text.page_number, ocr_text.ocr_text, 'OCR Text' as source
        FROM ocr_text 
        JOIN pdf_files ON ocr_text.pdf_id = pdf_files.id
        WHERE LOWER(ocr_text.ocr_text) LIKE ?
        """
        params = [f'%{search_term}%', f'%{search_term}%']
        return self.execute_query(query, params) or []


# For backward compatibility
def create_database(db_name: str = "pdf_data.db") -> None:
    """
    Create the SQLite database and tables for storing PDF data.
    
    Args:
        db_name: Name of the database file to create
    """
    db = PDFDatabase(db_name)
    db.create_database()


def get_connection(db_name: str = "pdf_data.db") -> sqlite3.Connection:
    """
    Get a connection to the SQLite database.
    
    Args:
        db_name: Name of the database file to connect to
        
    Returns:
        A SQLite connection object
    """
    conn = sqlite3.connect(db_name, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def execute_query(query: str, params: tuple = (), db_name: str = "pdf_data.db") -> Optional[list]:
    """
    Execute a SQL query and return the results.
    
    Args:
        query: SQL query to execute
        params: Parameters for the query
        db_name: Name of the database file
        
    Returns:
        Query results as a list of tuples, or None for non-SELECT queries
    """
    db = PDFDatabase(db_name)
    return db.execute_query(query, params)
