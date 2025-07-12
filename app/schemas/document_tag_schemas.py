from datetime import datetime
from pydantic import BaseModel
from uuid import UUID


class DocumentTag(BaseModel):
    document_id: UUID
    tag_id: UUID
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }
    