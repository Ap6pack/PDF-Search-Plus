"""
Database utilities for the PDF Search Plus application.

This module provides classes and functions for interacting with the SQLite database
used to store PDF data, including text content, OCR results, and metadata.
It includes functionality for creating the database schema, executing queries,
and performing common operations like searching and retrieving PDF information.
"""

import sqlite3
import contextlib
import re
import html
from typing import Optional, List, Tuple, Dict, Any, Union
from dataclasses import dataclass
from pathlib import Path

from pdf_search_plus.utils.security import sanitize_text, sanitize_search_term


@dataclass
class PDFMetadata:
    """
    Store PDF metadata in a structured way.
    
    This class encapsulates metadata about a PDF file, including its name,
    path, and optional ID. It also handles sanitization of the file name
    and ensures the file path is stored as a string.
    
    Attributes:
        file_name: The name of the PDF file (without extension)
        file_path: The full path to the PDF file
        id: Optional database ID for the PDF file
    """
    file_name: str
    file_path: str
    id: Optional[int] = None
    
    def __post_init__(self):
        """Validate and sanitize metadata after initialization."""
        # Sanitize file name
        self.file_name = sanitize_text(self.file_name)
        
        # Ensure file path is a string
        if isinstance(self.file_path, Path):
            self.file_path = str(self.file_path)


