"""PDF text extraction."""

from pathlib import Path


def load_pdf_text(path: str | Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return Path(path).read_bytes().decode("utf-8", errors="ignore")

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)

