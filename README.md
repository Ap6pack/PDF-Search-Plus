# PDF Search Plus

A powerful tool for extracting and searching text from PDF files, with OCR capabilities using Tesseract.

## Features

- Extract text from PDF files
- OCR support for scanned documents using Tesseract OCR
- Full-text search capabilities
- GUI interface for easy searching
- SQLite database for storing extracted text

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pdf-search-plus.git
cd pdf-search-plus

# Install dependencies
pip install -r requirements.txt

# Install Tesseract OCR engine (required)
# For Ubuntu/Debian:
sudo apt-get install tesseract-ocr
# For macOS:
brew install tesseract
# For Windows:
# Download and install from https://github.com/UB-Mannheim/tesseract/wiki
```

## Usage

```bash
# Process a PDF file and add it to the database
python run_pdf_search.py --add /path/to/your/file.pdf

# Search for text in processed PDFs
python run_pdf_search.py --search "your search query"

# Launch the GUI
python run_pdf_search.py --gui
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
