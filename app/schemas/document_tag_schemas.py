from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class DocumentTag(BaseModel):
    document_id: UUID = Field(..., description="ID of the document")
    tag_id: UUID = Field(..., description="ID of the tag")
    created_at: datetime = Field(..., description="Timestamp when the document-tag relationship was created")
    
    model_config = {
        "from_attributes": True
    }
    