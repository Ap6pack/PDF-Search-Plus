# PDF Search Plus

<div align="center">

![PDF Search Plus Logo](https://img.shields.io/badge/PDF-Search%20Plus-blue)
![Version](https://img.shields.io/badge/version-2.4.4-green)
![License](https://img.shields.io/badge/license-MIT-blue)

</div>

PDF Search Plus is a powerful Python application that processes PDF files by extracting text from pages and images, applying OCR (Optical Character Recognition) to images, and storing the results in a SQLite database. It provides a graphical user interface (GUI) built with Tkinter to search and preview the PDF content, including OCR-extracted text.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
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
- [Document Tagging and Categorization](#document-tagging-and-categorization)
- [PDF Annotations](#pdf-annotations)
- [Document Similarity Search](#document-similarity-search)
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
- **Robust search** capabilities with optimized Full-Text Search for fast and accurate results
- **Document categorization and tagging** for better organization of PDF files
- **PDF annotations** for highlighting and adding notes to documents
- **Document similarity search** for finding related documents
- **Memory-aware caching** that adapts to system resources for optimal performance

## Installation

### Prerequisites

**Python Version**: This application requires Python 3.8 or higher. It has been tested and confirmed to work with Python 3.8 through 3.13.

You can check your Python version with:
```bash
python --version
```

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Ap6pack/PDF-Search-Plus.git
   cd PDF-Search-Plus
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

The application is designed to be simple to use. Just run the main script and everything will be set up automatically:

```bash
python run_pdf_search.py
```

The database will be automatically created or validated when you run the application. No separate setup steps are required.

**Note:** If you need to recreate the database from scratch (e.g., after schema changes or corruption), you can use the `db_setup.py` utility:

```bash
python db_setup.py
```

This will delete the existing database and create a fresh one with the latest schema. This is rarely needed during normal operation.

#### Command Line Options

The application supports several command-line options:

- `--verbose`, `-v`: Enable verbose logging
- `--process-file FILE`: Process a single PDF file without launching the GUI
- `--process-folder FOLDER`: Process all PDF files in a folder without launching the GUI
- `--search TERM`: Search for a term in the database without launching the GUI
- `--max-workers N`: Maximum number of worker threads for batch processing (default: 5)

##### Examples:

1. Launch the GUI with verbose logging:
   ```bash
   python run_pdf_search.py --verbose
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
    ├── security.py
    ├── tag_manager.py
    ├── annotation_manager.py
    └── similarity_search.py
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

- **annotations**: Stores PDF annotations (highlights, notes, etc.)
  - `id`: Primary key
  - `pdf_id`: Foreign key to pdf_files
  - `page_number`: Page number where annotation appears
  - `x_coord`: X coordinate of annotation position
  - `y_coord`: Y coordinate of annotation position
  - `width`: Width of annotation area
  - `height`: Height of annotation area
  - `content`: Annotation text content
  - `annotation_type`: Type of annotation (highlight, note, underline, etc.)
  - `color`: Color of annotation (hex code, default: #FFFF00)
  - `created_at`: Timestamp when annotation was created

- **tags**: Stores document tags for categorization
  - `id`: Primary key
  - `name`: Tag name
  - `color`: Tag color (hex code)
  - `created_at`: Timestamp when the tag was created

- **categories**: Stores hierarchical document categories
  - `id`: Primary key
  - `name`: Category name
  - `parent_id`: Foreign key to parent category (for hierarchical structure)
  - `created_at`: Timestamp when the category was created

- **pdf_tags**: Many-to-many relationship between PDFs and tags
  - `pdf_id`: Foreign key to pdf_files
  - `tag_id`: Foreign key to tags
  - `created_at`: Timestamp when the relationship was created

- **pdf_categories**: Many-to-many relationship between PDFs and categories
  - `pdf_id`: Foreign key to pdf_files
  - `category_id`: Foreign key to categories
  - `created_at`: Timestamp when the relationship was created

### Search Functionality

The application provides robust search capabilities:

- **Optimized Full-Text Search**: Uses FTS5 virtual tables with porter stemming for fast and accurate text matching
- **Tag-Based Search**: Find documents by assigned tags with options for ANY or ALL tag matching
- **Category-Based Organization**: Browse documents by hierarchical categories
- **Combined Search**: Search by text content and tags simultaneously

### Indexes

The database includes optimized indexes for better performance:

- Compound indexes on `pdf_id` and `page_number` for faster joins
- Specialized indexes for text columns for faster searching
- Indexes on file name and path for faster lookups
- Indexes for tag and category relationships

## Performance Optimizations

- **Memory-Aware Caching**: The application monitors system memory and adapts cache size dynamically
- **Optimized FTS5 Search**: Uses porter stemming and prefix matching for faster and more accurate searches
- **Memory Management**: Large PDFs are processed in a streaming fashion to reduce memory usage
- **Batch Processing**: Images are processed in batches to limit memory consumption
- **Time-Based Cache Expiration**: Automatically expires cached items after a specified time
- **Pagination**: Search results are paginated to handle large result sets efficiently

## Security Features

- **Enhanced Input Validation**: All user inputs are validated with comprehensive checks
- **Secure Path Validation**: File paths are validated to prevent path traversal attacks
- **Secure Temporary Files**: Temporary files are created with proper permissions and cleanup
- **Text Sanitization**: All text is sanitized to prevent XSS and other injection attacks
- **SQL Injection Protection**: Parameterized queries are used throughout the application
- **Memory Pressure Detection**: The application monitors and responds to system memory pressure

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

## Document Tagging and Categorization

The application supports document tagging and categorization:

- **Tags**: Assign colored tags to documents for quick identification and filtering
- **Categories**: Organize documents in hierarchical categories
- **Tag-Based Search**: Find documents by their assigned tags
- **Multiple Tags**: Assign multiple tags to each document
- **Tag Management**: Create, update, and delete tags
- **Category Hierarchy**: Create nested categories for better organization

## PDF Annotations

The application now supports PDF annotations:

- **Highlight Text**: Highlight important text in documents
- **Add Notes**: Add notes to specific parts of documents
- **Multiple Annotation Types**: Support for highlights, notes, underlines, and more
- **Annotation Search**: Search for text within annotations
- **Color Coding**: Assign different colors to annotations for better organization

## Document Similarity Search

Find similar documents based on content:

- **TF-IDF Vectorization**: Convert document text into numerical vectors
- **Cosine Similarity**: Measure similarity between documents
- **Document Clustering**: Group similar documents together
- **Text-Based Search**: Find documents similar to a text query
- **Threshold Control**: Adjust similarity threshold for more or fewer results

## Future Enhancements

- Add support for exporting search results
- Improve image OCR accuracy with advanced preprocessing
- Support for more languages in OCR
- Add support for PDF form field extraction
- Enhance tag visualization with tag clouds
