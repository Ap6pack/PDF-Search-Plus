# Changelog

## [2.4.3] - 2025-05-16
- Fixed Tesseract OCR process failure by redesigning temporary file management
- Fixed application continuing to run after closure by implementing proper thread management
- Added daemon threads to ensure background processes terminate when the application exits
- Implemented window close handler with resource cleanup
- Enhanced error handling and cleanup in the main application loop

## [2.4.2] - 2025-05-16
- Fixed FTS5 search query to use correct column names
- Corrected snippet function parameters for better search result highlighting

## [2.4.1] - 2025-05-16
- Fixed database utility functions for better backward compatibility
- Corrected cache module imports to use proper class names
- Improved error handling in database operations
- Enhanced code maintainability with proper delegation patterns

## [2.4.0] - 2025-05-16
- Implemented PDF annotations support
- Added document similarity search using TF-IDF and cosine similarity
- Enhanced database schema with annotations table
- Added document clustering functionality

## [2.3.0] - 2025-05-16
- Implemented document categorization and tagging system
- Enhanced database schema with tags and categories tables
- Optimized FTS5 search with porter stemming and prefix matching
- Improved caching system with memory-aware LRU cache
- Added time-based cache expiration for better resource management
- Enhanced security with secure temporary file handling
- Improved input validation for all user inputs
- Added comprehensive docstrings and type hints throughout the codebase

## [2.2.1] - 2025-05-15
- Enhanced run_pdf_search.py with improved database setup, error handling, and command-line options
- Updated README with comprehensive documentation and improved installation instructions
- Added copyright headers to all source files

## [2.0.0] - 2025-05-10
- Added caching system with LRUCache and DiskCache for efficient data storage
- Implemented memory management utilities for handling large PDFs
- Enhanced security with input validation and sanitization functions
- Added pagination for search results
- Enhanced database with full-text search capabilities and improved indexing
- Improved error handling and logging throughout the application

## [1.2.0] - 2025-05-05
- Removed EasyOCR support in favor of Tesseract OCR for better compatibility
- Streamlined OCR processing with improved architecture
- Updated package versions in requirements.txt for improved compatibility and performance

## [1.1.0] - 2025-05-03
- Improved PDF processor architecture with OOP structure
- Added type hints and comprehensive documentation
- Enhanced resource management with context managers
- Optimized database operations
- Used pathlib for cross-platform path handling
- Added PDFMetadata dataclass for better data structure

## [1.0.0] - 2025-05-01
- Initial release
- Support for PDF text extraction
- Support for OCR using Tesseract and EasyOCR
- Basic search functionality
- SQLite database for storing extracted text

## [0.9.0] - 2024-10-31
- Improved PDF processor architecture and error handling
- Enhanced code structure with better organization

## [0.8.0] - 2024-10-24
- Added support for EasyOCR as an alternative to Tesseract for OCR processing
- Fixed image processing with NumPy array conversion for EasyOCR compatibility
- Updated required modules and dependencies

## [0.7.0] - 2024-10-23
- Added MIT License
- Updated README with improved documentation
- Refactored code for better maintainability

## [0.6.0] - 2024-10-16
- Various enhancements to core functionality

## [0.5.0] - 2024-10-04
- Updated code and removed unused components
- Improved code organization

## [0.4.0] - 2024-10-03
- Enhanced search functionality with more precise keyword matching using regular expressions
- Added multithreading for database search operations
- Implemented zoom control for PDF preview
- Added page navigation with Next and Previous buttons
- Improved error handling with UI feedback and logging
- Enhanced UI layout with expandable TreeView and canvas
- Integrated PDF rendering directly on the main window

## [0.3.0] - 2024-10-03
- Updated README to reflect new features and improvements

## [0.2.0] - 2024-09-30
- Added requirements.txt file
- Updated .gitignore file

## [0.1.0] - 2024-09-30
- Initial commit
- Basic PDF processing functionality
