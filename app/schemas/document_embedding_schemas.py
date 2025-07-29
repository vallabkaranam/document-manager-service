"""
Document Embedding Pydantic Schemas

This module contains Pydantic models for document embedding data validation
and serialization.
"""

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentEmbedding(BaseModel):
    """
    Pydantic model for document embedding data.
    
    This model represents a document embedding with its metadata,
    used for API responses and data validation.
    """
    
    id: UUID = Field(..., description="Unique identifier for the embedding")
    document_id: UUID = Field(..., description="ID of the document this embedding belongs to")
    embedding: List[float] = Field(..., description="Vector representation of the document content")
    created_at: datetime = Field(..., description="Timestamp when the embedding was created")
    
    model_config = {
        "from_attributes": True
    }