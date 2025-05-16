"""
Tag and category management for PDF Search Plus.

This module provides classes and functions for managing tags and categories
for PDF documents, including creating, updating, and deleting tags, as well
as assigning tags to documents and searching by tags.
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass

from pdf_search_plus.utils.db import PDFDatabase
from pdf_search_plus.utils.security import sanitize_text


@dataclass
class Tag:
    """
    Represents a document tag.
    
    Attributes:
        name: The name of the tag
        color: The color of the tag (hex code)
        id: Optional database ID for the tag
    """
    name: str
    color: str = "#808080"
    id: Optional[int] = None
    
    def __post_init__(self):
        """Validate and sanitize tag data after initialization."""
        # Sanitize tag name
        self.name = sanitize_text(self.name)
        
        # Validate color format (hex code)
        if not self.color.startswith('#') or len(self.color) != 7:
            self.color = "#808080"  # Default to gray if invalid


@dataclass
class Category:
    """
    Represents a document category.
    
    Categories can be hierarchical, with parent-child relationships.
    
    Attributes:
        name: The name of the category
        parent_id: Optional ID of the parent category
        id: Optional database ID for the category
    """
    name: str
    parent_id: Optional[int] = None
    id: Optional[int] = None
    
    def __post_init__(self):
        """Validate and sanitize category data after initialization."""
        # Sanitize category name
        self.name = sanitize_text(self.name)


class TagManager:
    """
    Manages document tags and categories.
    
    This class provides methods for creating, updating, and deleting tags,
    as well as assigning tags to documents and searching by tags.
    """
    
    def __init__(self, db: PDFDatabase):
        """
        Initialize the tag manager.
        
        Args:
            db: Database manager
        """
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def create_tag(self, tag: Tag) -> int:
        """
        Create a new tag.
        
        Args:
            tag: Tag to create
            
        Returns:
            ID of the created tag
            
        Raises:
            ValueError: If the tag name is empty or already exists
            sqlite3.Error: If a database error occurs
        """
        if not tag.name:
            raise ValueError("Tag name cannot be empty")
            
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if tag already exists
                cursor.execute("SELECT id FROM tags WHERE name = ?", (tag.name,))
                if cursor.fetchone():
                    raise ValueError(f"Tag '{tag.name}' already exists")
                
                # Insert the tag
                cursor.execute(
                    "INSERT INTO tags (name, color) VALUES (?, ?)",
                    (tag.name, tag.color)
                )
                conn.commit()
                
                tag_id = cursor.lastrowid
                self.logger.info(f"Created tag '{tag.name}' with ID {tag_id}")
                return tag_id
        except sqlite3.Error as e:
            self.logger.error(f"Database error creating tag: {e}")
            raise
    
    def update_tag(self, tag_id: int, name: Optional[str] = None, color: Optional[str] = None) -> bool:
        """
        Update an existing tag.
        
        Args:
            tag_id: ID of the tag to update
            name: New name for the tag (optional)
            color: New color for the tag (optional)
            
        Returns:
            True if the tag was updated, False if the tag was not found
            
        Raises:
            ValueError: If both name and color are None
            sqlite3.Error: If a database error occurs
        """
        if name is None and color is None:
            raise ValueError("At least one of name or color must be provided")
            
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if tag exists
                cursor.execute("SELECT name FROM tags WHERE id = ?", (tag_id,))
                result = cursor.fetchone()
                if not result:
                    self.logger.warning(f"Tag with ID {tag_id} not found")
                    return False
                
                old_name = result[0]
                
                # Build the update query
                query_parts = []
                params = []
                
                if name is not None:
                    name = sanitize_text(name)
                    if not name:
                        raise ValueError("Tag name cannot be empty")
                    query_parts.append("name = ?")
                    params.append(name)
                
                if color is not None:
                    if not color.startswith('#') or len(color) != 7:
                        color = "#808080"  # Default to gray if invalid
                    query_parts.append("color = ?")
                    params.append(color)
                
                # Add the tag ID to params
                params.append(tag_id)
                
                # Execute the update
                cursor.execute(
                    f"UPDATE tags SET {', '.join(query_parts)} WHERE id = ?",
                    tuple(params)
                )
                conn.commit()
                
                self.logger.info(f"Updated tag {tag_id} ('{old_name}')")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Database error updating tag: {e}")
            raise
    
    def delete_tag(self, tag_id: int) -> bool:
        """
        Delete a tag.
        
        This also removes all associations between the tag and PDF files.
        
        Args:
            tag_id: ID of the tag to delete
            
        Returns:
            True if the tag was deleted, False if the tag was not found
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if tag exists
                cursor.execute("SELECT name FROM tags WHERE id = ?", (tag_id,))
                result = cursor.fetchone()
                if not result:
                    self.logger.warning(f"Tag with ID {tag_id} not found")
                    return False
                
                tag_name = result[0]
                
                # Delete the tag (cascade will delete pdf_tags entries)
                cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
                conn.commit()
                
                self.logger.info(f"Deleted tag {tag_id} ('{tag_name}')")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Database error deleting tag: {e}")
            raise
    
    def get_all_tags(self) -> List[Tag]:
        """
        Get all tags.
        
        Returns:
            List of all tags
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, color FROM tags ORDER BY name")
                
                return [
                    Tag(id=row[0], name=row[1], color=row[2])
                    for row in cursor.fetchall()
                ]
        except sqlite3.Error as e:
            self.logger.error(f"Database error getting tags: {e}")
            raise
    
    def get_tag(self, tag_id: int) -> Optional[Tag]:
        """
        Get a tag by ID.
        
        Args:
            tag_id: ID of the tag to get
            
        Returns:
            Tag if found, None otherwise
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, color FROM tags WHERE id = ?", (tag_id,))
                
                row = cursor.fetchone()
                if row:
                    return Tag(id=row[0], name=row[1], color=row[2])
                return None
        except sqlite3.Error as e:
            self.logger.error(f"Database error getting tag: {e}")
            raise
    
    def assign_tag(self, pdf_id: int, tag_id: int) -> bool:
        """
        Assign a tag to a PDF document.
        
        Args:
            pdf_id: ID of the PDF document
            tag_id: ID of the tag
            
        Returns:
            True if the tag was assigned, False if the PDF or tag was not found
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if PDF exists
                cursor.execute("SELECT file_name FROM pdf_files WHERE id = ?", (pdf_id,))
                pdf_result = cursor.fetchone()
                if not pdf_result:
                    self.logger.warning(f"PDF with ID {pdf_id} not found")
                    return False
                
                # Check if tag exists
                cursor.execute("SELECT name FROM tags WHERE id = ?", (tag_id,))
                tag_result = cursor.fetchone()
                if not tag_result:
                    self.logger.warning(f"Tag with ID {tag_id} not found")
                    return False
                
                # Check if the tag is already assigned
                cursor.execute(
                    "SELECT 1 FROM pdf_tags WHERE pdf_id = ? AND tag_id = ?",
                    (pdf_id, tag_id)
                )
                if cursor.fetchone():
                    # Already assigned
                    return True
                
                # Assign the tag
                cursor.execute(
                    "INSERT INTO pdf_tags (pdf_id, tag_id) VALUES (?, ?)",
                    (pdf_id, tag_id)
                )
                conn.commit()
                
                self.logger.info(f"Assigned tag {tag_id} ('{tag_result[0]}') to PDF {pdf_id} ('{pdf_result[0]}')")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Database error assigning tag: {e}")
            raise
    
    def remove_tag(self, pdf_id: int, tag_id: int) -> bool:
        """
        Remove a tag from a PDF document.
        
        Args:
            pdf_id: ID of the PDF document
            tag_id: ID of the tag
            
        Returns:
            True if the tag was removed, False if the PDF or tag was not found
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if the assignment exists
                cursor.execute(
                    "SELECT 1 FROM pdf_tags WHERE pdf_id = ? AND tag_id = ?",
                    (pdf_id, tag_id)
                )
                if not cursor.fetchone():
                    # Not assigned
                    return False
                
                # Remove the tag
                cursor.execute(
                    "DELETE FROM pdf_tags WHERE pdf_id = ? AND tag_id = ?",
                    (pdf_id, tag_id)
                )
                conn.commit()
                
                self.logger.info(f"Removed tag {tag_id} from PDF {pdf_id}")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Database error removing tag: {e}")
            raise
    
    def get_pdf_tags(self, pdf_id: int) -> List[Tag]:
        """
        Get all tags assigned to a PDF document.
        
        Args:
            pdf_id: ID of the PDF document
            
        Returns:
            List of tags assigned to the PDF
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT t.id, t.name, t.color
                    FROM tags t
                    JOIN pdf_tags pt ON t.id = pt.tag_id
                    WHERE pt.pdf_id = ?
                    ORDER BY t.name
                """, (pdf_id,))
                
                return [
                    Tag(id=row[0], name=row[1], color=row[2])
                    for row in cursor.fetchall()
                ]
        except sqlite3.Error as e:
            self.logger.error(f"Database error getting PDF tags: {e}")
            raise
    
    def search_by_tags(self, tag_ids: List[int], require_all: bool = False) -> List[int]:
        """
        Search for PDFs with the specified tags.
        
        Args:
            tag_ids: List of tag IDs to search for
            require_all: If True, PDFs must have ALL specified tags
                         If False, PDFs with ANY of the tags will be returned
                         
        Returns:
            List of PDF IDs matching the tag criteria
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        if not tag_ids:
            return []
            
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                if require_all:
                    # PDFs must have ALL specified tags
                    placeholders = ','.join('?' * len(tag_ids))
                    query = f"""
                    SELECT pdf_id FROM pdf_tags
                    WHERE tag_id IN ({placeholders})
                    GROUP BY pdf_id
                    HAVING COUNT(DISTINCT tag_id) = ?
                    """
                    params = tag_ids + [len(tag_ids)]
                else:
                    # PDFs with ANY of the tags
                    placeholders = ','.join('?' * len(tag_ids))
                    query = f"""
                    SELECT DISTINCT pdf_id FROM pdf_tags
                    WHERE tag_id IN ({placeholders})
                    """
                    params = tag_ids
                    
                cursor.execute(query, params)
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Database error searching by tags: {e}")
            raise
    
    def create_category(self, category: Category) -> int:
        """
        Create a new category.
        
        Args:
            category: Category to create
            
        Returns:
            ID of the created category
            
        Raises:
            ValueError: If the category name is empty
            sqlite3.Error: If a database error occurs
        """
        if not category.name:
            raise ValueError("Category name cannot be empty")
            
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if parent category exists if provided
                if category.parent_id is not None:
                    cursor.execute("SELECT id FROM categories WHERE id = ?", (category.parent_id,))
                    if not cursor.fetchone():
                        raise ValueError(f"Parent category with ID {category.parent_id} not found")
                
                # Insert the category
                cursor.execute(
                    "INSERT INTO categories (name, parent_id) VALUES (?, ?)",
                    (category.name, category.parent_id)
                )
                conn.commit()
                
                category_id = cursor.lastrowid
                self.logger.info(f"Created category '{category.name}' with ID {category_id}")
                return category_id
        except sqlite3.Error as e:
            self.logger.error(f"Database error creating category: {e}")
            raise
    
    def get_all_categories(self) -> List[Category]:
        """
        Get all categories.
        
        Returns:
            List of all categories
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, parent_id FROM categories ORDER BY name")
                
                return [
                    Category(id=row[0], name=row[1], parent_id=row[2])
                    for row in cursor.fetchall()
                ]
        except sqlite3.Error as e:
            self.logger.error(f"Database error getting categories: {e}")
            raise
    
    def assign_category(self, pdf_id: int, category_id: int) -> bool:
        """
        Assign a category to a PDF document.
        
        Args:
            pdf_id: ID of the PDF document
            category_id: ID of the category
            
        Returns:
            True if the category was assigned, False if the PDF or category was not found
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if PDF exists
                cursor.execute("SELECT file_name FROM pdf_files WHERE id = ?", (pdf_id,))
                pdf_result = cursor.fetchone()
                if not pdf_result:
                    self.logger.warning(f"PDF with ID {pdf_id} not found")
                    return False
                
                # Check if category exists
                cursor.execute("SELECT name FROM categories WHERE id = ?", (category_id,))
                category_result = cursor.fetchone()
                if not category_result:
                    self.logger.warning(f"Category with ID {category_id} not found")
                    return False
                
                # Check if the category is already assigned
                cursor.execute(
                    "SELECT 1 FROM pdf_categories WHERE pdf_id = ? AND category_id = ?",
                    (pdf_id, category_id)
                )
                if cursor.fetchone():
                    # Already assigned
                    return True
                
                # Assign the category
                cursor.execute(
                    "INSERT INTO pdf_categories (pdf_id, category_id) VALUES (?, ?)",
                    (pdf_id, category_id)
                )
                conn.commit()
                
                self.logger.info(f"Assigned category {category_id} ('{category_result[0]}') to PDF {pdf_id} ('{pdf_result[0]}')")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Database error assigning category: {e}")
            raise
    
    def get_pdf_categories(self, pdf_id: int) -> List[Category]:
        """
        Get all categories assigned to a PDF document.
        
        Args:
            pdf_id: ID of the PDF document
            
        Returns:
            List of categories assigned to the PDF
            
        Raises:
            sqlite3.Error: If a database error occurs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.id, c.name, c.parent_id
                    FROM categories c
                    JOIN pdf_categories pc ON c.id = pc.category_id
                    WHERE pc.pdf_id = ?
                    ORDER BY c.name
                """, (pdf_id,))
                
                return [
                    Category(id=row[0], name=row[1], parent_id=row[2])
                    for row in cursor.fetchall()
                ]
        except sqlite3.Error as e:
            self.logger.error(f"Database error getting PDF categories: {e}")
            raise
