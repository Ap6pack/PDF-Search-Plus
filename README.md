# PDFSearchPlus

**PDFSearchPlus** is a Python-based application designed to help you extract, search, and manage data from PDF files. It allows users to extract text, images, and keywords from PDFs, store the extracted information in an SQLite database, and search the content by keywords and context. Additionally, users can preview PDF pages and navigate directly to where the keywords were found.

## Features

- **Extract text, images, and keywords** from PDF files.
- **Mass scanning**: Process multiple PDF files from a folder at once.
- **Keyword and context search**: Search the extracted content by keywords and view the surrounding context.
- **PDF preview**: Open and preview the exact page in a PDF where the keyword was found.
- **Database integration**: Store extracted data in an SQLite database for quick access and searching.
- **GUI-based user interface**: Easy-to-use interface with keyword search and PDF preview capabilities.

## Table of Contents

1. [Features](#features)
2. [Installation](#installation)
3. [Usage](#usage)
   - [Setting up the database](#setting-up-the-database)
   - [Processing PDFs](#processing-pdfs)
   - [Searching PDFs](#searching-pdfs)
4. [Screenshots](#screenshots)
5. [Contributing](#contributing)
6. [License](#license)

## Installation

### Prerequisites

Ensure that you have the following installed on your system:

- Python 3.7+
- pip (Python package manager)

### Required Python Libraries

You can install the required Python libraries using the following command:

```bash
pip install -r requirements.txt
```

**`requirements.txt` should include:**
```
PyMuPDF
Pillow
tkinter
```

Alternatively, install these dependencies manually:

```bash
pip install PyMuPDF Pillow
```

### Setting up the Database

Run the following script to create the SQLite database and initialize the required tables:

```bash
python db_setup.py
```

This will create a `pdf_data.db` file and set up the following tables:
- `pdf_files`
- `pages`
- `images`
- `keywords`

## Usage

### 1. Processing PDFs

To process PDFs and extract text, images, and keywords, run the `pdf_processor.py` script:

```bash
python pdf_processor.py
```

You will be prompted to either process a single PDF or perform a mass scan on a folder containing multiple PDFs. Once processed, the extracted content will be stored in the `pdf_data.db` database and saved to organized folders.

### 2. Searching PDFs

To search the extracted data by keywords or context, run the `pdf_search_gui.py` script:

```bash
python pdf_search_gui.py
```

This will open a graphical user interface where you can:
- Search for keywords or context in the database.
- View search results, including the PDF file, page number, keyword, and context.
- Open and preview the corresponding PDF at the exact page where the keyword is found.

## Screenshots

### Main GUI for PDF Search and Preview

![PDF Search GUI](path-to-your-image)

### PDF Preview

![PDF Preview](path-to-your-image)

## Contributing

Contributions are welcome! If you'd like to contribute to **PDFSearchPlus**, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bugfix (`git checkout -b feature-name`).
3. Make your changes and commit them (`git commit -m 'Add feature'`).
4. Push your branch to GitHub (`git push origin feature-name`).
5. Open a pull request and provide a detailed description of your changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---
