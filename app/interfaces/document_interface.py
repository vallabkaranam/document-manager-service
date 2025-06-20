from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models.document import Document
from app.db.models.document_tag import DocumentTag
from app.schemas.document_schemas import Document as DocumentPydantic, Tag as TagPydantic
from app.db.models.tag import Tag

class DocumentInterface:
    def __init__(self, db: Session):
        self.db = db

    def create_document(self, filename: str, s3_url: str, content_type: Optional[str] = None, description: Optional[str] = None) -> DocumentPydantic:
        """
        Creates a new document record in the database.
        """
        document = Document(
            filename=filename,
            storage_path=s3_url,
            content_type=content_type or 'unknown',
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
            upload_time=document.upload_time,
            description=document.description,
            user_id=document.user_id
            )
    
    def get_documents_by_user_id(self, user_id: int) -> List[DocumentPydantic]:
        documents_from_db = self.db.query(Document).filter(Document.user_id == user_id).all()
        return [
            DocumentPydantic(
                id=document.id,
                filename=document.filename,
                storage_path=document.storage_path,
                content_type=document.content_type,
                upload_time=document.upload_time,
                description=document.description,
                user_id=document.user_id
                )
            for document in documents_from_db
        ]

    def get_all_tags(self) -> List[TagPydantic]:
        tags = self.db.query(Tag).all()
        return [ TagPydantic(id=tag.id, text=tag.text, created_at=tag.created_at) for tag in tags ]

    def create_tag(self, tag_text: str) -> TagPydantic:
        tag = Tag(text=tag_text)
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)

        return TagPydantic(id=tag.id, text=tag.text, created_at=tag.created_at)

    def link_document_tag(self, document_id, tag_id):
        link = DocumentTag(document_id=document_id, tag_id=tag_id)
        self.db.add(link)
        self.db.commit()