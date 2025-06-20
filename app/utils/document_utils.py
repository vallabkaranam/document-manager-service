from app.ml_models.embedding_models import shared_keybert_model
from typing import List
from PyPDF2 import PdfReader
import io
import re
import uuid
from datetime import datetime

def extract_tags(text: str, num_tags: int = 5) -> List[str]:
    if not text or text.strip() == "":
        return []

    keywords = shared_keybert_model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 2),
        stop_words='english',
        use_maxsum=True,
        top_n=num_tags
    )
    return [kw[0] for kw in keywords]

def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception:
        return ""

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing special characters and replacing with underscores.
    """
    if not filename:
        return ""
    
    # Remove or replace special characters
    # Keep alphanumeric, dots, hyphens, and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Remove multiple consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    return sanitized

def generate_unique_filename(filename: str) -> str:
    """
    Generate a unique filename with timestamp and UUID to prevent overwrites.
    """
    # Sanitize the filename
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