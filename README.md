# PDF Search Plus

<div align="center">

![PDF Search Plus Logo](https://img.shields.io/badge/PDF-Search%20Plus-blue)
![Version](https://img.shields.io/badge/version-2.0.0-green)
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
