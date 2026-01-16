"""
GUI for the PDF Search Plus application.
"""

import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, Canvas
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import threading
import logging
from typing import Optional, List, Tuple, Any, Union

from pdf_search_plus.utils.db import PDFDatabase
from pdf_search_plus.utils.security import (
    sanitize_search_term, validate_file_path,
    validate_pdf_file, validate_page_number, validate_zoom_factor
)
from pdf_search_plus.utils.cache import (
    pdf_cache, search_cache
)
from pdf_search_plus.utils.memory import (
    log_memory_usage, memory_usage_tracking, force_garbage_collection
)


class PDFSearchApp:
    """
    GUI application for searching and previewing PDF files.
    """

    def __init__(self, root: Union[tk.Tk, tk.Toplevel], db: Optional[PDFDatabase] = None):
        """
        Initialize the PDF Search application.

        Args:
            root: Tkinter root window or Toplevel window
            db: Database manager, or None to create a new one
        """
        self.root = root
        self.root.title("PDF Search and Preview")
        self.root.geometry("1000x700")  # Larger default window size
        self.root.resizable(True, True)  # Enable window resizing (minimize/maximize)

        # PDF state
        self.current_pdf: Optional[str] = None
        self.page_number: int = 1
        self.total_pages: int = 0
        self.zoom_factor: float = 1.0
        self.current_image: Optional[Any] = None  # Keep reference to prevent garbage collection

        # Search state
        self.current_search_term: str = ""
        self.current_page: int = 0
        self.results_per_page: int = 50  # Increased from 20 to 50 results per page
        self.total_results: int = 0
        self.use_fts: bool = True  # Use full-text search by default
        self.search_in_progress: bool = False  # Track if search is running

        # Database
        self.db = db or PDFDatabase()

        # Configure logging
        self.logger = logging.getLogger(__name__)

        # Initialize UI components
        self.create_widgets()
        
        # Start memory monitoring
        log_memory_usage("Application startup")

    def create_widgets(self):
        """Create and arrange the UI widgets."""
        # Search input fields
        frame_search = tk.Frame(self.root)
        frame_search.grid(row=0, column=0, columnspan=8, padx=10, pady=10, sticky='ew')

        tk.Label(frame_search, text="Search Text").grid(row=0, column=0, padx=10, pady=10)
        self.context_entry = tk.Entry(frame_search, width=30)
        self.context_entry.grid(row=0, column=1, padx=10, pady=10)
        self.context_entry.bind("<Return>", lambda event: self.search_keywords())

        # Search options
        self.use_fts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame_search, 
            text="Use Full-Text Search", 
            variable=self.use_fts_var
        ).grid(row=0, column=2, padx=10, pady=10)

        tk.Button(
            frame_search, 
            text="Search", 
            command=self.search_keywords
        ).grid(row=0, column=3, padx=10, pady=10)
        
        # Create a dedicated frame for pagination with a border to make it stand out
        self.pagination_frame = tk.Frame(self.root, bd=2, relief=tk.RIDGE)
        self.pagination_frame.grid(row=1, column=0, columnspan=8, padx=10, pady=(0, 10), sticky='ew')
        
        # Add a label to clearly indicate pagination
        pagination_label = tk.Label(
            self.pagination_frame, 
            text="SEARCH RESULTS NAVIGATION", 
            font=("Helvetica", 10, "bold"),
            fg="#0066cc"
        )
        pagination_label.grid(row=0, column=0, columnspan=5, padx=5, pady=5, sticky='w')
        
        # Results count label
        self.results_count_label = tk.Label(
            self.pagination_frame, 
            text="No results", 
            font=("Helvetica", 10),
            fg="#333333"
        )
        self.results_count_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
        
        # Current page indicator
        self.current_range_label = tk.Label(
            self.pagination_frame, 
            text="Showing: none", 
            font=("Helvetica", 10),
            fg="#333333"
        )
        self.current_range_label.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        
        # Navigation buttons with improved styling
        self.btn_first_page = tk.Button(
            self.pagination_frame, 
            text="⏮ First", 
            command=self.first_results_page,
            bg="#e1e1e1",
            width=8
        )
        self.btn_first_page.grid(row=1, column=2, padx=5, pady=5)
        
        self.btn_prev_page = tk.Button(
            self.pagination_frame, 
            text="◀ Previous", 
            command=self.prev_results_page,
            bg="#e1e1e1",
            width=10
        )
        self.btn_prev_page.grid(row=1, column=3, padx=5, pady=5)
        
        self.page_label = tk.Label(
            self.pagination_frame, 
            text="Page 1 of 1", 
            font=("Helvetica", 10, "bold"),
            width=15
        )
        self.page_label.grid(row=1, column=4, padx=5, pady=5)
        
        self.btn_next_page = tk.Button(
            self.pagination_frame, 
            text="Next ▶", 
            command=self.next_results_page,
            bg="#e1e1e1",
            width=10
        )
        self.btn_next_page.grid(row=1, column=5, padx=5, pady=5)
        
        self.btn_last_page = tk.Button(
            self.pagination_frame, 
            text="Last ⏭", 
            command=self.last_results_page,
            bg="#e1e1e1",
            width=8
        )
        self.btn_last_page.grid(row=1, column=6, padx=5, pady=5)
        
        # Initially hide pagination controls
        self.pagination_frame.grid_remove()

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
        self.tree.grid(row=2, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')
        tree_scroll.grid(row=2, column=4, sticky='ns', pady=10)

        # Embedded PDF preview using a Canvas
        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.grid(row=2, column=5, columnspan=3, padx=10, pady=10, sticky='nsew')
        
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
        frame_controls.grid(row=3, column=0, columnspan=8, pady=10)

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
        self.status_bar.grid(row=4, column=0, columnspan=8, sticky='ew')

        # Make sure the layout expands properly
        self.root.grid_rowconfigure(2, weight=1)  # Make row 2 (tree and canvas) expandable
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
        except sqlite3.Error as e:
            self.logger.error(f"Database error retrieving PDF path for ID {pdf_id}: {e}")
            messagebox.showerror("Database Error", f"Failed to retrieve PDF information: {e}")
            return None
        except (ValueError, TypeError) as e:
            self.logger.error(f"Invalid PDF ID: {pdf_id}, error: {e}")
            messagebox.showerror("Invalid ID", "The selected PDF ID is invalid.")
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
            doc: fitz.Document = fitz.open(pdf_path)
            self.total_pages = len(doc)  # Set the total number of pages

            # Validate the page number
            self.page_number = validate_page_number(page_number, self.total_pages)
            self.show_pdf_page(page_number)

            # Update status bar
            self.status_var.set(f"Loaded: {os.path.basename(pdf_path)} - Page {page_number} of {self.total_pages}")
        except (FileNotFoundError, PermissionError, OSError) as e:
            self.logger.error(f"File system error opening PDF {pdf_path}: {e}")
            messagebox.showerror("File Error", f"Cannot access PDF file: {e}")
            self.current_pdf = None
        except (RuntimeError, ValueError) as e:
            # PyMuPDF raises RuntimeError for corrupted PDFs and ValueError for invalid files
            self.logger.error(f"Invalid or corrupted PDF {pdf_path}: {e}")
            messagebox.showerror("Invalid PDF", f"The PDF file appears to be corrupted or invalid: {e}")
            self.current_pdf = None

    def preview_selected_pdf(self) -> None:
        """Preview the selected PDF and display the corresponding page."""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Select an item", "Please select a search result first.")
            return

        selected_row = self.tree.item(selected_item)['values']
        pdf_id = int(selected_row[0])
        page_number = int(selected_row[2])  # This is the page number you want to preview
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
        # Validate and update zoom factor
        self.zoom_factor = validate_zoom_factor(self.zoom_factor + delta)
        self.show_pdf_page(self.page_number)
        self.status_var.set(f"Zoom: {int(self.zoom_factor * 100)}%")

    def first_results_page(self) -> None:
        """Go to the first page of search results."""
        if self.current_page > 0:
            self.current_page = 0
            self.load_search_results()
    
    def last_results_page(self) -> None:
        """Go to the last page of search results."""
        if self.current_page < self.total_pages - 1:
            self.current_page = self.total_pages - 1
            self.load_search_results()
    
    def next_results_page(self) -> None:
        """Go to the next page of search results."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.load_search_results()
            
    def prev_results_page(self) -> None:
        """Go to the previous page of search results."""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_search_results()
            
    def update_pagination_controls(self) -> None:
        """Update the pagination controls based on current search state."""
        if self.total_results > 0:
            self.total_pages = (self.total_results + self.results_per_page - 1) // self.results_per_page
            
            # Update page label
            self.page_label.config(text=f"Page {self.current_page + 1} of {self.total_pages}")
            
            # Update results count
            self.results_count_label.config(text=f"Total results: {self.total_results}")
            
            # Update current range
            offset = self.current_page * self.results_per_page
            end_result = min(offset + self.results_per_page, self.total_results)
            self.current_range_label.config(text=f"Showing: {offset + 1}-{end_result}")
            
            # Enable/disable navigation buttons based on current page
            self.btn_first_page.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
            self.btn_prev_page.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
            self.btn_next_page.config(state=tk.NORMAL if self.current_page < self.total_pages - 1 else tk.DISABLED)
            self.btn_last_page.config(state=tk.NORMAL if self.current_page < self.total_pages - 1 else tk.DISABLED)
            
            # Show pagination controls
            self.pagination_frame.grid()
            
            # Update status bar
            self.status_var.set(
                f"Search complete: Found {self.total_results} results for '{self.current_search_term}'"
            )
        else:
            self.pagination_frame.grid_remove()  # Hide pagination controls
            self.status_var.set(f"No results found for: {self.current_search_term}")
            
    def load_search_results(self) -> None:
        """Load the current page of search results."""
        if not self.current_search_term:
            return
            
        # Calculate offset for pagination
        offset = self.current_page * self.results_per_page
        
        # Check if we have cached results
        cache_key = f"{self.current_search_term}_{self.current_page}_{self.use_fts}"
        cached_value = search_cache.get(cache_key)
        cached_results: Optional[List[Tuple[Any, ...]]] = cached_value if isinstance(cached_value, list) else None

        if cached_results:
            self.logger.info(f"Using cached search results for '{self.current_search_term}' page {self.current_page + 1}")
            self.update_treeview(cached_results)
            return
            
        # Perform the search
        try:
            with memory_usage_tracking(f"Search for '{self.current_search_term}'"):
                results = self.db.search_text(
                    self.current_search_term,
                    use_fts=self.use_fts,
                    limit=self.results_per_page,
                    offset=offset
                )

                # Cache the results
                search_cache.put(cache_key, results)

                # Update the UI
                self.update_treeview(results)

                # Update status bar with pagination info
                offset = self.current_page * self.results_per_page
                end_result = min(offset + len(results), self.total_results)

                # Update the tree heading to show search info
                self.tree.heading("Context", text=f"Context (Showing {offset + 1}-{end_result} of {self.total_results} results)")
        except sqlite3.Error as e:
            self.logger.error(f"Database error loading search results: {e}")
            messagebox.showerror("Database Error", f"Failed to retrieve search results: {e}")
        except (ValueError, TypeError) as e:
            self.logger.error(f"Invalid search parameters: {e}")
            messagebox.showerror("Search Error", f"Invalid search parameters: {e}")
            
    def search_keywords(self) -> None:
        """Search the database for context in both PDF text and OCR-extracted text."""
        # Check if a search is already in progress
        if self.search_in_progress:
            self.logger.info("Search already in progress, ignoring new request")
            return

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

        # Mark search as in progress
        self.search_in_progress = True

        # Clear previous results
        self.clear_tree()

        # Update search state
        self.current_search_term = search_term
        self.current_page = 0
        self.use_fts = self.use_fts_var.get()

        # Reset tree headings
        self.tree.heading("Context", text="Context")

        # Update status
        self.status_var.set(f"Searching for: {search_term}... This may take a moment for large result sets.")
        
        # Check if we have cached count
        count_cache_key = f"count_{search_term}_{self.use_fts}"
        cached_count_value: Optional[Union[int, List[Tuple[Any, ...]]]] = search_cache.get(count_cache_key)

        def search_db() -> None:
            try:
                # Get the total count of results for pagination
                # Type narrow: count cache values are always int, not list
                if cached_count_value is not None and isinstance(cached_count_value, int):
                    self.total_results = cached_count_value
                    self.logger.info(f"Using cached count for '{search_term}': {self.total_results}")
                else:
                    with memory_usage_tracking(f"Count results for '{search_term}'"):
                        self.total_results = self.db.get_search_count(search_term, use_fts=self.use_fts)
                        search_cache.put(count_cache_key, self.total_results)

                # Update pagination controls
                self.root.after(0, self.update_pagination_controls)

                # Load the first page of results
                self.root.after(0, self.load_search_results)

                # Force garbage collection after search
                force_garbage_collection()

            except sqlite3.Error as e:
                self.logger.error(f"Database error during search: {e}")
                self.root.after(0, lambda: messagebox.showerror("Database Error", f"Search failed: {e}"))
                self.root.after(0, lambda: self.status_var.set("Search error - database issue"))
            except (ValueError, TypeError) as e:
                self.logger.error(f"Invalid search parameters: {e}")
                self.root.after(0, lambda: messagebox.showerror("Search Error", f"Invalid search: {e}"))
                self.root.after(0, lambda: self.status_var.set("Search error - invalid parameters"))
            finally:
                # Always reset the search flag when done
                self.root.after(0, lambda: setattr(self, 'search_in_progress', False))

        # Start search in a daemon thread so it doesn't block app shutdown
        search_thread = threading.Thread(target=search_db, daemon=True)
        search_thread.start()

    def update_treeview(self, rows: List[Tuple[Any, ...]]) -> None:
        """
        Update the treeview with the search results.

        Args:
            rows: Search result rows (tuples of: pdf_id, file_name, page_number, text, source)
        """
        self.clear_tree()
        if not rows:
            return
            
        for row in rows:
            # Truncate context text if too long
            values = list(row)
            if len(values[3]) > 100:  # Truncate context if too long
                values[3] = values[3][:100] + "..."
            # Note: The database returns 6 columns but we only display 5 in the treeview
            # The last_accessed column is used for sorting but not displayed
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
            
            # Check if we have a cached page image
            cache_key = f"{self.current_pdf}_{page_number}_{self.zoom_factor}"
            cached_image: Optional[ImageTk.PhotoImage] = pdf_cache.get(cache_key)

            if cached_image:
                self.logger.info(f"Using cached page image for {os.path.basename(self.current_pdf)} page {page_number}")
                img_tk: ImageTk.PhotoImage = cached_image

                # Configure canvas scrollregion
                self.canvas.config(scrollregion=(0, 0, img_tk.width(), img_tk.height()))

                # Display the image in the canvas
                self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
                self.current_image = img_tk  # Keep a reference to avoid garbage collection

                # Update status bar
                self.status_var.set(f"Loaded: {os.path.basename(self.current_pdf)} - Page {page_number} of {self.total_pages}")
                return
            
            # Open the PDF file
            with memory_usage_tracking(f"Rendering PDF page {page_number}"):
                doc: fitz.Document = fitz.open(self.current_pdf)

                # Validate page number
                validated_page = validate_page_number(page_number, len(doc))
                if validated_page != page_number:
                    page_number = validated_page
                    self.page_number = validated_page

                page_index = page_number - 1  # Page number starts from 1
                page: fitz.Page = doc.load_page(page_index)

                # Validate zoom factor
                validated_zoom = validate_zoom_factor(self.zoom_factor)
                if validated_zoom != self.zoom_factor:
                    self.zoom_factor = validated_zoom

                # Render the page
                pix: fitz.Pixmap = page.get_pixmap(matrix=fitz.Matrix(self.zoom_factor, self.zoom_factor))

                # Convert to a PIL Image
                img: Image.Image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

                # Convert the image to ImageTk format for tkinter
                img_tk: ImageTk.PhotoImage = ImageTk.PhotoImage(img)

                # Cache the rendered page
                pdf_cache.put(cache_key, img_tk)

                # Configure canvas scrollregion
                self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))

                # Display the image in the canvas
                self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
                self.current_image = img_tk  # Keep a reference to avoid garbage collection

                # Update status bar
                self.status_var.set(f"Loaded: {os.path.basename(self.current_pdf)} - Page {page_number} of {len(doc)}")
                
                # Force garbage collection after rendering
                force_garbage_collection()
        except (FileNotFoundError, PermissionError) as e:
            self.logger.error(f"File system error rendering PDF page {page_number}: {e}")
            messagebox.showerror("File Error", f"Cannot access PDF file: {e}")
            self.current_pdf = None
        except (RuntimeError, ValueError) as e:
            # PyMuPDF errors during rendering
            self.logger.error(f"PDF rendering error on page {page_number}: {e}")
            messagebox.showerror("Rendering Error", f"Failed to render PDF page: {e}")
        except MemoryError as e:
            # Memory exhaustion
            self.logger.error(f"Out of memory rendering page {page_number}: {e}")
            messagebox.showerror("Memory Error", "Insufficient memory to render PDF page.")
            force_garbage_collection()  # Try to free up memory
        except OSError as e:
            # Other I/O or system errors
            self.logger.error(f"System error rendering page {page_number}: {e}")
            messagebox.showerror("System Error", f"System error while rendering PDF: {e}")

    def clear_tree(self) -> None:
        """Clear the treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)
