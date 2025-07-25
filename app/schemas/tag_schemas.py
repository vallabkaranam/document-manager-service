from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class Tag(BaseModel):
    id: UUID
    text: str
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True
    }

class SimilarTag(Tag):
    distance: float

class TagUpdate(BaseModel):
    id: Optional[UUID] = None
    text: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CreateTagRequest(BaseModel):
    text: str = Field(
        description="The text content of the tag",
        example="machine learning"
    )

class TagsResponse(BaseModel):
    tags: List[Tag] 