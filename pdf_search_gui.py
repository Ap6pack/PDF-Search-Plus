import os
import sqlite3
import fitz  # PyMuPDF
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import Toplevel
from PIL import Image, ImageTk


class PDFSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Search and Preview")
        self.root.geometry("900x600")

        # Initialize database connection
        self.conn = sqlite3.connect('pdf_data.db')
        self.cursor = self.conn.cursor()

        # Initialize UI components
        self.create_widgets()

    def create_widgets(self):
        # Search input fields
        tk.Label(self.root, text="Keyword").grid(row=0, column=0, padx=10, pady=10)
        self.keyword_entry = tk.Entry(self.root)
        self.keyword_entry.grid(row=0, column=1, padx=10, pady=10)

        tk.Label(self.root, text="Context").grid(row=1, column=0, padx=10, pady=10)
        self.context_entry = tk.Entry(self.root)
        self.context_entry.grid(row=1, column=1, padx=10, pady=10)

        # Search button
        tk.Button(self.root, text="Search", command=self.search_keywords).grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        # Treeview for displaying search results
        self.tree = ttk.Treeview(self.root, columns=("PDF ID", "File Name", "Page Number", "Keyword", "Context"), show="headings")
        self.tree.heading("PDF ID", text="PDF ID")
        self.tree.heading("File Name", text="File Name")
        self.tree.heading("Page Number", text="Page Number")
        self.tree.heading("Keyword", text="Keyword")
        self.tree.heading("Context", text="Context")
        self.tree.grid(row=3, column=0, columnspan=4, padx=10, pady=10)

        # Button to open selected PDF at the specified page
        tk.Button(self.root, text="Open PDF", command=self.open_selected_pdf).grid(row=4, column=0, columnspan=2, padx=10, pady=10)

    def search_keywords(self):
        """Search the database for keywords and context."""
        keyword = self.keyword_entry.get()
        context = self.context_entry.get()

        query = "SELECT pdf_files.id, pdf_files.file_name, keywords.page_number, keywords.keyword, keywords.context " \
                "FROM keywords " \
                "JOIN pdf_files ON keywords.pdf_id = pdf_files.id " \
                "WHERE 1=1"
        params = []

        if keyword:
            query += " AND keywords.keyword LIKE ?"
            params.append(f'%{keyword}%')

        if context:
            query += " AND keywords.context LIKE ?"
            params.append(f'%{context}%')

        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()

        self.clear_tree()
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def open_selected_pdf(self):
        """Open the selected PDF and display the corresponding page."""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Select an item", "Please select a search result first.")
            return

        # Get selected search result
        selected_row = self.tree.item(selected_item)['values']
        pdf_id = selected_row[0]
        file_name = selected_row[1]
        page_number = selected_row[2]

        pdf_path = self.get_pdf_path(pdf_id)

        if pdf_path:
            self.open_pdf_at_page(pdf_path, page_number)
        else:
            messagebox.showerror("File Not Found", "The selected PDF file could not be found.")

    def get_pdf_path(self, pdf_id):
        """Get the file path for a PDF given its ID."""
        self.cursor.execute("SELECT file_path FROM pdf_files WHERE id = ?", (pdf_id,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        return None

    def open_pdf_at_page(self, pdf_path, page_number):
        """Open the PDF at the specified page using PyMuPDF."""
        if not os.path.exists(pdf_path):
            messagebox.showerror("File Not Found", f"The file {pdf_path} does not exist.")
            return

        # Open the PDF file
        doc = fitz.open(pdf_path)

        # Ensure the page number is valid
        if 0 <= page_number - 1 < len(doc):
            self.show_pdf_page(doc, page_number - 1)
        else:
            messagebox.showerror("Page Error", "Invalid page number.")

    def show_pdf_page(self, doc, page_index):
        """Display a preview of the selected PDF page in a new window."""
        page = doc.load_page(page_index)
        pix = page.get_pixmap()

        # Convert to a PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Display the image in a new window
        new_window = Toplevel(self.root)
        new_window.title(f"Page {page_index + 1}")
        new_window.geometry(f"{pix.width}x{pix.height}")

        img_tk = ImageTk.PhotoImage(img)
        panel = tk.Label(new_window, image=img_tk)
        panel.image = img_tk
        panel.pack()

    def clear_tree(self):
        """Clear the treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)

    def __del__(self):
        """Close the database connection when the application is closed."""
        self.conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSearchApp(root)
    root.mainloop()
