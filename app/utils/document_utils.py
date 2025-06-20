from app.ml_models.embedding_models import shared_keybert_model
from typing import List
from PyPDF2 import PdfReader
import io

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