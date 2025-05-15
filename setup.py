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
    author_email="adam@example.com",
    description="PDF text extraction and search with OCR capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/username/pdf-search-plus",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "PyMuPDF",
        "Pillow",
        "pytesseract",
        "easyocr",
        "numpy",
        "threaded",
    ],
    entry_points={
        "console_scripts": [
            "pdf-search-plus=pdf_search_plus.main:main",
        ],
    },
)
