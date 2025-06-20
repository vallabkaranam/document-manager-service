from typing import List
from sqlalchemy.orm import Session
from app.db.models.document import Document
from app.db.models.document_tag import DocumentTag
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