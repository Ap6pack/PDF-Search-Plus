import os
import io
import fitz  # PyMuPDF
from PIL import Image
import easyocr
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np

# Initialize the EasyOCR reader (you can specify the languages supported, 'en' for English)
reader = easyocr.Reader(['en'])

# Database interaction functions (unchanged)
def insert_pdf_file(conn, file_name, file_path):
    """Insert metadata of the PDF file into the database."""
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pdf_files (file_name, file_path) VALUES (?, ?)", (file_name, file_path))
    conn.commit()
    return cursor.lastrowid

def insert_page_text(conn, pdf_id, page_number, text):
    """Insert text of each PDF page into the database."""
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pages (pdf_id, page_number, text) VALUES (?, ?, ?)", (pdf_id, page_number, text))
    conn.commit()

def insert_image_metadata(conn, pdf_id, page_number, image_name, image_ext):
    """Insert metadata of extracted images into the database."""
    cursor = conn.cursor()
    cursor.execute("INSERT INTO images (pdf_id, page_number, image_name, image_ext) VALUES (?, ?, ?, ?)",
                   (pdf_id, page_number, image_name, image_ext))
    conn.commit()

def insert_image_ocr_text(conn, pdf_id, page_number, ocr_text):
    """Insert the OCR text extracted from images into the database."""
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ocr_text (pdf_id, page_number, ocr_text) VALUES (?, ?, ?)", 
                   (pdf_id, page_number, ocr_text))
    conn.commit()

# PDF processing functions
def extract_text_and_save(page, page_number, conn, pdf_id):
    """Extract text from a PDF page and insert into the database."""
    text = page.get_text()
    insert_page_text(conn, pdf_id, page_number, text)

def extract_images_and_save(page, page_number, conn, pdf_id):
    """Extract images from a PDF page, apply OCR, and insert metadata and OCR text into the database."""
    image_list = page.get_images(full=True)
    if image_list:
        for image_index, img in enumerate(image_list, start=1):
            xref = img[0]
            base_image = page.parent.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image = Image.open(io.BytesIO(image_bytes))

            # Insert image metadata into the database
            insert_image_metadata(conn, pdf_id, page_number, f"image_page{page_number}_{image_index}", image_ext)

            # Convert PIL Image to NumPy array for EasyOCR
            image_np = np.array(image)

            # Apply EasyOCR to the image to extract text
            ocr_result = reader.readtext(image_np)
            ocr_text = " ".join([text[1] for text in ocr_result])  # Extract text from the OCR result

            if ocr_text.strip():
                # Insert OCR text into the database
                insert_image_ocr_text(conn, pdf_id, page_number, ocr_text)
                print(f"OCR text extracted from image on page {page_number}: {ocr_text[:100]}...")  # Display first 100 chars

def process_pdf(conn, pdf_path):
    """Process a single PDF file, extracting text and images, and storing them in the database."""
    try:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        pdf_id = insert_pdf_file(conn, base_name, pdf_path)

        with fitz.open(pdf_path) as pdf_file:
            for page_index, page in enumerate(pdf_file):
                page_number = page_index + 1
                extract_text_and_save(page, page_number, conn, pdf_id)
                extract_images_and_save(page, page_number, conn, pdf_id)

        print(f"Successfully processed PDF: {pdf_path}")

    except Exception as e:
        print(f"Error processing PDF {pdf_path}: {e}")
        messagebox.showerror("Error", f"An error occurred while processing the PDF: {e}")

# Main application functions (unchanged)
def process_selected_file(conn, pdf_path):
    """Process a single PDF file selected by the user."""
    if pdf_path:
        process_pdf(conn, pdf_path)
    else:
        print("No file selected. Exiting.")

def process_folder(conn, folder_path):
    """Process all PDF files in a selected folder."""
    if folder_path:
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith(".pdf"):
                pdf_path = os.path.join(folder_path, file_name)
                print(f"Processing file: {file_name}")
                process_pdf(conn, pdf_path)
        print("Mass scanning completed.")
    else:
        print("No folder selected. Exiting.")

def main():
    """Main function to run the tkinter-based file dialog for PDF scanning."""
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    conn = sqlite3.connect('pdf_data.db')

    scan_type = messagebox.askquestion("Select Scanning Type", "Do you want to scan a folder (mass scanning)?")
    
    if scan_type == 'yes':
        folder_path = filedialog.askdirectory(title="Select Folder with PDFs for Mass Scanning")
        process_folder(conn, folder_path)
    else:
        pdf_path = filedialog.askopenfilename(title="Select PDF File", filetypes=[("PDF Files", "*.pdf")])
        process_selected_file(conn, pdf_path)

    conn.close()
    print("Processing completed.")

if __name__ == "__main__":
    main()
