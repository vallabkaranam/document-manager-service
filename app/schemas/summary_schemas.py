from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class Summary(BaseModel):
    id: UUID = Field(..., description="Unique identifier for the summary")
    content: str = Field(..., description="The text content of the summary")
    created_at: datetime = Field(..., description="Timestamp when the summary was created")
    document_id: UUID = Field(..., description="ID of the document this summary belongs to")

    model_config = {
        "from_attributes": True
    }