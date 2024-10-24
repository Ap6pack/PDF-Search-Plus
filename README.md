# PDF Search and OCR Application

This Python application processes PDF files by extracting text from the pages and images, applying OCR (Optical Character Recognition) to images, and storing the results in a SQLite database. It provides a graphical user interface (GUI) built with `Tkinter` to search and preview the PDF content, including OCR-extracted text.

## Features

- Extracts and stores text from PDF pages.
- Extracts images from PDF pages and applies OCR using Tesseract.
- Stores image metadata and OCR-extracted text into the SQLite database.
- Provides a user-friendly GUI for searching through the stored data, including PDF text and OCR text.
- Allows for both single-file and folder-based (batch) PDF processing.
- Enables preview of PDFs with zoom and navigation features.

## Prerequisites

Before running the application, you need to install the following dependencies:

- Python 3.x
- [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/en/latest/)
- [Pillow (PIL)](https://pillow.readthedocs.io/en/stable/)
- [pytesseract](https://pypi.org/project/pytesseract/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (must be installed separately)

### Installation Instructions

1. Install the required Python packages using `pip`:

   ```bash
   pip install pymupdf Pillow pytesseract
   ```

2. Install Tesseract OCR:

   - On **Ubuntu**:
     ```bash
     sudo apt install tesseract-ocr
     ```
   - On **MacOS** (using Homebrew):
     ```bash
     brew install tesseract
     ```
   - On **Windows**:
     Download and install from [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki).

3. Ensure that `tesseract` is in your system’s PATH.

### Database Schema

The application stores PDF data in an SQLite database called `pdf_data.db`. The following tables are used to store the extracted data:

- **pdf_files**: Stores metadata for each processed PDF file.
  ```sql
  CREATE TABLE pdf_files (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      file_name TEXT,
      file_path TEXT
  );
  ```

- **pages**: Stores text extracted from each PDF page.
  ```sql
  CREATE TABLE pages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      pdf_id INTEGER,
      page_number INTEGER,
      text TEXT,
      FOREIGN KEY(pdf_id) REFERENCES pdf_files(id)
  );
  ```

- **images**: Stores metadata about extracted images from the PDF.
  ```sql
  CREATE TABLE images (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      pdf_id INTEGER,
      page_number INTEGER,
      image_name TEXT,
      image_ext TEXT,
      FOREIGN KEY(pdf_id) REFERENCES pdf_files(id)
  );
  ```

- **ocr_text**: Stores the text extracted via OCR from images.
  ```sql
  CREATE TABLE ocr_text (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      pdf_id INTEGER,
      page_number INTEGER,
      ocr_text TEXT,
      FOREIGN KEY(pdf_id) REFERENCES pdf_files(id)
  );
  ```

### Usage

1. **Running the Application**:

   To start the application, run the `main()` function in the script:

   ```bash
   python pdf_search_gui.py
   ```

   This will launch a GUI allowing you to process PDF files and search their contents.

2. **Processing PDF Files**:

   - The application provides two options:
     - **Single File**: Select a single PDF file to process.
     - **Batch Processing**: Select a folder containing multiple PDFs for processing.
   
   After processing, the text, images, and OCR data will be stored in the SQLite database.

3. **Searching for Text**:

   In the GUI, enter a search term and press "Search". The application will search both PDF page text and OCR-extracted text from images. The results will be displayed in a table, showing the PDF file name, page number, and matching context.

4. **Previewing PDF Pages**:

   From the search results, you can select a PDF and page to preview. The selected PDF page will be displayed in the right-hand pane of the GUI, with zoom and navigation controls available.

### Code Structure

- **PDF Processing**: The script uses `PyMuPDF` (fitz) to extract text and images from PDF files. The images are passed through `pytesseract` to perform OCR, and the extracted text is stored in the database.
  
- **Database Interaction**: The script inserts extracted PDF text, image metadata, and OCR results into the SQLite database. It provides search functionality for both PDF text and OCR-extracted text.

### How It Works

1. **Text Extraction**: For each page in the PDF, text is extracted and inserted into the `pages` table in the database.
   
2. **Image Extraction and OCR**: For each image found in the PDF, metadata is saved in the `images` table. The image is then passed to `pytesseract` to extract text via OCR, and the result is stored in the `ocr_text` table.

3. **Search**: The user can search both the `pages` table (PDF text) and the `ocr_text` table (OCR text from images). The results are combined and displayed in the GUI.

4. **Preview**: The selected PDF file is opened and rendered in the GUI's canvas area, allowing the user to view the selected page.

### Example Usage

1. **Single PDF File**:
   - Open the application.
   - Choose a PDF file to process.
   - Search for text or OCR data using the search bar.
   - View the search results and select a page to preview.

2. **Batch Processing**:
   - Select a folder containing multiple PDF files.
   - The application will process all PDFs and extract text, images, and OCR data.
   - Perform searches across all processed files.

### Error Handling and Logging

- All errors during processing are logged to `app.log`, and the user is notified of issues via GUI pop-up messages.

### License

This project is open-source and available under the [MIT License](LICENSE).

---

### Future Enhancements

- Add support for exporting search results.
- Improve image OCR accuracy with advanced preprocessing.
- Add annotations for highlighted text in preview mode.