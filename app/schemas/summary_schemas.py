from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class Summary(BaseModel):
    id: UUID
    content: str
    created_at: datetime
    document_id: UUID