"""Text extraction from PDFs — digital (PyMuPDF) and scanned (Tesseract OCR)."""

import os
import re
from typing import Dict, Optional

import fitz  # PyMuPDF


def extract_text_from_pdf(file_path: str) -> Dict[int, str]:
    """
    Extract text from a PDF file.
    Returns a dict mapping page_number (1-based) → text.
    Falls back to OCR if digital extraction yields little text.
    """
    page_texts = _extract_digital(file_path)

    # Check if extraction yielded meaningful text
    total_text = "".join(page_texts.values())
    if len(total_text.strip()) < 100:
        # Likely a scanned PDF — try OCR
        ocr_texts = _extract_ocr(file_path)
        if ocr_texts:
            return ocr_texts

    return page_texts


def _extract_digital(file_path: str) -> Dict[int, str]:
    """Extract text using PyMuPDF (for digital/text-based PDFs)."""
    page_texts = {}
    try:
        doc = fitz.open(file_path)
        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            page_texts[page_num + 1] = text  # 1-based page numbers
        doc.close()
    except Exception as e:
        print(f"PyMuPDF extraction error: {e}")
    return page_texts


def _extract_ocr(file_path: str) -> Optional[Dict[int, str]]:
    """Extract text using Tesseract OCR (for scanned PDFs)."""
    try:
        from pdf2image import convert_from_path
        import pytesseract

        images = convert_from_path(file_path, dpi=300)
        page_texts = {}
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            page_texts[i + 1] = text
        return page_texts
    except ImportError:
        print("OCR dependencies not available (pdf2image / pytesseract)")
        return None
    except Exception as e:
        print(f"OCR extraction error: {e}")
        return None


def get_full_text(page_texts: Dict[int, str]) -> str:
    """Combine all page texts into a single string."""
    return "\n\n".join(
        f"[Page {page}]\n{text}" for page, text in sorted(page_texts.items())
    )


def get_page_count(file_path: str) -> int:
    """Get the number of pages in a PDF."""
    try:
        doc = fitz.open(file_path)
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0


def preprocess_text(text: str) -> str:
    """Clean extracted text: normalize whitespace, remove artifacts."""
    # Remove excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Normalize spaces
    text = re.sub(r"[ \t]+", " ", text)
    # Remove common header/footer patterns (page numbers)
    text = re.sub(r"\n\s*Page\s+\d+\s*(of\s+\d+)?\s*\n", "\n", text, flags=re.IGNORECASE)
    # Remove encoding artifacts
    text = text.encode("utf-8", errors="ignore").decode("utf-8")
    return text.strip()
