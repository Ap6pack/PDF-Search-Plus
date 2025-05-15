#!/usr/bin/env python3
"""
Setup script for the PDF Search Plus package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pdf-search-plus",
    version="0.1.0",
    author="Adam Rhys Heaton",
    author_email="adamslinuxemail@gmail.com",
    description="PDF text extraction and search with OCR capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Ap6pack/pdf-search-plus",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "PyMuPDF>=1.18.0",
        "Pillow>=8.0.0",
        "pytesseract>=0.3.8",
        "easyocr>=1.4.1",
        "numpy>=1.20.0",
        "threaded>=4.1.0",
        "psutil>=5.8.0",
        "cachetools>=4.2.0",
        "tqdm>=4.60.0",
    ],
    entry_points={
        "console_scripts": [
            "pdf-search-plus=pdf_search_plus.main:main",
        ],
    },
)
