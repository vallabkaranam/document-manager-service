from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

from app.db.models.document import TagStatusEnum, EmbeddingStatusEnum
from app.schemas.tag_schemas import SimilarTag

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
    id: UUID = Field(..., description="Unique identifier for the document")
    filename: str = Field(..., description="The name of the file")
    storage_path: str = Field(..., description="The storage path where the file is located")
    content_type: str = Field(..., description="The MIME type of the file")
    size: int = Field(..., description="The size of the file in bytes")
    upload_time: datetime = Field(..., description="Timestamp when the document was uploaded")
    updated_at: datetime = Field(..., description="Timestamp when the document was last updated")
    description: Optional[str] = Field(None, description="Optional description of the document")
    user_id: int = Field(..., description="ID of the user who uploaded the document")
    tag_status: TagStatusEnum = Field(..., description="Current status of document tagging")
    tag_status_updated_at: datetime = Field(..., description="Timestamp when the tag status was last updated")
    embedding_status: EmbeddingStatusEnum = Field(..., description="Current status of document embedding")
    embedding_status_updated_at: datetime = Field(..., description="Timestamp when the embedding status was last updated")
    
    model_config = {
        "from_attributes": True
    }

class DocumentsResponse(BaseModel):
    documents: List[Document] = Field(..., description="List of documents")

class DocumentsSearchRequest(BaseModel):
    query: str = Field(..., description="Search query string")

class DocumentsSearchResponse(BaseModel):
    documents: List[Document] = Field(..., description="List of documents matching the search")
    tags: List[SimilarTag] = Field(..., description="List of similar tags found during search")

class DocumentUpdate(BaseModel):
    filename: Optional[str] = Field(None, description="The name of the file")
    storage_path: Optional[str] = Field(None, description="The storage path where the file is located")
    content_type: Optional[str] = Field(None, description="The MIME type of the file")
    size: Optional[int] = Field(None, description="The size of the file in bytes")
    description: Optional[str] = Field(None, description="Optional description of the document")
    user_id: Optional[int] = Field(None, description="ID of the user who uploaded the document")
    tag_status: Optional[TagStatusEnum] = Field(None, description="Current status of document tagging")
    tag_status_updated_at: Optional[datetime] = Field(None, description="Timestamp when the tag status was last updated")
    embedding_status: Optional[EmbeddingStatusEnum] = Field(None, description="Current status of document embedding")
    embedding_status_updated_at: Optional[datetime] = Field(None, description="Timestamp when the embedding status was last updated")
    updated_at: Optional[datetime] = Field(None, description="Timestamp when the document was last updated")

class PresignedURLResponse(BaseModel):
    url: str