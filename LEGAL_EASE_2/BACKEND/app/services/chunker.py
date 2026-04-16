"""Text chunking for legal documents with overlap and metadata."""

import re
from typing import Dict, List

import tiktoken


# Heading patterns to detect clause/section boundaries
HEADING_PATTERNS = [
    re.compile(r"^(ARTICLE|SECTION|CLAUSE)\s+\d+", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\d+\.\s+[A-Z][A-Za-z\s]+", re.MULTILINE),
    re.compile(r"^[IVXLC]+\.\s+[A-Z]", re.MULTILINE),
    re.compile(r"^[A-Z][A-Z\s]{5,}$", re.MULTILINE),
]

CHUNK_SIZE = 450  # tokens – fits within mxbai-embed-large 512-token context
CHUNK_OVERLAP = 50  # tokens


def detect_headings(text: str) -> List[dict]:
    """Detect section headings and their positions in the text."""
    headings = []
    for pattern in HEADING_PATTERNS:
        for match in pattern.finditer(text):
            headings.append({
                "text": match.group().strip(),
                "start": match.start(),
            })
    # Sort by position and deduplicate nearby headings
    headings.sort(key=lambda h: h["start"])
    return headings


def _get_heading_for_position(headings: List[dict], pos: int) -> str:
    """Find the most recent heading before a given text position."""
    current_heading = "General"
    for h in headings:
        if h["start"] <= pos:
            current_heading = h["text"][:80]
        else:
            break
    return current_heading


def chunk_text(
    text: str,
    page_texts: Dict[int, str],
    doc_id: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[dict]:
    """
    Split document text into overlapping chunks with metadata.
    
    Returns list of:
    {
        doc_id: str,
        chunk_id: str,
        text: str,
        page_number: int,
        clause_heading: str,
        token_count: int,
    }
    """
    encoder = tiktoken.get_encoding("cl100k_base")
    tokens = encoder.encode(text)
    headings = detect_headings(text)

    # Build a character-position → page-number mapping
    page_map = _build_page_map(page_texts)

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text_str = encoder.decode(chunk_tokens)

        # Determine approximate character position for metadata
        char_pos = len(encoder.decode(tokens[:start]))
        page_number = _get_page_for_position(page_map, char_pos)
        clause_heading = _get_heading_for_position(headings, char_pos)

        chunks.append({
            "doc_id": doc_id,
            "chunk_id": f"{doc_id}_chunk_{chunk_index}",
            "text": chunk_text_str,
            "page_number": page_number,
            "clause_heading": clause_heading,
            "token_count": len(chunk_tokens),
        })

        chunk_index += 1
        start += chunk_size - overlap  # Move forward with overlap

    return chunks


def _build_page_map(page_texts: Dict[int, str]) -> List[dict]:
    """Build a list of {page, start_char, end_char} for character position → page mapping."""
    page_map = []
    current_pos = 0
    for page_num in sorted(page_texts.keys()):
        text = page_texts[page_num]
        page_header = f"[Page {page_num}]\n"
        start = current_pos + len(page_header)
        end = start + len(text)
        page_map.append({"page": page_num, "start": current_pos, "end": end})
        current_pos = end + 2  # +2 for the \n\n separator
    return page_map


def _get_page_for_position(page_map: List[dict], char_pos: int) -> int:
    """Find which page a character position belongs to."""
    for entry in reversed(page_map):
        if char_pos >= entry["start"]:
            return entry["page"]
    return 1
