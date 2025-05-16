# Changelog

All notable changes to the PDF-Search-Plus project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.1] - 2025-05-16

### Fixed
- Fixed database error "1st ORDER BY term does not match any column in the result set" in search functionality
- Fixed "no such column: T.content" error in FTS queries
- Improved database query structure for more reliable searching
- Enhanced database initialization to automatically validate and recreate if necessary
- Updated `run_pdf_search.py` to handle database setup automatically

### Changed
- Simplified search queries to use LIKE operator with wildcards instead of FTS MATCH
- Improved error handling in database operations
- Enhanced command-line interface with better debugging information

## [2.2.0] - 2025-05-15

### Changed
- Removed EasyOCR support, now using only Pytesseract for OCR on both Windows and Linux
- Simplified OCR engine selection by standardizing on Tesseract

## [2.1.0] - 2025-05-15

### Changed
- Major code refactoring to eliminate duplication
- Consolidated PDF processing logic into a single implementation
- Unified GUI implementation
- Simplified entry points with a single runner script
- Removed work-in-progress files

### Added
- Comprehensive refactoring plan (REFACTORING.md)
- Improved documentation for the unified codebase

## [2.0.0] - 2025-05-15

### Added
- Security module with input validation and sanitization
- Caching system for PDF pages, search results, and images
- Memory management utilities for handling large PDFs
- Full-text search using SQLite FTS5
- Pagination for search results
- Database indexes for improved performance
- Batch processing with memory limits
- Streaming PDF processing for large files

### Changed
- Enhanced database schema with timestamps and FTS support
- Improved search functionality with caching and pagination
- Updated GUI with better responsiveness
- Optimized PDF rendering with caching

### Security
- Added input validation for all user inputs
- Implemented path validation to prevent path traversal attacks
- Added text sanitization to prevent XSS attacks
- Enhanced SQL injection protection with parameterized queries

## [1.2.0] - 2024-11-10

### Added
- Support for EasyOCR as an alternative OCR engine
- Command-line arguments for selecting OCR engine
- Multi-threading support for batch processing
- Improved error handling and logging

### Changed
- Refactored OCR module to support multiple OCR engines
- Enhanced PDF processing with better error recovery
- Improved GUI responsiveness during processing

## [1.1.0] - 2024-07-22

### Added
- GUI improvements with zoom and navigation features
- Preview functionality for PDF pages
- Support for batch processing of PDF folders
- Enhanced search capabilities

### Changed
- Improved database schema with foreign key constraints
- Better error handling and user feedback
- Optimized image extraction process

## [1.0.0] - 2024-03-15

### Added
- Initial release with basic functionality
- PDF text extraction and storage
- Image extraction from PDFs
- OCR processing using Tesseract
- SQLite database for storing extracted text and metadata
- Basic search functionality
- Simple GUI for searching and viewing results

### Technical Details
- Core PDF processing module
- Database utilities for SQLite interaction
- OCR integration with Tesseract
- Basic GUI using Tkinter
