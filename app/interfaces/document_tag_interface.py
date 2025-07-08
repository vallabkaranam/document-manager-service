from sqlalchemy.orm import Session
from app.db.models.document_tag import DocumentTag

class DocumentTagInterface:
    def __init__(self, db: Session):
        self.db = db

    def link_document_tag(self, document_id, tag_id):
        link = DocumentTag(document_id=document_id, tag_id=tag_id)
        self.db.add(link)
        self.db.commit()
        return link 