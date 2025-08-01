from typing import List
from pydantic import BaseModel, Field

from app.schemas.document_embedding_schemas import DocumentEmbedding

class SimilarChunk(DocumentEmbedding):
    distance: float = Field(..., description="Similarity distance score for the chunk")
    similarity_score: float = Field(..., description="Similarity score (0-1, higher is more similar)")
    
class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language question or prompt for the RAG system")
    top_k: int = Field(5, description="Number of top relevant chunks to retrieve")
    include_tags: bool = Field(True, description="Whether to include document-level tags in prompt context")

class RAGQueryResponse(BaseModel):
    query: str = Field(..., description="Original user query for which the response was generated")
    answer: str = Field(..., description="Generated answer from the LLM based on retrieved context")
    context_chunks: List[SimilarChunk] = Field(..., description="Similar chunks used to construct the answer")

