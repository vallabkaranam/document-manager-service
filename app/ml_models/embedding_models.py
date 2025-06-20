from sentence_transformers import SentenceTransformer
from keybert import KeyBERT

shared_sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
shared_keybert_model = KeyBERT(model=shared_sentence_model)