"""
Document Interface Module

Encapsulates all business logic for document-related operations, abstracting the database layer
and providing clean, validated interfaces to the controller and route layers.

Key Capabilities:
- Create, retrieve, update, and delete documents
- Fetch documents by user or tag
- Ensure validation and exception safety across operations

Assumptions:
- Documents are stored in S3 and referenced by storage_path
- All inputs and outputs are validated Pydantic models
"""

from fastapi import HTTPException
from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from app.db.models.document import Document
from app.db.models.tag import Tag
from app.schemas.document_schemas import Document as DocumentPydantic, DocumentUpdate, DocumentsResponse
from datetime import datetime, timezone
from app.schemas.errors import DocumentCreationError, DocumentDeletionError, DocumentNotFoundError, DocumentUpdateError, TagNotFoundError

class DocumentInterface:
    """
    Provides an abstraction over document operations, ensuring consistent error handling
    and encapsulating all document-related logic behind a single class.
    """
    def __init__(self, db: Session) -> None:
        """
        Initializes the document interface with a database session.

        Args:
            db (Session): SQLAlchemy session object.
        """
        self.db = db

    def create_document(
        self,
        s3_url: str,
        filename: Optional[str] = 'Untitled',
        content_type: Optional[str] = 'unknown',
        size: Optional[int] = 0,
        description: Optional[str] = None
    ) -> DocumentPydantic:
        """
        Creates a new document record in the database.

        Args:
            s3_url (str): S3 storage path of the document.
            filename (Optional[str]): Name of the document file.
            content_type (Optional[str]): MIME type of the document.
            size (Optional[int]): Size of the document in bytes.
            description (Optional[str]): Optional description of the document.

        Returns:
            DocumentPydantic: The created document.

        Raises:
            DocumentCreationError: If the document creation fails.
        """
        document = Document(
            filename=filename,
            storage_path=s3_url,
            content_type=content_type,
            size=size,
            description=description,
            user_id=1  # TODO: Hardcoding the user_id here until we hook up to user-service
        )
        try:
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
        except Exception as e:
            raise DocumentCreationError(f"Failed to create document: {str(e)}") from e

    def get_documents_by_user_id(self, user_id: int) -> List[DocumentPydantic]:
        """
        Fetches all documents belonging to a specific user.

        Args:
            user_id (int): The user's ID.

        Returns:
            List[DocumentPydantic]: List of documents for the user.
        """
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
        """
        Retrieves a document by its ID.

        Args:
            document_id (str): UUID string of the document.

        Returns:
            DocumentPydantic: The document object.

        Raises:
            DocumentNotFoundError: If the document is not found.
        """
        doc_uuid = uuid.UUID(document_id)
        document_from_db = self.db.query(Document).filter(Document.id == doc_uuid).first()
        if not document_from_db:
            raise DocumentNotFoundError(f"Document with id {document_id} not found")
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

    def get_documents_by_tag_id(self, tag_id: str) -> DocumentsResponse:
        """
        Returns all documents associated with a tag.

        Args:
            tag_id (str): UUID string of the tag.

        Returns:
            DocumentsResponse: List of documents linked to the tag.

        Raises:
            TagNotFoundError: If the tag is not found.
        """
        tag_uuid = uuid.UUID(tag_id)
        tag = self.db.query(Tag).filter(Tag.id == tag_uuid).first()
        if not tag:
            raise TagNotFoundError(f"Tag with id {tag_id} not found")
        documents = [DocumentPydantic.model_validate(document) for document in tag.documents]
        return documents

    def update_document(self, document_id: str, update_data: DocumentUpdate) -> DocumentPydantic:
        """
        Updates fields of an existing document.

        Args:
            document_id (str): UUID string of the document.
            update_data (DocumentUpdate): Fields to update.

        Returns:
            DocumentPydantic: The updated document.

        Raises:
            DocumentNotFoundError: If the document is not found.
            DocumentUpdateError: If update fails.
        """
        doc_uuid = uuid.UUID(document_id)
        document = self.db.query(Document).filter(Document.id == doc_uuid).first()
        if not document:
            raise DocumentNotFoundError(f"Document with id {document_id} not found")
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(document, field, value)
        document.updated_at = datetime.now(timezone.utc)
        try:
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
        except Exception as e:
            raise DocumentUpdateError(f"Failed to update document with id {document_id}: {str(e)}") from e

    def delete_document(self, document_id: str) -> DocumentPydantic:
        """
        Deletes a document by its ID.

        Args:
            document_id (str): UUID string of the document.

        Returns:
            DocumentPydantic: The deleted document.

        Raises:
            DocumentNotFoundError: If the document does not exist.
            DocumentDeletionError: If deletion fails.
        """
        doc_uuid = uuid.UUID(document_id)
        document = self.db.query(Document).filter(Document.id == doc_uuid).first()
        if not document:
            raise DocumentNotFoundError(f"Document with id {document_id} not found")
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
        try:
            self.db.delete(document)
            self.db.commit()
            return response
        except Exception as e:
            raise DocumentDeletionError(f"Failed to delete document with id {document_id}: {str(e)}") from e