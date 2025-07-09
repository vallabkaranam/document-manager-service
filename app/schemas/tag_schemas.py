from typing import List
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class Tag(BaseModel):
    id: UUID
    text: str
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }

class CreateTagRequest(BaseModel):
    text: str = Field(
        description="The text content of the tag",
        example="machine learning"
    )

class TagsResponse(BaseModel):
    tags: List[Tag] 