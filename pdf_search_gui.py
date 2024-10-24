import os
import sqlite3
import fitz  # PyMuPDF
import tkinter as tk
from tkinter import ttk, messagebox, Canvas
from PIL import Image, ImageTk
import threading  # For threading long operations
import logging

# Configure logging to track errors
logging.basicConfig(filename='app.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

class PDFSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Search and Preview")
        self.root.geometry("800x600")  # Default window size

        # PDF state
        self.current_pdf = None
        self.page_number = 1
        self.total_pages = 0
        self.zoom_factor = 1.0

        # Initialize UI components
        self.create_widgets()

    def create_widgets(self):
        # Search input fields
        frame_search = tk.Frame(self.root)
        frame_search.grid(row=0, column=0, columnspan=8, padx=10, pady=10, sticky='ew')

        tk.Label(frame_search, text="Context").grid(row=0, column=2, padx=10, pady=10)
        self.context_entry = tk.Entry(frame_search)
        self.context_entry.grid(row=0, column=3, padx=10, pady=10)

        tk.Button(frame_search, text="Search", command=self.search_keywords).grid(row=0, column=4, padx=10, pady=10)

        # Treeview for displaying search results
        self.tree = ttk.Treeview(self.root, columns=("PDF ID", "File Name", "Page Number", "Context", "Source"), show="headings")
        self.tree.heading("PDF ID", text="PDF ID")
        self.tree.heading("File Name", text="File Name")
        self.tree.heading("Page Number", text="Page Number")
        self.tree.heading("Context", text="Context")
        self.tree.heading("Source", text="Source")  # New column to indicate the source of text (OCR or PDF text)
        self.tree.grid(row=1, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')

        # Embedded PDF preview using a Canvas
        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.grid(row=1, column=4, columnspan=4, padx=10, pady=10, sticky='nsew')
        self.canvas = Canvas(self.canvas_frame, width=600, height=800)
        self.canvas.grid(row=0, column=0, sticky='nsew')

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

        # Make sure the layout expands properly
        self.root.grid_rowconfigure(1, weight=1)  # Make row 1 (tree and canvas) expandable
        self.root.grid_columnconfigure(0, weight=1)  # Make treeview expand
        self.root.grid_columnconfigure(4, weight=1)  # Make canvas column expandable

    def get_pdf_path(self, pdf_id):
        """Fetch the PDF file path for a given ID."""
        try:
            result = self.execute_query("SELECT file_path FROM pdf_files WHERE id = ?", (pdf_id,))
            if result:
                return result[0][0]
            return None
        except sqlite3.DatabaseError as e:
            logging.error(f"Database error: {e}")
            messagebox.showerror("Database Error", str(e))
            return None

    def load_pdf(self, pdf_path, page_number=1):
        """Load the selected PDF and display the provided page number."""
        if not os.path.exists(pdf_path):
            messagebox.showerror("File Not Found", f"The file {pdf_path} does not exist.")
            return

        try:
            self.current_pdf = pdf_path  # Store the current PDF path
            doc = fitz.open(pdf_path)
            self.total_pages = len(doc)  # Set the total number of pages
            self.page_number = page_number  # Start at the provided page number
            self.show_pdf_page(page_number)
        except Exception as e:
            logging.error(f"Error opening PDF: {e}")
            messagebox.showerror("Error", f"An error occurred while opening the PDF: {e}")

    def preview_selected_pdf(self):
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

    def next_page(self):
        """Go to the next page in the PDF preview."""
        if self.current_pdf and self.page_number < self.total_pages:
            self.page_number += 1
            self.show_pdf_page(self.page_number)

    def prev_page(self):
        """Go to the previous page in the PDF preview."""
        if self.current_pdf and self.page_number > 1:
            self.page_number -= 1
            self.show_pdf_page(self.page_number)

    def update_zoom_factor(self, delta):
        """Update zoom factor by a given delta and refresh the current page."""
        new_zoom = self.zoom_factor + delta
        if 0.5 <= new_zoom <= 3.0:  # Set a range for zoom factor
            self.zoom_factor = new_zoom
            self.show_pdf_page(self.page_number)

    def search_keywords(self):
        """Search the database for context in both PDF text and OCR-extracted text."""
        context = self.context_entry.get().lower()

        def search_db():
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
            params = [f'%{context}%', f'%{context}%']

            try:
                rows = self.execute_query(query, params)
                self.root.after(0, self.update_treeview, rows)  # Safely update Treeview
            except sqlite3.DatabaseError as e:
                logging.error(f"Database error: {e}")
                self.root.after(0, lambda error=e: messagebox.showerror("Database Error", str(error)))

        threading.Thread(target=search_db).start()

    def update_treeview(self, rows):
        """Update the treeview with the search results."""
        self.clear_tree()
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def execute_query(self, query, params=()):
        """Execute a database query with given parameters."""
        with sqlite3.connect('pdf_data.db', check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def show_pdf_page(self, page_number):
        """Display the selected PDF page in the embedded Canvas."""
        if self.current_pdf is None:
            messagebox.showerror("Error", "No PDF file loaded.")
            return

        if not os.path.exists(self.current_pdf):
            messagebox.showerror("File Not Found", f"The file {self.current_pdf} does not exist.")
            return

        try:
            doc = fitz.open(self.current_pdf)
            page_index = page_number - 1  # Page number starts from 1

            if 0 <= page_index < len(doc):
                page = doc.load_page(page_index)
                pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom_factor, self.zoom_factor))

                # Convert to a PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # Convert the image to ImageTk format for tkinter
                img_tk = ImageTk.PhotoImage(img)

                # Display the image in the canvas
                self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
                self.canvas.image = img_tk  # Keep a reference to avoid garbage collection
            else:
                messagebox.showerror("Page Not Found", f"Page {page_number} is not valid.")
        except Exception as e:
            logging.error(f"Error displaying PDF page: {e}")
            messagebox.showerror("Error", f"An error occurred while displaying the PDF page: {e}")

    def clear_tree(self):
        """Clear the treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSearchApp(root)
    root.mainloop()
