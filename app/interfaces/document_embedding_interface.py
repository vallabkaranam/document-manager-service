"""
Document Embedding Interface Module

Encapsulates all business logic related to document-level embeddings,
abstracting the database layer and providing clean, validated interfaces
to the controller and route layers.

Key Capabilities:
- Create a document embedding
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
    SimilarChunkSearchError,
)
from app.schemas.rag_schemas import SimilarChunk


class DocumentEmbeddingInterface:
    def __init__(self, db: Session) -> None:
        """
        Initializes the document embedding interface with a database session.

        Args:
            db (Session): SQLAlchemy session object.
        """
        self.db = db

    def get_embedding_by_document_id(self, document_id: str) -> DocumentEmbeddingPydantic:
        """
        Retrieves the chunk embedding by document ID.

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
    
    def get_embedding_by_id(self, embedding_id: str) -> DocumentEmbeddingPydantic:
        """
        Retrieves a document embedding by its primary key ID.

        Args:
            embedding_id (str): UUID string of the embedding.

        Returns:
            DocumentEmbeddingPydantic: The embedding object.

        Raises:
            DocumentEmbeddingNotFoundError: If no embedding exists for the given ID.
        """
        embedding_uuid = uuid.UUID(embedding_id)
        embedding = (
            self.db.query(DocumentEmbedding)
            .filter(DocumentEmbedding.id == embedding_uuid)
            .first()
        )

        if not embedding:
            raise DocumentEmbeddingNotFoundError(
                f"No embedding found with id {embedding_id}"
            )

        return DocumentEmbeddingPydantic.model_validate(embedding)

    

    def create_chunk_embedding(
        self, document_id: str, embedding_vector: List[float], chunk_text: str
    ) -> DocumentEmbeddingPydantic:
        """
        Creates a new chunk embedding with the provided embedding vector and chunk text.

        Args:
            document_id (str): UUID string of the document.
            embedding_vector (List[float]): Pre-computed embedding vector.
            chunk_text (str): Text content used to compute the embedding.

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

        try:
            new_embedding = DocumentEmbedding(
                document_id=document_uuid,
                embedding=embedding_vector,
                chunk_text=chunk_text
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
        self, document_id: str, embedding_vector: List[float], chunk_text: str
    ) -> DocumentEmbeddingPydantic:
        """
        Updates an existing document embedding with a new embedding vector and chunk text.

        Args:
            document_id (str): UUID string of the document.
            embedding_vector (List[float]): New embedding vector.
            chunk_text (str): Updated chunk of text associated with the embedding.

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

        try:
            existing.embedding = embedding_vector
            existing.chunk_text = chunk_text
            self.db.commit()
            self.db.refresh(existing)
            return DocumentEmbeddingPydantic.model_validate(existing)
        except Exception as e:
            raise DocumentEmbeddingUpdateError(
                f"Failed to update embedding for document {document_id}: {str(e)}"
            ) from e

    def get_similar_chunks(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[SimilarChunk]:
        sql = text(
            """
            SELECT id, embedding <-> (:query_vector)::vector AS distance
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
            raise SimilarChunkSearchError(
                f"Error while fetching similar documents: {str(e)}"
            ) from e

        similar_chunks = []

        for row in results:
            try:
                chunk_obj = self.get_embedding_by_id(str(row.id))
                chunk_dict = chunk_obj.model_dump()
                chunk_dict["distance"] = row.distance
                chunk_dict["similarity_score"] = 1.0 / (1.0 + row.distance)

                similar_chunk = SimilarChunk.model_validate(chunk_dict)
                similar_chunks.append(similar_chunk)
            except Exception as e:
                print(f"Skipping malformed row: {row}\nError: {e}")
                continue

        return similar_chunks