# PDF Search Plus

<div align="center">

![PDF Search Plus Logo](https://img.shields.io/badge/PDF-Search%20Plus-blue)
![Version](https://img.shields.io/badge/version-2.2.0-green)
![License](https://img.shields.io/badge/license-MIT-blue)

</div>

PDF Search Plus is a powerful Python application that processes PDF files by extracting text from pages and images, applying OCR (Optical Character Recognition) to images, and storing the results in a SQLite database. It provides a graphical user interface (GUI) built with Tkinter to search and preview the PDF content, including OCR-extracted text.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [Setup](#setup)
  - [Tesseract OCR Installation](#tesseract-ocr-installation)
- [Python Dependencies](#python-dependencies)
- [Usage](#usage)
  - [Running the Application](#running-the-application)
  - [Application Workflow](#application-workflow)
- [Package Structure](#package-structure)
- [Database Schema](#database-schema)
- [Performance Optimizations](#performance-optimizations)
- [Security Features](#security-features)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)
- [Future Enhancements](#future-enhancements)

## Features

- Extracts and stores text from PDF pages
- Extracts images from PDF pages and applies OCR using Tesseract
- Stores image metadata and OCR-extracted text in a SQLite database
- Provides a user-friendly GUI for searching through the stored data
- Allows for both single-file and folder-based (batch) PDF processing
- Enables preview of PDFs with zoom and navigation features
- **Security features** including input validation, sanitization, and SQL injection protection
- **Caching system** for PDF pages, search results, and images to improve performance
- **Memory management** for efficiently handling large PDFs
- **Pagination** for search results to handle large document collections
- **Full-text search** capabilities using SQLite FTS5 for fast and efficient searching

## Installation

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Ap6pack/pdf-search-plus.git
   cd pdf-search-plus
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Tesseract OCR Installation

The application requires the Tesseract OCR command-line tool to be installed on your system:

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

Ensure that the `tesseract` command is in your system's PATH. The application calls this command directly rather than using a Python wrapper.

## Python Dependencies

All Python dependencies are specified in the `requirements.txt` file and should be installed as mentioned in the Installation section above.

### Dependency Conflicts

When installing the requirements, you may encounter dependency conflicts, particularly with numpy versions. If you see errors related to numpy version conflicts (e.g., with packages like thinc or spacy), you may need to uninstall the conflicting packages:

```bash
pip uninstall -y thinc spacy
pip install -r requirements.txt
```

This is because the application requires numpy<2.0 for compatibility with pandas 2.2.0, which may conflict with other packages that require numpy>=2.0.0.

## Usage

### Running the Application

#### Using the Command Line

The application can be run using the unified command-line script:

```bash
python run_pdf_search.py [options]
```

##### Options:

- `--verbose`, `-v`: Enable verbose logging
- `--process-file FILE`: Process a single PDF file without launching the GUI
- `--process-folder FOLDER`: Process all PDF files in a folder without launching the GUI
- `--search TERM`: Search for a term in the database without launching the GUI
- `--max-workers N`: Maximum number of worker threads for batch processing (default: 5)

##### Examples:

1. Launch the GUI:
   ```bash
   python run_pdf_search.py
   ```

2. Process a single PDF file from the command line:
   ```bash
   python run_pdf_search.py --process-file path/to/document.pdf
   ```

3. Process a folder of PDF files:
   ```bash
   python run_pdf_search.py --process-folder path/to/folder
   ```

4. Search the database from the command line:
   ```bash
   python run_pdf_search.py --search "search term"
   ```

#### Using the Python Module

You can also run the application as a Python module:

```bash
python -m pdf_search_plus.main
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
   - Toggle "Use Full-Text Search" option for faster searches on large collections
   - Click "Search"
   - View the results showing PDF file name, page number, and matching context
   - Use pagination controls to navigate through large result sets

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
│       └── tesseract.py
├── gui/
│   ├── __init__.py
│   └── search_app.py
└── utils/
    ├── __init__.py
    ├── db.py
    ├── cache.py
    ├── memory.py
    └── security.py
```

## Database Schema

The application stores PDF data in an SQLite database called `pdf_data.db` with the following structure:

### Tables

- **pdf_files**: Stores metadata for each processed PDF file
  - `id`: Primary key
  - `file_name`: Name of the PDF file
  - `file_path`: Path to the PDF file
  - `created_at`: Timestamp when the record was created
  - `last_accessed`: Timestamp when the record was last accessed

- **pages**: Stores text extracted from each PDF page
  - `id`: Primary key
  - `pdf_id`: Foreign key to pdf_files
  - `page_number`: Page number
  - `text`: Extracted text

- **images**: Stores metadata about extracted images from the PDF
  - `id`: Primary key
  - `pdf_id`: Foreign key to pdf_files
  - `page_number`: Page number
  - `image_name`: Name of the image
  - `image_ext`: Image extension

- **ocr_text**: Stores the text extracted via OCR from images
  - `id`: Primary key
  - `pdf_id`: Foreign key to pdf_files
  - `page_number`: Page number
  - `ocr_text`: Text extracted via OCR

### Full-Text Search

The database includes virtual tables for full-text search:

- **fts_content**: FTS5 virtual table for searching PDF text
- **fts_ocr**: FTS5 virtual table for searching OCR text

### Indexes

The database includes indexes for better performance:

- Indexes on `pdf_id` columns for faster joins
- Indexes on text columns for faster searching
- Indexes on file name and path for faster lookups

## Performance Optimizations

- **Caching**: The application caches PDF pages, search results, and images to improve performance
- **Memory Management**: Large PDFs are processed in a streaming fashion to reduce memory usage
- **Batch Processing**: Images are processed in batches to limit memory consumption
- **Full-Text Search**: SQLite FTS5 is used for fast and efficient text searching
- **Pagination**: Search results are paginated to handle large result sets efficiently

## Security Features

- **Input Validation**: All user inputs are validated before processing
- **Path Validation**: File paths are validated to prevent path traversal attacks
- **Sanitization**: Text is sanitized to prevent XSS and other injection attacks
- **SQL Injection Protection**: Parameterized queries are used to prevent SQL injection

## Contributing

Contributions are welcome! Here's how you can contribute to PDF Search Plus:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please make sure to update tests as appropriate and adhere to the existing coding style.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) for PDF processing capabilities
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for text recognition
- [SQLite](https://www.sqlite.org/) for database functionality
- All contributors who have helped improve this project

## Future Enhancements

- Add support for exporting search results
- Improve image OCR accuracy with advanced preprocessing
- Add annotations for highlighted text in preview mode
- Support for more languages in OCR
- Add document categorization and tagging
- Implement document similarity search
- Add support for PDF form field extraction
