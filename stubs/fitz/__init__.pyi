"""
Type stubs for PyMuPDF (fitz) module.
"""
from typing import Any, Dict, Iterator, List, Tuple, Optional

class Matrix:
    """Transformation matrix for PDF operations."""
    def __init__(self, a: float = 1.0, b: float = 0.0, c: float = 0.0, d: float = 1.0, e: float = 0.0, f: float = 0.0) -> None: ...
    def prerotate(self, angle: float) -> Matrix: ...

class Pixmap:
    """Represents a pixel map (raster image)."""
    width: int
    height: int
    samples: bytes
    def save(self, filename: str, output: Optional[str] = None) -> None: ...

class Page:
    """Represents a page in a PDF document."""
    parent: Document  # Reference to parent document
    number: int  # Page number

    def get_pixmap(
        self,
        matrix: Optional[Matrix] = None,
        dpi: Optional[int] = None,
        colorspace: Any = None,
        clip: Any = None,
        alpha: bool = False,
        annots: bool = True
    ) -> Pixmap: ...
    def get_text(self, option: str = "text") -> str: ...
    def get_images(self, full: bool = False) -> List[Tuple[Any, ...]]: ...

class Document:
    """Represents a PDF document."""
    metadata: Dict[str, Any]  # PDF metadata dictionary

    def __init__(self, filename: Optional[str] = None, stream: Optional[bytes] = None) -> None: ...
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[Page]: ...
    def __enter__(self) -> Document: ...
    def __exit__(self, *args: Any) -> None: ...
    def load_page(self, page_num: int) -> Page: ...
    def page_count(self) -> int: ...
    def close(self) -> None: ...
    def extract_image(self, xref: int) -> Dict[str, Any]: ...

def open(
    filename: Optional[str] = None,
    stream: Optional[bytes] = None,
    filetype: Optional[str] = None,
    rect: Any = None,
    width: int = 0,
    height: int = 0,
    fontsize: float = 11
) -> Document: ...
