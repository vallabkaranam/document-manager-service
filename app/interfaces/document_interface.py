from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from app.db.models.document import Document
from app.schemas.document_schemas import Document as DocumentPydantic
from datetime import datetime, timezone

class DocumentInterface:
    def __init__(self, db: Session):
        self.db = db

    def create_document(self, 
                        s3_url: str, 
                        filename: Optional[str] = 'Untitled',
                        content_type: Optional[str] = 'unknown', 
                        size: Optional[int] = 0,
                        description: Optional[str] = None
                        ) -> DocumentPydantic:
        """
        Creates a new document record in the database.
        """
        document = Document(
            filename=filename,
            storage_path=s3_url,
            content_type=content_type,
            size=size,
            description=description,
            user_id=1 # TODO: Hardcoding the user_id here until we hook up to user-service
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        return DocumentPydantic(
            id=document.id,
            filename=document.filename,
            storage_path=document.storage_path,
            content_type=document.content_type,
            size=document.size,
            upload_time=document.upload_time,
            updated_at=document.updated_at,
            description=document.description,
            user_id=document.user_id,
            tag_status=document.tag_status,
            tag_status_updated_at=document.tag_status_updated_at
            )
    
    def get_documents_by_user_id(self, user_id: int) -> List[DocumentPydantic]:
        documents_from_db = self.db.query(Document).filter(Document.user_id == user_id).all()
        return [
            DocumentPydantic(
                id=document.id,
                filename=document.filename,
                storage_path=document.storage_path,
                content_type=document.content_type,
                size=document.size,
                upload_time=document.upload_time,
                updated_at=document.updated_at,
                description=document.description,
                user_id=document.user_id,
                tag_status=document.tag_status,
                tag_status_updated_at=document.tag_status_updated_at
            )
            for document in documents_from_db
        ]
    
    def get_document_by_id(self, document_id: str) -> DocumentPydantic:
        doc_uuid = uuid.UUID(document_id)
        document_from_db = self.db.query(Document).filter(Document.id == doc_uuid).first()
        if not document_from_db:
            raise Exception(f"Document with id {document_id} not found")
        
        return DocumentPydantic(
            id=document_from_db.id,
            filename=document_from_db.filename,
            storage_path=document_from_db.storage_path,
            content_type=document_from_db.content_type,
            size=document_from_db.size,
            upload_time=document_from_db.upload_time,
            updated_at=document_from_db.updated_at,
            description=document_from_db.description,
            user_id=document_from_db.user_id,
            tag_status=document_from_db.tag_status,
            tag_status_updated_at=document_from_db.tag_status_updated_at
        )

    def update_document(self, document_id: str, update_data):
        doc_uuid = uuid.UUID(document_id)
        document = self.db.query(Document).filter(Document.id == doc_uuid).first()
        if not document:
            raise Exception(f"Document with id {document_id} not found")
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(document, field, value)
        document.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(document)
        return DocumentPydantic(
            id=document.id,
            filename=document.filename,
            storage_path=document.storage_path,
            content_type=document.content_type,
            size=document.size,
            upload_time=document.upload_time,
            updated_at=document.updated_at,
            description=document.description,
            user_id=document.user_id,
            tag_status=document.tag_status,
            tag_status_updated_at=document.tag_status_updated_at
        )

    def delete_document(self, document_id: str) -> DocumentPydantic:
        doc_uuid = uuid.UUID(document_id)
        document = self.db.query(Document).filter(Document.id == doc_uuid).first()
        if not document:
            raise Exception(f"Document with id {document_id} not found")
        
        # Create response before deleting
        response = DocumentPydantic(
            id=document.id,
            filename=document.filename,
            storage_path=document.storage_path,
            content_type=document.content_type,
            size=document.size,
            upload_time=document.upload_time,
            updated_at=document.updated_at,
            description=document.description,
            user_id=document.user_id,
            tag_status=document.tag_status,
            tag_status_updated_at=document.tag_status_updated_at
        )
        
        self.db.delete(document)
        self.db.commit()
        return response