# PDF Search Plus

PDF Search Plus is a Python application that processes PDF files by extracting text from pages and images, applying OCR (Optical Character Recognition) to images, and storing the results in a SQLite database. It provides a graphical user interface (GUI) built with Tkinter to search and preview the PDF content, including OCR-extracted text.

## Features

- Extracts and stores text from PDF pages
- Extracts images from PDF pages and applies OCR using Tesseract or EasyOCR
- Stores image metadata and OCR-extracted text in a SQLite database
- Provides a user-friendly GUI for searching through the stored data
- Allows for both single-file and folder-based (batch) PDF processing
- Enables preview of PDFs with zoom and navigation features

## Installation

### Option 1: Install from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/username/pdf-search-plus.git
   cd pdf-search-plus
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

### Option 2: Install from PyPI

```bash
pip install pdf-search-plus
```

### OCR Engine Requirements

#### Tesseract OCR

If you want to use Tesseract OCR (default):

- On Ubuntu:
  ```bash
  sudo apt install tesseract-ocr
  ```
- On macOS (using Homebrew):
  ```bash
  brew install tesseract
  ```
- On Windows:
  Download and install from [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki).

Ensure that `tesseract` is in your system's PATH.

#### EasyOCR

EasyOCR is included in the package dependencies and doesn't require separate installation.

## Usage

### Running the Application

#### Using the Command Line

1. Run with Tesseract OCR (default):
   ```bash
   pdf-search-plus
   ```
   or
   ```bash
   python -m pdf_search_plus.main
   ```

2. Run with EasyOCR:
   ```bash
   pdf-search-plus --easyocr
   ```
   or
   ```bash
   python -m pdf_search_plus.main --easyocr
   ```

#### Using the Provided Scripts

1. Run with Tesseract OCR:
   ```bash
   python run_pdf_search.py
   ```

2. Run with EasyOCR:
   ```bash
   python run_pdf_search_easyocr.py
   ```

### Application Workflow

1. **Processing PDF Files**:
   - Click "Process PDF" in the main window
   - Choose between single file or folder (batch) processing
   - Select the PDF file or folder to process
   - Wait for the processing to complete

2. **Searching for Text**:
   - Click "Search PDFs" in the main window
   - Enter a search term in the context field
   - Click "Search"
   - View the results showing PDF file name, page number, and matching context

3. **Previewing PDF Pages**:
   - Select a search result
   - Click "Preview PDF"
   - Use the navigation buttons to move between pages
   - Use the zoom buttons to adjust the view

## Package Structure

```
pdf_search_plus/
├── __init__.py
├── main.py
├── core/
│   ├── __init__.py
│   ├── pdf_processor.py
│   └── ocr/
│       ├── __init__.py
│       ├── base.py
│       ├── tesseract.py
│       └── easyocr.py
├── gui/
│   ├── __init__.py
│   └── search_app.py
└── utils/
    ├── __init__.py
    └── db.py
```

## Database Schema

The application stores PDF data in an SQLite database called `pdf_data.db` with the following tables:

- **pdf_files**: Stores metadata for each processed PDF file
- **pages**: Stores text extracted from each PDF page
- **images**: Stores metadata about extracted images from the PDF
- **ocr_text**: Stores the text extracted via OCR from images

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Future Enhancements

- Add support for exporting search results
- Improve image OCR accuracy with advanced preprocessing
- Add annotations for highlighted text in preview mode
- Support for more languages in OCR
- Advanced search options (regex, date filters, etc.)
