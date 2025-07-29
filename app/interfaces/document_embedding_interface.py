"""
Document Embedding Interface Module

Encapsulates all business logic related to document-level embeddings,
abstracting the database layer and providing clean, validated interfaces
to the controller and route layers.

Key Capabilities:
- Create a document embedding if one does not exist
- Update an existing document embedding
- Retrieve embeddings for a specific document
- Perform semantic similarity search using pgvector
- Validate UUIDs and enforce exception-safe operations

Assumptions:
- Embeddings are stored in a `vector` column using pgvector
- One embedding per document (1:1 relationship)
- Embeddings are computed from text using a shared utility
- All inputs and outputs use validated Pydantic models
"""

import uuid
from typing import List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.document_embedding import DocumentEmbedding
from app.schemas.document_embedding_schemas import DocumentEmbedding as DocumentEmbeddingPydantic
from app.schemas.errors import (
    DocumentNotFoundError,
    DocumentEmbeddingCreationError,
    DocumentEmbeddingNotFoundError,
    DocumentEmbeddingUpdateError,
    SimilarDocumentSearchError,
)
from app.utils.document_utils import embed_text


class DocumentEmbeddingInterface:
    def __init__(self, db: Session) -> None:
        """
        Initializes the document embedding interface with a database session.

        Args:
            db (Session): SQLAlchemy session object.
        """
        self.db = db

    def get_by_document_id(self, document_id: str) -> DocumentEmbeddingPydantic:
        """
        Retrieves the document embedding by document ID.

        Args:
            document_id (str): UUID string of the document.

        Returns:
            DocumentEmbeddingPydantic: The document's embedding.

        Raises:
            DocumentEmbeddingNotFoundError: If no embedding exists for the document.
        """
        document_uuid = uuid.UUID(document_id)
        embedding = (
            self.db.query(DocumentEmbedding)
            .filter(DocumentEmbedding.document_id == document_uuid)
            .first()
        )

        if not embedding:
            raise DocumentEmbeddingNotFoundError(
                f"No embedding found for document id {document_id}"
            )

        return DocumentEmbeddingPydantic.model_validate(embedding)

    def create_embedding(
        self, document_id: str, text_content: str
    ) -> DocumentEmbeddingPydantic:
        """
        Creates a new document embedding from raw text.

        Args:
            document_id (str): UUID string of the document.
            text_content (str): Raw text to embed.

        Returns:
            DocumentEmbeddingPydantic: The created embedding.

        Raises:
            DocumentNotFoundError: If the document does not exist.
            DocumentEmbeddingCreationError: If an embedding already exists or operation fails.
        """
        document_uuid = uuid.UUID(document_id)
        document = self.db.query(Document).filter(Document.id == document_uuid).first()

        if not document:
            raise DocumentNotFoundError(f"Document {document_id} not found")

        existing = (
            self.db.query(DocumentEmbedding)
            .filter(DocumentEmbedding.document_id == document_uuid)
            .first()
        )
        if existing:
            raise DocumentEmbeddingCreationError(
                f"Embedding already exists for document {document_id}"
            )

        embedding_vector = embed_text(text_content)

        try:
            new_embedding = DocumentEmbedding(
                document_id=document_uuid,
                embedding=embedding_vector,
            )
            self.db.add(new_embedding)
            self.db.commit()
            self.db.refresh(new_embedding)
            return DocumentEmbeddingPydantic.model_validate(new_embedding)
        except Exception as e:
            raise DocumentEmbeddingCreationError(
                f"Failed to create embedding for document {document_id}: {str(e)}"
            ) from e

    def update_embedding(
        self, document_id: str, text_content: str
    ) -> DocumentEmbeddingPydantic:
        """
        Updates an existing document embedding with new text.

        Args:
            document_id (str): UUID string of the document.
            text_content (str): New text to re-embed.

        Returns:
            DocumentEmbeddingPydantic: The updated embedding.

        Raises:
            DocumentEmbeddingNotFoundError: If the embedding does not exist.
            DocumentEmbeddingUpdateError: If update fails.
        """
        document_uuid = uuid.UUID(document_id)

        existing = (
            self.db.query(DocumentEmbedding)
            .filter(DocumentEmbedding.document_id == document_uuid)
            .first()
        )
        if not existing:
            raise DocumentEmbeddingNotFoundError(
                f"No existing embedding to update for document {document_id}"
            )

        new_embedding_vector = embed_text(text_content)

        try:
            existing.embedding = new_embedding_vector
            self.db.commit()
            self.db.refresh(existing)
            return DocumentEmbeddingPydantic.model_validate(existing)
        except Exception as e:
            raise DocumentEmbeddingUpdateError(
                f"Failed to update embedding for document {document_id}: {str(e)}"
            ) from e

    def get_similar_documents(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[DocumentEmbeddingPydantic]:
        """
        Retrieves documents most similar to the input embedding using pgvector similarity.

        Args:
            query_embedding (List[float]): The embedding to compare against.
            top_k (int): Number of most similar documents to retrieve.

        Returns:
            List[DocumentEmbeddingPydantic]: Top-k similar documents.

        Raises:
            SimilarDocumentSearchError: If the query fails.

        Notes:
            This uses PostgreSQL + pgvector's '<->' operator for L2 distance sorting.
        """
        sql = text(
            """
            SELECT id, document_id, embedding, created_at, embedding <-> (:query_vector)::vector AS distance
            FROM document_embeddings
            WHERE embedding IS NOT NULL
            ORDER BY embedding <-> (:query_vector)::vector
            LIMIT :top_k
            """
        )

        try:
            results = self.db.execute(
                sql, {"query_vector": query_embedding, "top_k": top_k}
            ).fetchall()
        except Exception as e:
            raise SimilarDocumentSearchError(
                f"Error while fetching similar documents: {str(e)}"
            ) from e

        similar = []
        for row in results:
            try:
                embedding = DocumentEmbeddingPydantic(
                    id=row.id,
                    document_id=row.document_id,
                    embedding=row.embedding,
                    created_at=row.created_at,
                )
                similar.append(embedding)
            except Exception:
                continue  # Skip malformed rows

        return similar