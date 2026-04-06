from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keybert import KeyBERT
    from sentence_transformers import SentenceTransformer

DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


@lru_cache
def get_sentence_model() -> "SentenceTransformer":
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(DEFAULT_EMBEDDING_MODEL)


@lru_cache
def get_keybert_model() -> "KeyBERT":
    from keybert import KeyBERT

    return KeyBERT(model=get_sentence_model())
