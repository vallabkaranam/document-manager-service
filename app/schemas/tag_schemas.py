from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class Tag(BaseModel):
    id: UUID = Field(..., description="Unique identifier for the tag")
    text: str = Field(..., description="The text content of the tag")
    created_at: datetime = Field(..., description="Timestamp when the tag was created")
    updated_at: datetime = Field(..., description="Timestamp when the tag was last updated")
    
    model_config = {
        "from_attributes": True
    }

class SimilarTag(Tag):
    distance: float = Field(..., description="Similarity distance score for the tag")
    similarity_score: float = Field(..., description="Similarity score (0-1, higher is more similar)")

class TagUpdate(BaseModel):
    id: Optional[UUID] = Field(None, description="Unique identifier for the tag")
    text: Optional[str] = Field(None, description="The text content of the tag")
    created_at: Optional[datetime] = Field(None, description="Timestamp when the tag was created")
    updated_at: Optional[datetime] = Field(None, description="Timestamp when the tag was last updated")

class CreateTagRequest(BaseModel):
    text: str = Field(
        description="The text content of the tag",
        example="machine learning"
    )

class TagsResponse(BaseModel):
    tags: List[Tag] = Field(..., description="List of tags") 