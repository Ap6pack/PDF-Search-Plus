"""
Annotation management for PDF Search Plus.

This module provides classes and functions for managing PDF annotations,
including creating, updating, and deleting annotations, as well as
retrieving annotations for a specific PDF or page.
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from pdf_search_plus.utils.db import PDFDatabase
from pdf_search_plus.utils.security import sanitize_text


@dataclass
class Annotation:
    """
    Represents a PDF annotation.
    
    Attributes:
        pdf_id: ID of the PDF file
        page_number: Page number where the annotation is located
        x_coord: X coordinate of the annotation
        y_coord: Y coordinate of the annotation
        width: Width of the annotation
        height: Height of the annotation
        content: Text content of the annotation
        annotation_type: Type of annotation (e.g., 'highlight', 'note', 'underline')
        color: Color of the annotation (hex code)
        id: Optional database ID for the annotation
    """
    pdf_id: int
    page_number: int
    x_coord: float
    y_coord: float
    width: float
    height: float
    content: str
    annotation_type: str
    color: str = "#FFFF00"  # Default to yellow
    id: Optional[int] = None
    
    def __post_init__(self):
        """Validate and sanitize annotation data after initialization."""
        # Sanitize content
        self.content = sanitize_text(self.content)
        
        # Validate annotation type
        valid_types = {'highlight', 'note', 'underline', 'strikethrough', 'rectangle', 'circle'}
        if self.annotation_type not in valid_types:
            self.annotation_type = 'highlight'  # Default to highlight if invalid
        
        # Validate color format (hex code)
        if not self.color.startswith('#') or len(self.color) != 7:
            self.color = "#FFFF00"  # Default to yellow if invalid


class AnnotationManager:
    """
    Manages PDF annotations.
    
    This class provides methods for creating, updating, and deleting annotations,
    as well as retrieving annotations for a specific PDF or page.
    """
    
    def __init__(self, db: PDFDatabase):
        """
        Initialize the annotation manager.
        
        Args:
            db: Database manager
        """
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def create_annotation(self, annotation: Annotation) -> int:
        """
        Create a new annotation.
        
        Args:
            annotation: Annotation to create
            
        Returns:
            ID of the created annotation
            
        Raises:
            ValueError: If the annotation data is invalid
            sqlite3.Error: If a database error occurs
        """
        if not annotation.content:
            raise ValueError("Annotation content cannot be empty")
            
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if PDF exists
                cursor.execute("SELECT id FROM pdf_files WHERE id = ?", (annotation.pdf_id,))
                if not cursor.fetchone():
                    raise ValueError(f"PDF with ID {annotation.pdf_id} not found")
                
                # Insert the annotation
                cursor.execute(
                    """
                    INSERT INTO annotations (
                        pdf_id, page_number, x_coord, y_coord, width, height,
                        content, annotation_type, color
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        annotation.pdf_id, annotation.page_number,
                        annotation.x_coord, annotation.y_coord,
                        annotation.width, annotation.height,
                        annotation.content, annotation.annotation_type,
                        annotation.color
                    )
                )
                conn.commit()
                
                annotation_id = cursor.lastrowid
                self.logger.info(f"Created annotation with ID {annotation_id} for PDF {annotation.pdf_id}")
                return annotation_id
        except sqlite3.Error as e:
            self.logger.error(f"Database error creating annotation: {e}")
            raise
    
    def update_annotation(self, annotation_id: int, **kwargs) -> bool:
        """
        Update an existing annotation.
        
        Args:
            annotation_id: ID of the annotation to update
            **kwargs: Annotation attributes to update
            
        Returns:
            True if the annotation was updated, False if the annotation was not found
            
        Raises:
            ValueError: If no valid attributes are provided
            sqlite3.Error: If a database error occurs
        """
        valid_fields = {
            'x_coord', 'y_coord', 'width', 'height',
            'content', 'annotation_type', 'color'
        }
        
        # Filter out invalid fields
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not update_fields:
            raise ValueError("No valid fields provided for update")
            
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if annotation exists
                cursor.execute("SELECT id FROM annotations WHERE id = ?", (annotation_id,))
                if not cursor.fetchone():
                    self.logger.warning(f"Annotation with ID {annotation_id} not found")
                    return False
                
                # Build the update query
                query_parts = []
                params = []
                
                for field, value in update_fields.items():
                    if field == 'content':
                        value = sanitize_text(value)
                    elif field == 'annotation_type':
                        valid_types = {'highlight', 'note', 'underline', 'strikethrough', 'rectangle', 'circle'}
                        if value not in valid_types:
                            value = 'highlight'
                    elif field == 'color':
                        if not value.startswith('#') or len(value) != 7:
                            value = "#FFFF00"
                    
                    query_parts.append(f"{field} = ?")
                    params.append(value)
                
                # Add the annotation ID to params
                params.append(annotation_id)
                
                # Execute the update
                cursor.execute(
                    f"UPDATE annotations SET {', '.join(query_parts)} WHERE id = ?",
                    tuple(params)
                )
                conn.commit()
                
                self.logger.info(f"Updated annotation {annotation_id}")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Database error updating annotation: {e}")
            raise
    
    def delete_annotation(self, annotation_id: int) -> bool:
        """
        Delete an annotation.
        
        Args:
            annotation_id: ID of the annotation to delete
            
        Returns:
            True if the annotation was deleted, False if the annotation was not found
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if annotation exists
                cursor.execute("SELECT id FROM annotations WHERE id = ?", (annotation_id,))
                if not cursor.fetchone():
                    self.logger.warning(f"Annotation with ID {annotation_id} not found")
                    return False
                
                # Delete the annotation
                cursor.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
                conn.commit()
                
                self.logger.info(f"Deleted annotation {annotation_id}")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Database error deleting annotation: {e}")
            raise
    
    def get_annotation(self, annotation_id: int) -> Optional[Annotation]:
        """
        Get an annotation by ID.
        
        Args:
            annotation_id: ID of the annotation to get
            
        Returns:
            Annotation if found, None otherwise
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, pdf_id, page_number, x_coord, y_coord, width, height,
                           content, annotation_type, color
                    FROM annotations
                    WHERE id = ?
                    """,
                    (annotation_id,)
                )
                
                row = cursor.fetchone()
                if not row:
                    return None
                    
                return Annotation(
                    id=row[0],
                    pdf_id=row[1],
                    page_number=row[2],
                    x_coord=row[3],
                    y_coord=row[4],
                    width=row[5],
                    height=row[6],
                    content=row[7],
                    annotation_type=row[8],
                    color=row[9]
                )
        except sqlite3.Error as e:
            self.logger.error(f"Database error getting annotation: {e}")
            raise
    
    def get_pdf_annotations(self, pdf_id: int) -> List[Annotation]:
        """
        Get all annotations for a PDF.
        
        Args:
            pdf_id: ID of the PDF
            
        Returns:
            List of annotations for the PDF
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, pdf_id, page_number, x_coord, y_coord, width, height,
                           content, annotation_type, color
                    FROM annotations
                    WHERE pdf_id = ?
                    ORDER BY page_number, y_coord
                    """,
                    (pdf_id,)
                )
                
                return [
                    Annotation(
                        id=row[0],
                        pdf_id=row[1],
                        page_number=row[2],
                        x_coord=row[3],
                        y_coord=row[4],
                        width=row[5],
                        height=row[6],
                        content=row[7],
                        annotation_type=row[8],
                        color=row[9]
                    )
                    for row in cursor.fetchall()
                ]
        except sqlite3.Error as e:
            self.logger.error(f"Database error getting PDF annotations: {e}")
            raise
    
    def get_page_annotations(self, pdf_id: int, page_number: int) -> List[Annotation]:
        """
        Get all annotations for a specific page of a PDF.
        
        Args:
            pdf_id: ID of the PDF
            page_number: Page number
            
        Returns:
            List of annotations for the page
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, pdf_id, page_number, x_coord, y_coord, width, height,
                           content, annotation_type, color
                    FROM annotations
                    WHERE pdf_id = ? AND page_number = ?
                    ORDER BY y_coord
                    """,
                    (pdf_id, page_number)
                )
                
                return [
                    Annotation(
                        id=row[0],
                        pdf_id=row[1],
                        page_number=row[2],
                        x_coord=row[3],
                        y_coord=row[4],
                        width=row[5],
                        height=row[6],
                        content=row[7],
                        annotation_type=row[8],
                        color=row[9]
                    )
                    for row in cursor.fetchall()
                ]
        except sqlite3.Error as e:
            self.logger.error(f"Database error getting page annotations: {e}")
            raise
    
    def search_annotations(self, search_term: str, limit: int = 100, offset: int = 0) -> List[Annotation]:
        """
        Search for annotations by content.
        
        Args:
            search_term: Text to search for in annotation content
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            
        Returns:
            List of annotations matching the search term
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        # Sanitize the search term to prevent SQL injection
        search_term = sanitize_text(search_term)
        
        if not search_term:
            return []
            
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, pdf_id, page_number, x_coord, y_coord, width, height,
                           content, annotation_type, color
                    FROM annotations
                    WHERE content LIKE ?
                    ORDER BY pdf_id, page_number, y_coord
                    LIMIT ? OFFSET ?
                    """,
                    (f"%{search_term}%", limit, offset)
                )
                
                return [
                    Annotation(
                        id=row[0],
                        pdf_id=row[1],
                        page_number=row[2],
                        x_coord=row[3],
                        y_coord=row[4],
                        width=row[5],
                        height=row[6],
                        content=row[7],
                        annotation_type=row[8],
                        color=row[9]
                    )
                    for row in cursor.fetchall()
                ]
        except sqlite3.Error as e:
            self.logger.error(f"Database error searching annotations: {e}")
            raise
