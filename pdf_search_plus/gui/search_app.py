"""
GUI for the PDF Search Plus application.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, Canvas, filedialog
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import threading
import logging
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path

from pdf_search_plus.utils.db import PDFDatabase
from pdf_search_plus.utils.security import (
    sanitize_text, sanitize_search_term, validate_file_path,
    validate_pdf_file
)


class PDFSearchApp:
    """
    GUI application for searching and previewing PDF files.
    """
    
    def __init__(self, root: tk.Tk, db: Optional[PDFDatabase] = None):
        """
        Initialize the PDF Search application.
        
        Args:
            root: Tkinter root window
            db: Database manager, or None to create a new one
        """
        self.root = root
        self.root.title("PDF Search and Preview")
        self.root.geometry("800x600")  # Default window size

        # PDF state
        self.current_pdf = None
        self.page_number = 1
        self.total_pages = 0
        self.zoom_factor = 1.0

        # Database
        self.db = db or PDFDatabase()

        # Configure logging
        self.logger = logging.getLogger(__name__)

        # Initialize UI components
        self.create_widgets()

    def create_widgets(self):
        """Create and arrange the UI widgets."""
        # Search input fields
        frame_search = tk.Frame(self.root)
        frame_search.grid(row=0, column=0, columnspan=8, padx=10, pady=10, sticky='ew')

        tk.Label(frame_search, text="Search Text").grid(row=0, column=2, padx=10, pady=10)
        self.context_entry = tk.Entry(frame_search, width=30)
        self.context_entry.grid(row=0, column=3, padx=10, pady=10)

        tk.Button(frame_search, text="Search", command=self.search_keywords).grid(row=0, column=4, padx=10, pady=10)

        # Treeview for displaying search results
        self.tree = ttk.Treeview(self.root, columns=("PDF ID", "File Name", "Page Number", "Context", "Source"), show="headings")
        self.tree.heading("PDF ID", text="PDF ID")
        self.tree.heading("File Name", text="File Name")
        self.tree.heading("Page Number", text="Page Number")
        self.tree.heading("Context", text="Context")
        self.tree.heading("Source", text="Source")  # Indicates the source of text (OCR or PDF text)
        
        # Configure column widths
        self.tree.column("PDF ID", width=50, stretch=tk.NO)
        self.tree.column("File Name", width=150)
        self.tree.column("Page Number", width=80, stretch=tk.NO)
        self.tree.column("Context", width=300)
        self.tree.column("Source", width=80, stretch=tk.NO)
        
        # Add scrollbar
        tree_scroll = ttk.Scrollbar(self.root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        # Place treeview and scrollbar
        self.tree.grid(row=1, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')
        tree_scroll.grid(row=1, column=4, sticky='ns', pady=10)

        # Embedded PDF preview using a Canvas
        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.grid(row=1, column=5, columnspan=3, padx=10, pady=10, sticky='nsew')
        
        # Add scrollbars for canvas
        canvas_scroll_y = ttk.Scrollbar(self.canvas_frame, orient="vertical")
        canvas_scroll_x = ttk.Scrollbar(self.canvas_frame, orient="horizontal")
        self.canvas = Canvas(
            self.canvas_frame, 
            width=600, 
            height=800,
            yscrollcommand=canvas_scroll_y.set,
            xscrollcommand=canvas_scroll_x.set
        )
        
        canvas_scroll_y.config(command=self.canvas.yview)
        canvas_scroll_x.config(command=self.canvas.xview)
        
        # Place canvas and scrollbars
        canvas_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        canvas_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Controls for page navigation, zoom, and preview
        frame_controls = tk.Frame(self.root)
        frame_controls.grid(row=2, column=0, columnspan=8, pady=10)

        self.btn_prev = tk.Button(frame_controls, text="Previous Page", command=self.prev_page)
        self.btn_prev.grid(row=0, column=0, padx=5)

        self.btn_next = tk.Button(frame_controls, text="Next Page", command=self.next_page)
        self.btn_next.grid(row=0, column=1, padx=5)

        self.btn_zoom_in = tk.Button(frame_controls, text="Zoom In", command=lambda: self.update_zoom_factor(0.1))
        self.btn_zoom_in.grid(row=0, column=2, padx=5)

        self.btn_zoom_out = tk.Button(frame_controls, text="Zoom Out", command=lambda: self.update_zoom_factor(-0.1))
        self.btn_zoom_out.grid(row=0, column=3, padx=5)

        self.btn_preview = tk.Button(frame_controls, text="Preview PDF", command=self.preview_selected_pdf)
        self.btn_preview.grid(row=0, column=4, padx=5)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=3, column=0, columnspan=8, sticky='ew')

        # Make sure the layout expands properly
        self.root.grid_rowconfigure(1, weight=1)  # Make row 1 (tree and canvas) expandable
        self.root.grid_columnconfigure(0, weight=1)  # Make treeview expand
        self.root.grid_columnconfigure(5, weight=1)  # Make canvas column expandable

    def get_pdf_path(self, pdf_id: int) -> Optional[str]:
        """
        Fetch the PDF file path for a given ID.
        
        Args:
            pdf_id: ID of the PDF file
            
        Returns:
            Path to the PDF file, or None if not found
        """
        try:
            return self.db.get_pdf_path(pdf_id)
        except Exception as e:
            self.logger.error(f"Database error: {e}")
            messagebox.showerror("Database Error", str(e))
            return None

    def load_pdf(self, pdf_path: str, page_number: int = 1) -> None:
        """
        Load the selected PDF and display the provided page number.
        
        Args:
            pdf_path: Path to the PDF file
            page_number: Page number to display
        """
        # Validate the file path
        if not validate_file_path(pdf_path):
            messagebox.showerror("Invalid File", f"The file path is invalid: {pdf_path}")
            return
            
        # Validate that the file is a valid PDF
        if not validate_pdf_file(pdf_path):
            messagebox.showerror("Invalid PDF", f"The file is not a valid PDF: {pdf_path}")
            return

        try:
            self.current_pdf = pdf_path  # Store the current PDF path
            doc = fitz.open(pdf_path)
            self.total_pages = len(doc)  # Set the total number of pages
            
            # Validate the page number
            if page_number < 1 or page_number > self.total_pages:
                page_number = 1
                self.logger.warning(f"Invalid page number {page_number}, defaulting to page 1")
                
            self.page_number = page_number  # Start at the provided page number
            self.show_pdf_page(page_number)
            
            # Update status bar
            self.status_var.set(f"Loaded: {os.path.basename(pdf_path)} - Page {page_number} of {self.total_pages}")
        except Exception as e:
            self.logger.error(f"Error opening PDF: {e}")
            messagebox.showerror("Error", "An error occurred while opening the PDF file.")

    def preview_selected_pdf(self) -> None:
        """Preview the selected PDF and display the corresponding page."""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Select an item", "Please select a search result first.")
            return

        selected_row = self.tree.item(selected_item)['values']
        pdf_id = selected_row[0]
        page_number = selected_row[2]  # This is the page number you want to preview
        pdf_path = self.get_pdf_path(pdf_id)

        if pdf_path:
            self.load_pdf(pdf_path, page_number=page_number)
        else:
            messagebox.showerror("File Not Found", "The selected PDF file could not be found.")

    def next_page(self) -> None:
        """Go to the next page in the PDF preview."""
        if self.current_pdf and self.page_number < self.total_pages:
            self.page_number += 1
            self.show_pdf_page(self.page_number)
            self.status_var.set(f"Loaded: {os.path.basename(self.current_pdf)} - Page {self.page_number} of {self.total_pages}")

    def prev_page(self) -> None:
        """Go to the previous page in the PDF preview."""
        if self.current_pdf and self.page_number > 1:
            self.page_number -= 1
            self.show_pdf_page(self.page_number)
            self.status_var.set(f"Loaded: {os.path.basename(self.current_pdf)} - Page {self.page_number} of {self.total_pages}")

    def update_zoom_factor(self, delta: float) -> None:
        """
        Update zoom factor by a given delta and refresh the current page.
        
        Args:
            delta: Change in zoom factor
        """
        new_zoom = self.zoom_factor + delta
        if 0.5 <= new_zoom <= 3.0:  # Set a range for zoom factor
            self.zoom_factor = new_zoom
            self.show_pdf_page(self.page_number)
            self.status_var.set(f"Zoom: {int(self.zoom_factor * 100)}%")

    def search_keywords(self) -> None:
        """Search the database for context in both PDF text and OCR-extracted text."""
        # Get the search term from the entry field
        raw_search_term = self.context_entry.get()
        
        # Validate and sanitize the search term
        if not raw_search_term:
            messagebox.showwarning("Empty Search", "Please enter a search term.")
            return
        
        # Sanitize the search term to prevent SQL injection
        search_term = sanitize_search_term(raw_search_term)
        if not search_term:
            messagebox.showwarning("Invalid Search", "The search term contains invalid characters.")
            return
            
        self.status_var.set(f"Searching for: {search_term}...")
        
        def search_db():
            try:
                # Use the sanitized search term for the database query
                rows = self.db.search_text(search_term)
                self.root.after(0, self.update_treeview, rows)  # Safely update Treeview
                self.root.after(0, lambda: self.status_var.set(f"Found {len(rows)} results for: {search_term}"))
            except Exception as e:
                self.logger.error(f"Database error: {e}")
                # Don't expose detailed error messages to the user
                self.root.after(0, lambda: messagebox.showerror("Database Error", "An error occurred while searching."))
                self.root.after(0, lambda: self.status_var.set("Search error"))

        threading.Thread(target=search_db).start()

    def update_treeview(self, rows: List[Tuple]) -> None:
        """
        Update the treeview with the search results.
        
        Args:
            rows: Search result rows
        """
        self.clear_tree()
        if not rows:
            return
            
        for row in rows:
            # Truncate context text if too long
            values = list(row)
            if len(values[3]) > 100:  # Truncate context if too long
                values[3] = values[3][:100] + "..."
            self.tree.insert("", tk.END, values=values)

    def show_pdf_page(self, page_number: int) -> None:
        """
        Display the selected PDF page in the embedded Canvas.
        
        Args:
            page_number: Page number to display
        """
        # Validate PDF state
        if self.current_pdf is None:
            messagebox.showerror("Error", "No PDF file loaded.")
            return

        # Validate file path
        if not validate_file_path(self.current_pdf):
            messagebox.showerror("Invalid File", f"The file path is invalid: {self.current_pdf}")
            self.current_pdf = None
            return
            
        # Validate PDF file
        if not validate_pdf_file(self.current_pdf):
            messagebox.showerror("Invalid PDF", f"The file is not a valid PDF: {self.current_pdf}")
            self.current_pdf = None
            return

        try:
            # Clear the canvas
            self.canvas.delete("all")
            
            # Open the PDF file
            doc = fitz.open(self.current_pdf)
            
            # Validate page number
            if page_number < 1:
                page_number = 1
                self.page_number = 1
                self.logger.warning(f"Invalid page number {page_number}, defaulting to page 1")
            elif page_number > len(doc):
                page_number = len(doc)
                self.page_number = len(doc)
                self.logger.warning(f"Invalid page number {page_number}, defaulting to last page {len(doc)}")
                
            page_index = page_number - 1  # Page number starts from 1
            page = doc.load_page(page_index)
            
            # Validate zoom factor
            if self.zoom_factor < 0.5:
                self.zoom_factor = 0.5
                self.logger.warning("Zoom factor too small, setting to minimum (0.5)")
            elif self.zoom_factor > 3.0:
                self.zoom_factor = 3.0
                self.logger.warning("Zoom factor too large, setting to maximum (3.0)")
                
            # Render the page
            pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom_factor, self.zoom_factor))

            # Convert to a PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Convert the image to ImageTk format for tkinter
            img_tk = ImageTk.PhotoImage(img)

            # Configure canvas scrollregion
            self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))
            
            # Display the image in the canvas
            self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
            self.canvas.image = img_tk  # Keep a reference to avoid garbage collection
            
            # Update status bar
            self.status_var.set(f"Loaded: {os.path.basename(self.current_pdf)} - Page {page_number} of {len(doc)}")
        except Exception as e:
            self.logger.error(f"Error displaying PDF page: {e}")
            # Don't expose detailed error messages to the user
            messagebox.showerror("Error", "An error occurred while displaying the PDF page.")

    def clear_tree(self) -> None:
        """Clear the treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)
