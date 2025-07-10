import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.models.document import Document
from app.db.models.document_tag import DocumentTag
from app.db.models.tag import Tag

class DocumentTagInterface:
    def __init__(self, db: Session):
        self.db = db

    def link_document_tag(self, document_id: str, tag_id: str):
        doc_uuid = uuid.UUID(document_id)
        tag_uuid = uuid.UUID(tag_id)

        document = self.db.query(Document).filter(Document.id == doc_uuid).first()
        tag = self.db.query(Tag).filter(Tag.id == tag_uuid).first()

        if not document:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

        if not tag:
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")

        existing_link = self.db.query(DocumentTag).filter_by(
            document_id=doc_uuid, tag_id=tag_uuid
        ).first()

        if existing_link:
            return existing_link

        link = DocumentTag(document_id=doc_uuid, tag_id=tag_uuid)
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link 