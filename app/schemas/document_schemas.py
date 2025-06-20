from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


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
    upload_time: datetime
    description: Optional[str] = None
    user_id: int

class Tag(BaseModel):
    id: UUID
    text: str
    created_at: datetime

class UploadDocumentResponse(BaseModel):
    document: Document
    tags: List[Tag]

class DocumentsResponse(BaseModel):
    documents: List[Document]