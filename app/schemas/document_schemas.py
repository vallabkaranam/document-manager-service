from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

from app.db.models.document import TagStatusEnum

class UploadDocumentRequest(BaseModel):
    filename: Optional[str] = Field(
                          default=None,
                          description="The name of the file",
                          example="filename.pdf")
    description: Optional[str] = Field(
                             default=None,
                             description="The description of the file",
                             example="Description of the filename")
    
class Document(BaseModel):
    id: UUID
    filename: str
    storage_path: str
    content_type: str
    size: int
    upload_time: datetime
    updated_at: datetime
    description: Optional[str] = None
    user_id: int
    tag_status: TagStatusEnum
    tag_status_updated_at: datetime
class Tag(BaseModel):
    id: UUID
    text: str
    created_at: datetime

class UploadDocumentResponse(BaseModel):
    document: Document
    tags: List[Tag]

class DocumentsResponse(BaseModel):
    documents: List[Document]

class DocumentUpdate(BaseModel):
    filename: Optional[str] = None
    storage_path: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None
    description: Optional[str] = None
    user_id: Optional[int] = None
    tag_status: Optional[TagStatusEnum] = None
    tag_status_updated_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None