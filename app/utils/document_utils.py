"""
Document Utility Functions

This module provides utility functions to support document-related operations
such as PDF text extraction, tag generation using KeyBERT, filename sanitization,
unique filename generation, and embedding generation using SentenceTransformer.

These helpers are used by the Document Controller to process uploaded files,
generate metadata, and prepare content for ML pipelines and semantic search.

Key Capabilities:
- Extract clean text from uploaded PDF files
- Normalize and clean text for better embedding quality
- Add lightweight XML-style section tags to enhance structure
- Generate tags using KeyBERT with maxsum similarity
- Sanitize and generate unique filenames to prevent S3 overwrites
- Generate vector embeddings using SentenceTransformer

Assumptions:
- PDF files are readable using PyPDF2
- Tag generation uses English stopwords
- Embeddings are returned as float32 lists compatible with vector DBs
"""

import io
import re
import uuid
from datetime import datetime
from typing import List

from PyPDF2 import PdfReader
from app.ml_models.embedding_models import shared_keybert_model, shared_sentence_model


def extract_tags(text: str, num_tags: int = 5) -> List[str]:
    """
    Extracts top N tags from input text using KeyBERT.

    Args:
        text (str): The text to extract tags from.
        num_tags (int): Number of tags to extract. Defaults to 5.

    Returns:
        List[str]: A list of extracted keywords or phrases.
    """
    if not text or text.strip() == "":
        return []

    #   These params make the extracted tags more relevant, diverse, and descriptive.
    # - stop_words='english': Removes common words (like 'the', 'is', 'and') so only meaningful words/phrases are considered.
    # - use_maxsum=True: Ensures the selected keywords are not only relevant but also as different from each other as possible (avoids repetitive keywords).
    # - keyphrase_ngram_range=(1, 2): Allows extraction of both single words and short phrases (e.g., 'apple', 'apple pie').
    keywords = shared_keybert_model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 2),
        stop_words='english',
        use_maxsum=True,
        top_n=num_tags
    )

    return [kw[0] for kw in keywords]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts text from a PDF file given as raw bytes.

    Args:
        file_bytes (bytes): Byte content of the PDF.

    Returns:
        str: Extracted text content from all pages.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception:
        return ""


def clean_and_normalize_text(text: str) -> str:
    """
    Cleans and normalizes text for embedding.

    - Removes non-printable characters
    - Normalizes whitespace and line breaks
    - Replaces special bullet symbols with a standard dash

    Args:
        text (str): Raw extracted text.

    Returns:
        str: Cleaned and normalized text ready for embedding.
    """
    text = re.sub(r"[^\x20-\x7E\n\t]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[•·▪→]", "-", text)
    return text


def tag_sections(text: str) -> str:
    """
    Tags likely section headers and wraps content in <section> blocks.

    - Lines in ALL CAPS or Title Case treated as headers
    - Sections are wrapped in:
        <section>
          <header>...</header>
          <body>...</body>
        </section>

    Args:
        text (str): Cleaned or raw text.

    Returns:
        str: Text with lightweight structural tagging applied.
    """
    lines = text.split('\n')
    sections = []
    current_section = {"header": None, "body": []}

    for line in lines:
        stripped = line.strip()
        if re.match(r"^[A-Z\s:]{5,}$", stripped):  # ALL CAPS headings
            if current_section["header"] or current_section["body"]:
                sections.append(current_section)
                current_section = {"header": None, "body": []}
            current_section["header"] = stripped
        else:
            current_section["body"].append(stripped)

    if current_section["header"] or current_section["body"]:
        sections.append(current_section)

    tagged_text = ""
    for sec in sections:
        tagged_text += "<section>\n"
        if sec["header"]:
            tagged_text += f"  <header>{sec['header']}</header>\n"
        tagged_text += f"  <body>{' '.join(sec['body'])}</body>\n"
        tagged_text += "</section>\n"

    return tagged_text.strip()


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename by replacing special characters with underscores.

    Args:
        filename (str): Original filename.

    Returns:
        str: Cleaned filename safe for storage and URLs.
    """
    if not filename:
        return ""

    # Keep only alphanumeric characters, dots, hyphens, and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    sanitized = re.sub(r'_+', '_', sanitized)  # Collapse multiple underscores
    sanitized = sanitized.strip('_')           # Trim leading/trailing underscores

    return sanitized


def generate_unique_filename(filename: str) -> str:
    """
    Generates a unique filename by appending a timestamp and UUID segment.

    Args:
        filename (str): Original filename.

    Returns:
        str: A uniquely identifiable filename for storage (e.g., S3).
    """
    sanitized_name = sanitize_filename(filename)
    
    # If no filename available, use a default
    if not sanitized_name:
        sanitized_name = "uploaded_file"
    
    # Get file extension
    name_parts = sanitized_name.rsplit('.', 1)
    base_name = name_parts[0]
    extension = f".{name_parts[1]}" if len(name_parts) > 1 else ""
    
    # Generate unique identifier with timestamp and UUID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]  # Use first 8 characters of UUID
    
    # Create unique filename: base_name_timestamp_uniqueid.extension
    unique_filename = f"{base_name}_{timestamp}_{unique_id}{extension}"
    
    return unique_filename

def embed_text(text: str) -> List[float]:
    """
    Generates vector embeddings for the given text using SentenceTransformer.

    Args:
        text (str): Input string to encode.

    Returns:
        List[float]: Embedding vector as a list of floats.
    """
    return shared_sentence_model.encode(text).tolist()