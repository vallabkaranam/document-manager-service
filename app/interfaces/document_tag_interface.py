"""
Document-Tag Association Interface Module

Encapsulates all business logic for linking and unlinking documents and tags, abstracting the database layer
and providing clean, validated interfaces to the controller and route layers.

Key Capabilities:
- Link and unlink documents and tags
- Ensure validation and exception safety across operations

Assumptions:
- Document-tag associations are managed via a join table
- All inputs and outputs are validated Pydantic models
"""

import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.models.document import Document
from app.db.models.document_tag import DocumentTag
from app.db.models.tag import Tag
from app.schemas.document_tag_schemas import DocumentTag as DocumentTagPydantic
from app.schemas.errors import DocumentNotFoundError, TagNotFoundError, DocumentTagNotFoundError, DocumentTagLinkError

class DocumentTagInterface:
    """
    Provides an abstraction over document-tag association operations, ensuring consistent error handling
    and encapsulating all document-tag logic behind a single class.
    """
    def __init__(self, db: Session) -> None:
        """
        Initializes the document-tag interface with a database session.

        Args:
            db (Session): SQLAlchemy session object.
        """
        self.db = db

    def link_document_tag(self, document_id: str, tag_id: str) -> DocumentTagPydantic:
        """
        Links a document and a tag, creating an association if it does not already exist.

        Args:
            document_id (str): UUID string of the document.
            tag_id (str): UUID string of the tag.

        Returns:
            DocumentTagPydantic: The created or existing document-tag association.

        Raises:
            DocumentNotFoundError: If the document is not found.
            TagNotFoundError: If the tag is not found.
            DocumentTagLinkError: If linking fails.
        """
        doc_uuid = uuid.UUID(document_id)
        tag_uuid = uuid.UUID(tag_id)

        document = self.db.query(Document).filter(Document.id == doc_uuid).first()
        tag = self.db.query(Tag).filter(Tag.id == tag_uuid).first()

        if not document:
            raise DocumentNotFoundError(f"Document {document_id} not found")

        if not tag:
            raise TagNotFoundError(f"Tag {tag_id} not found")

        existing_link = self.db.query(DocumentTag).filter_by(
            document_id=doc_uuid, tag_id=tag_uuid
        ).first()

        if existing_link:
            return DocumentTagPydantic.model_validate(existing_link)

        try:
            link = DocumentTag(document_id=doc_uuid, tag_id=tag_uuid)
            self.db.add(link)
            self.db.commit()
            self.db.refresh(link)
            return DocumentTagPydantic.model_validate(link)
        except Exception as e:
            raise DocumentTagLinkError("Failed to link document and tag") from e

    def unlink_document_tag(self, document_id: str, tag_id: str) -> DocumentTagPydantic:
        """
        Unlinks (removes) the association between a document and a tag.

        Args:
            document_id (str): UUID string of the document.
            tag_id (str): UUID string of the tag.

        Returns:
            DocumentTagPydantic: The deleted document-tag association.

        Raises:
            DocumentNotFoundError: If the document is not found.
            TagNotFoundError: If the tag is not found.
            DocumentTagNotFoundError: If the association does not exist.
            DocumentTagLinkError: If unlinking fails.
        """
        doc_uuid = uuid.UUID(document_id)
        tag_uuid = uuid.UUID(tag_id)

        document = self.db.query(Document).filter(Document.id == doc_uuid).first()
        if not document:
            raise DocumentNotFoundError(f"Unable to find document with id {document_id}")

        tag = self.db.query(Tag).filter(Tag.id == tag_uuid).first()
        if not tag:
            raise TagNotFoundError(f"Unable to find tag with id {tag_id}")

        link = self.db.query(DocumentTag).filter_by(document_id=doc_uuid, tag_id=tag_uuid).first()
        if not link:
            raise DocumentTagNotFoundError(f"Unable to find association between document with id {document_id} and tag with id {tag_id}")

        try:
            # Create response before deleting
            response = DocumentTagPydantic.model_validate(link)
            self.db.delete(link)
            self.db.commit()
            return response
        except Exception as e:
            raise DocumentTagLinkError(f"Failed to unlink document and tag: {str(e)}") from e