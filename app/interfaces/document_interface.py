from sqlalchemy.orm import Session
from app.db.models.document import Document

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