class PDFDatabase:
    """
    Database manager for PDF Search Plus.
    
    This class provides methods for interacting with the SQLite database
    used to store PDF data, including text and OCR results. It handles
    database creation, connection management, and provides methods for
    common operations like searching, inserting, and retrieving data.
    
    The database schema includes tables for PDF files, pages, images,
    and OCR text, as well as full-text search virtual tables for efficient
    text searching.
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
        """
        Create the SQLite database and tables for storing PDF data.
        
        This method creates the following tables if they don't exist:
        - pdf_files: Stores metadata for each processed PDF file
        - pages: Stores text extracted from each PDF page
        - images: Stores metadata about extracted images from PDFs
        - ocr_text: Stores text extracted via OCR from images
        
        It also creates FTS5 virtual tables for full-text search and
        appropriate indexes for better performance.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create tables if they don't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pdf_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tags table for document categorization
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    color TEXT DEFAULT '#808080',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Categories table (hierarchical organization)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    parent_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(parent_id) REFERENCES categories(id) ON DELETE CASCADE
                )
            ''')
            
            # PDF-Tag relationships (many-to-many)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pdf_tags (
                    pdf_id INTEGER,
                    tag_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(pdf_id, tag_id),
                    FOREIGN KEY(pdf_id) REFERENCES pdf_files(id) ON DELETE CASCADE,
                    FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
                )
            ''')
            
            # PDF-Category relationships (many-to-many)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pdf_categories (
                    pdf_id INTEGER,
                    category_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(pdf_id, category_id),
                    FOREIGN KEY(pdf_id) REFERENCES pdf_files(id) ON DELETE CASCADE,
                    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
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

            # Create optimized virtual tables for full-text search
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS fts_content USING fts5(
                    pdf_id UNINDEXED,
                    page_number UNINDEXED,
                    content,
                    source UNINDEXED,
                    tokenize='porter unicode61'
                )
            ''')

            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS fts_ocr USING fts5(
                    pdf_id UNINDEXED,
                    page_number UNINDEXED,
                    content,
                    source UNINDEXED,
                    tokenize='porter unicode61'
                )
            ''')

            # Create optimized indexes for better performance
            # Compound indexes for common query patterns
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pages_pdf_page ON pages(pdf_id, page_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ocr_pdf_page ON ocr_text(pdf_id, page_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_pdf_page ON images(pdf_id, page_number)')
            
            # Indexes for text search when not using FTS
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pages_text ON pages(text)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ocr_text_ocr_text ON ocr_text(ocr_text)')
            
            # Indexes for file lookup
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pdf_files_file_name ON pdf_files(file_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pdf_files_file_path ON pdf_files(file_path)')
            
            # Index for sorting by last accessed
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pdf_files_last_accessed ON pdf_files(last_accessed DESC)')

            # Create a view for combined text
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

            # Optimized triggers to update FTS tables
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS pages_ai AFTER INSERT ON pages BEGIN
                    INSERT INTO fts_content(pdf_id, page_number, content, source)
                    VALUES (new.pdf_id, new.page_number, new.text, 'PDF Text');
                END
            ''')

            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS pages_ad AFTER DELETE ON pages BEGIN
                    DELETE FROM fts_content WHERE pdf_id = old.pdf_id AND page_number = old.page_number;
                END
            ''')

            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS pages_au AFTER UPDATE ON pages BEGIN
                    UPDATE fts_content SET content = new.text
                    WHERE pdf_id = old.pdf_id AND page_number = old.page_number;
                END
            ''')

            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS ocr_text_ai AFTER INSERT ON ocr_text BEGIN
                    INSERT INTO fts_ocr(pdf_id, page_number, content, source)
                    VALUES (new.pdf_id, new.page_number, new.ocr_text, 'OCR Text');
                END
            ''')

            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS ocr_text_ad AFTER DELETE ON ocr_text BEGIN
                    DELETE FROM fts_ocr WHERE pdf_id = old.pdf_id AND page_number = old.page_number;
                END
            ''')

            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS ocr_text_au AFTER UPDATE ON ocr_text BEGIN
                    UPDATE fts_ocr SET content = new.ocr_text
                    WHERE pdf_id = old.pdf_id AND page_number = old.page_number;
                END
            ''')

            # Create a trigger to update last_accessed timestamp
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS pdf_files_au AFTER UPDATE ON pdf_files BEGIN
                    UPDATE pdf_files SET last_accessed = CURRENT_TIMESTAMP WHERE id = new.id;
                END
            ''')

            conn.commit()
            print("Database and tables created successfully with indexes and FTS support.")
    
    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Tuple[Any, ...]]]:
        """
        Execute a SQL query and return the results.
        
        This method executes the provided SQL query with the given parameters
        and returns the results for SELECT queries. For non-SELECT queries,
        it commits the changes and returns None.
        
        Args:
            query: SQL query to execute
            params: Parameters for the query to prevent SQL injection
            
        Returns:
            Query results as a list of tuples for SELECT queries, or None for non-SELECT queries
            
        Raises:
            sqlite3.Error: If a database error occurs during execution
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
        
        This method inserts a new record into the pdf_files table with the
        provided metadata. If the file has already been processed, you should
        check with is_pdf_processed() before calling this method.
        
        Args:
            metadata: PDF metadata containing file name and path
            
        Returns:
            ID of the inserted PDF file (primary key)
            
        Raises:
            sqlite3.Error: If a database error occurs during insertion
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
    
    def search_text(self, search_term: str, use_fts: bool = True, 
                   limit: int = 100, offset: int = 0) -> List[Tuple[int, str, int, str, str]]:
        """
        Search for text in both PDF text and OCR text.
        
        This method searches across all indexed PDF content and OCR-extracted text
        for the specified search term. Results are paginated based on limit and offset.
        The search term is sanitized to prevent SQL injection.
        
        Args:
            search_term: Text to search for
            use_fts: Whether to use full-text search (faster but less flexible)
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            
        Returns:
            List of tuples containing (pdf_id, file_name, page_number, text, source)
            where source indicates whether the match was found in PDF text or OCR text
            
        Raises:
            sqlite3.Error: If a database error occurs during the search
            
        Example:
            >>> db = PDFDatabase()
            >>> results = db.search_text("important document", limit=10)
            >>> for pdf_id, name, page, text, source in results:
            ...     print(f"Found in {name}, page {page}: {text[:50]}...")
        """
        # Sanitize the search term to prevent SQL injection
        sanitized_term = sanitize_search_term(search_term)
        
        if not sanitized_term:
            return []
        
        try:
            # Check if we should use the FTS tables (faster for large datasets)
            if use_fts:
                # Use optimized FTS5 search with snippet function for context
                query = """
                SELECT 
                    pdf_files.id, 
                    pdf_files.file_name, 
                    fts.page_number, 
                    snippet(fts_content, 0, '<mark>', '</mark>', '...', 15) as text_snippet, 
                    'PDF Text' as source,
                    pdf_files.last_accessed
                FROM 
                    fts_content as fts
                JOIN 
                    pdf_files ON fts.pdf_id = pdf_files.id
                WHERE 
                    fts_content MATCH ?
                
                UNION
                
                SELECT 
                    pdf_files.id, 
                    pdf_files.file_name, 
                    fts.page_number, 
                    snippet(fts_ocr, 0, '<mark>', '</mark>', '...', 15) as text_snippet, 
                    'OCR Text' as source,
                    pdf_files.last_accessed
                FROM 
                    fts_ocr as fts
                JOIN 
                    pdf_files ON fts.pdf_id = pdf_files.id
                WHERE 
                    fts_ocr MATCH ?
                
                ORDER BY 
                    last_accessed DESC
                LIMIT ? OFFSET ?
                """
                
                # Format search term for FTS5 MATCH
                fts_term = f"{sanitized_term}*"  # Use stemming and prefix matching
                params = (fts_term, fts_term, limit, offset)
            else:
                # Use LIKE for more flexible but slower search
                query = """
                SELECT 
                    pdf_files.id, 
                    pdf_files.file_name, 
                    pages.page_number, 
                    pages.text, 
                    'PDF Text' as source,
                    pdf_files.last_accessed
                FROM pages 
                JOIN pdf_files ON pages.pdf_id = pdf_files.id 
                WHERE pages.text LIKE ?
                
                UNION
                
                SELECT 
                    pdf_files.id, 
                    pdf_files.file_name, 
                    ocr_text.page_number, 
                    ocr_text.ocr_text, 
                    'OCR Text' as source,
                    pdf_files.last_accessed
                FROM ocr_text 
                JOIN pdf_files ON ocr_text.pdf_id = pdf_files.id
                WHERE ocr_text.ocr_text LIKE ?
                
                ORDER BY last_accessed DESC
                LIMIT ? OFFSET ?
                """
                params = (f"%{sanitized_term}%", f"%{sanitized_term}%", limit, offset)
            
            # Execute the query
            results = self.execute_query(query, params) or []
            
            # Update last_accessed timestamp for the PDFs that were found
            if results:
                pdf_ids = set(row[0] for row in results)
                for pdf_id in pdf_ids:
                    self.execute_query(
                        "UPDATE pdf_files SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                        (pdf_id,)
                    )
            
            # Sanitize the results to prevent XSS
            sanitized_results = []
            for row in results:
                pdf_id, file_name, page_number, text, source, last_accessed = row
                sanitized_results.append((
                    pdf_id,
                    sanitize_text(file_name),
                    page_number,
                    sanitize_text(text),
                    source
                ))
            
            return sanitized_results
        except sqlite3.Error as e:
            # Log the error but don't expose details to the caller
            print(f"Database error: {e}")
            return []
    
    def get_search_count(self, search_term: str, use_fts: bool = True) -> int:
        """
        Get the total count of search results for pagination.
        
        This method counts the total number of results that match the search term
        without retrieving the actual results. This is useful for implementing
        pagination in the user interface.
        
        Args:
            search_term: Text to search for
            use_fts: Whether to use full-text search (faster but less flexible)
            
        Returns:
            Total number of matching results
            
        Raises:
            sqlite3.Error: If a database error occurs during the count
        """
        # Sanitize the search term to prevent SQL injection
        sanitized_term = sanitize_search_term(search_term)
        
        if not sanitized_term:
            return 0
        
        try:
            # Check if we should use the FTS tables
            if use_fts:
                # Use optimized FTS5 count query
                query = """
                SELECT COUNT(*) FROM (
                    SELECT 1
                    FROM fts_content
                    WHERE fts_content MATCH ?
                    
                    UNION
                    
                    SELECT 1
                    FROM fts_ocr
                    WHERE fts_ocr MATCH ?
                )
                """
                # Format search term for FTS5 MATCH
                fts_term = f"{sanitized_term}*"  # Use stemming and prefix matching
                params = (fts_term, fts_term)
            else:
                # Use LIKE for more flexible but slower search
                query = """
                SELECT COUNT(*) FROM (
                    SELECT 1
                    FROM pages
                    JOIN pdf_files ON pages.pdf_id = pdf_files.id
                    WHERE pages.text LIKE ?
                    
                    UNION
                    
                    SELECT 1
                    FROM ocr_text
                    JOIN pdf_files ON ocr_text.pdf_id = pdf_files.id
                    WHERE ocr_text.ocr_text LIKE ?
                )
                """
                params = (f"%{sanitized_term}%", f"%{sanitized_term}%")
            
            # Execute the query
            result = self.execute_query(query, params)
            return result[0][0] if result else 0
        except sqlite3.Error as e:
            # Log the error but don't expose details to the caller
            print(f"Database error: {e}")
            return 0
