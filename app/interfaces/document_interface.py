from typing import List
from sqlalchemy.orm import Session
from app.db.models.document import Document
from app.db.models.document_tag import DocumentTag
from app.schemas.document_schemas import Document as DocumentPydantic
from app.db.models.tag import Tag

class DocumentInterface:
    def __init__(self, db: Session):
        self.db = db

    def create_document(self, filename: str, s3_url: str, description: str = None) -> Document:
        """
        Creates a new document record in the database.
        """
        document = Document(
            filename=filename,
            storage_path=s3_url,
            description=description,
            user_id=1
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document 
    
    def get_documents_by_user_id(self, user_id: int) -> List[DocumentPydantic]:
        documents_from_db = self.db.query(Document).filter(Document.user_id == user_id).all()
        return [
            DocumentPydantic(
                id=document.id,
                filename=document.filename,
                storage_path=document.storage_path,
                upload_time=document.upload_time,
                description=document.description,
                user_id=document.user_id
                )
            for document in documents_from_db
        ]

    def get_all_tags(self) -> List[Tag]:
        return self.db.query(Tag).all()

    def create_tag(self, tag_text: str) -> Tag:
        tag = Tag(text=tag_text)
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def link_document_tag(self, document_id, tag_id):
        link = DocumentTag(document_id=document_id, tag_id=tag_id)
        self.db.add(link)
        self.db.commit()