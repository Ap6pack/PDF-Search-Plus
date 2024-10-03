import os
import io
import re  # Regular expressions for exact keyword matching
import fitz  # PyMuPDF
from PIL import Image
import sqlite3
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox


# Functions to interact with the database (inserting data)
def insert_pdf_file(conn, file_name, file_path):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pdf_files (file_name, file_path) VALUES (?, ?)", (file_name, file_path))
    conn.commit()
    return cursor.lastrowid  # Return the ID of the inserted record


def insert_page_text(conn, pdf_id, page_number, text):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pages (pdf_id, page_number, text) VALUES (?, ?, ?)", (pdf_id, page_number, text))
    conn.commit()


def insert_image_metadata(conn, pdf_id, page_number, image_name, image_ext):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO images (pdf_id, page_number, image_name, image_ext) VALUES (?, ?, ?, ?)", 
                   (pdf_id, page_number, image_name, image_ext))
    conn.commit()


def insert_keyword_result(conn, pdf_id, page_number, keyword, context):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO keywords (pdf_id, page_number, keyword, context) VALUES (?, ?, ?, ?)", 
                   (pdf_id, page_number, keyword, context))
    conn.commit()


def search_keywords_in_text(text, keywords):
    """Search for exact keyword matches in the provided text."""
    results = {}

    # Iterate over each keyword to find exact matches
    for keyword in keywords:
        keyword = keyword.lower()
        # Use regular expression to match whole words, case-insensitive
        pattern = r'\b' + re.escape(keyword) + r'\b'
        matches = re.findall(pattern, text, flags=re.IGNORECASE)

        if matches:
            # Collect surrounding context (line where the match was found)
            occurrences = []
            for line in text.splitlines():
                if re.search(pattern, line, flags=re.IGNORECASE):
                    occurrences.append(line.strip())
            if occurrences:
                results[keyword] = occurrences

    return results

def process_pdf(conn, pdf_path, keyword_list):
    # Extract the filename without extension and path
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    # Insert PDF metadata into the database
    pdf_id = insert_pdf_file(conn, base_name, pdf_path)

    # Create output directories for text, images, and keywords
    output_dir = os.path.join(os.getcwd(), base_name)
    text_dir = os.path.join(output_dir, "text")
    images_dir = os.path.join(output_dir, "images")
    keywords_dir = os.path.join(output_dir, "keywords")

    os.makedirs(text_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(keywords_dir, exist_ok=True)

    # Open the PDF file
    with fitz.open(pdf_path) as pdf_file:
        keyword_results = {}

        # Iterate over PDF pages
        for page_index, page in enumerate(pdf_file):
            # Extract text
            text = page.get_text()

            # Insert page text into the database
            insert_page_text(conn, pdf_id, page_index + 1, text)  # Page number starts from 1

            # Save text of each page to file
            page_text_filename = os.path.join(text_dir, f"page_{page_index + 1}.txt")
            with open(page_text_filename, "w", encoding="utf-8") as f:
                f.write(text)

            # Search for keywords on each page
            page_results = search_keywords_in_text(text, keyword_list)
            if page_results:
                keyword_results[f"Page {page_index + 1}"] = page_results

                # Insert keywords into the database
                for keyword, occurrences in page_results.items():
                    for occurrence in occurrences:
                        insert_keyword_result(conn, pdf_id, page_index + 1, keyword, occurrence)

            # Extract images
            image_list = page.get_images(full=True)
            if image_list:
                for image_index, img in enumerate(image_list, start=1):
                    xref = img[0]
                    base_image = pdf_file.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    image = Image.open(io.BytesIO(image_bytes))

                    # Define the output path for the image
                    image_filename = os.path.join(images_dir, f"image_page{page_index + 1}_{image_index}.{image_ext}")
                    image.save(image_filename)

                    # Insert image metadata into the database
                    insert_image_metadata(conn, pdf_id, page_index + 1, f"image_page{page_index + 1}_{image_index}", image_ext)

        # Save the keyword search results
        if keyword_results:
            keyword_output_file = os.path.join(keywords_dir, f"{base_name}_keyword_results.txt")
            with open(keyword_output_file, "w", encoding="utf-8") as f:
                for page, results in keyword_results.items():
                    f.write(f"\n{page}\n")
                    f.write("=" * 20 + "\n")
                    for keyword, occurrences in results.items():
                        f.write(f"\nKeyword: {keyword}\n")
                        f.write("-" * 10 + "\n")
                        for occurrence in occurrences:
                            f.write(f"{occurrence}\n")

                    # Insert keywords into the database
                    for keyword, occurrences in results.items():
                        for occurrence in occurrences:
                            insert_keyword_result(conn, pdf_id, page_index + 1, keyword, occurrence)


def main():
    # Initialize tkinter root
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    # Connect to the existing database
    conn = sqlite3.connect('pdf_data.db')

    # Ask the user if they want to scan a single file or multiple files
    scan_type = messagebox.askquestion(
        "Select Scanning Type", "Do you want to scan a folder (mass scanning)?"
    )

    if scan_type == 'yes':  # Mass scanning
        folder_path = filedialog.askdirectory(
            title="Select Folder with PDFs for Mass Scanning"
        )

        if not folder_path:
            print("No folder selected. Exiting.")
            return

        # Ask the user to input keywords
        keywords = simpledialog.askstring(
            "Keyword Input",
            "Enter keywords separated by commas (e.g., security, AI, attack):"
        )
        if not keywords:
            print("No keywords provided. Exiting.")
            return

        # Split keywords and clean up any extra spaces
        keyword_list = [kw.strip() for kw in keywords.split(",")]

        # Process each PDF file in the selected folder
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith(".pdf"):
                pdf_path = os.path.join(folder_path, file_name)
                print(f"Processing file: {file_name}")
                process_pdf(conn, pdf_path, keyword_list)
        print(f"Mass scanning completed. Results are saved in the working directory.")

    else:  # Single file scanning
        # Open file dialog to select a single PDF file
        pdf_path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF Files", "*.pdf")],
        )

        if not pdf_path:
            print("No file selected. Exiting.")
            return

        # Ask the user to input keywords
        keywords = simpledialog.askstring(
            "Keyword Input",
            "Enter keywords separated by commas (e.g., security, AI, attack):"
        )
        if not keywords:
            print("No keywords provided. Exiting.")
            return

        # Split keywords and clean up any extra spaces
        keyword_list = [kw.strip() for kw in keywords.split(",")]

        # Process the selected single PDF file
        process_pdf(conn, pdf_path, keyword_list)

    conn.close()
    print("Processing completed.")


if __name__ == "__main__":
    main()
