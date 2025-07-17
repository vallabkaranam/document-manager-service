"""
Tag Interface Module

Encapsulates all business logic for tag-related operations, abstracting the database layer
and providing clean, validated interfaces to the controller and route layers.

Key Capabilities:
- Create, retrieve, update, and delete tags
- Fetch tags associated with a document
- Perform semantic similarity search using pgvector
- Ensure validation and exception safety across operations

Assumptions:
- Tags use vector embeddings for semantic search
- Embeddings are stored in a `vector` column using pgvector
- All inputs and outputs are validated Pydantic models
"""

from datetime import datetime, timezone
from typing import List
import uuid

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.tag import Tag
from app.schemas.errors import (
    DocumentNotFoundError,
    SimilarTagSearchError,
    TagCreationError,
    TagDeletionError,
    TagNotFoundError,
    TagUpdateError,
)
from app.schemas.tag_schemas import SimilarTag, Tag as TagPydantic, TagUpdate
from app.utils.document_utils import embed_text


class TagInterface:
    def __init__(self, db: Session) -> None:
        """
        Initializes the tag interface with a database session.

        Args:
            db (Session): SQLAlchemy session object.
        """
        self.db = db

    def get_all_tags(self) -> List[TagPydantic]:
        """
        Fetches all tags from the database.

        Returns:
            List[TagPydantic]: List of all tags.
        """
        tags = self.db.query(Tag).all()
        return [
            TagPydantic(
                id=tag.id,
                text=tag.text,
                created_at=tag.created_at,
                updated_at=tag.updated_at,
            )
            for tag in tags
        ]

    def create_tag(self, tag_text: str) -> TagPydantic:
        """
        Creates a new tag with an embedding.

        Args:
            tag_text (str): The text of the tag to create.

        Returns:
            TagPydantic: The created tag.

        Raises:
            TagCreationError: If the tag creation fails.
        """
        embedding = embed_text(tag_text)
        tag = Tag(text=tag_text, embedding=embedding)
        try:
            self.db.add(tag)
            self.db.commit()
            self.db.refresh(tag)
            return TagPydantic.model_validate(tag)
        except Exception as e:
            raise TagCreationError(f"Failed to create tag '{tag_text}': {str(e)}") from e

    def delete_tag(self, tag_id: str) -> TagPydantic:
        """
        Deletes a tag by its ID.

        Args:
            tag_id (str): UUID string of the tag.

        Returns:
            TagPydantic: The deleted tag.

        Raises:
            TagNotFoundError: If the tag does not exist.
            TagDeletionError: If deletion fails.
        """
        tag_uuid = uuid.UUID(tag_id)
        tag = self.db.query(Tag).filter(Tag.id == tag_uuid).first()

        if not tag:
            raise TagNotFoundError(f"Tag with id {tag_id} not found")

        try:
            response = TagPydantic.model_validate(tag)
            self.db.delete(tag)
            self.db.commit()
            return response
        except Exception as e:
            raise TagDeletionError(f"Failed to delete tag '{tag_id}': {str(e)}") from e

    def get_tag_by_id(self, tag_id: str) -> TagPydantic:
        """
        Retrieves a tag by its ID.

        Args:
            tag_id (str): UUID string of the tag.

        Returns:
            TagPydantic: The tag object.

        Raises:
            TagNotFoundError: If the tag is not found.
        """
        tag_uuid = uuid.UUID(tag_id)
        tag = self.db.query(Tag).filter(Tag.id == tag_uuid).first()

        if not tag:
            raise TagNotFoundError(f"Tag with id {tag_id} not found")

        return TagPydantic.model_validate(tag)

    def update_tag(self, tag_id: str, update_data: TagUpdate) -> TagPydantic:
        """
        Updates fields of an existing tag.

        Args:
            tag_id (str): UUID string of the tag.
            update_data (TagUpdate): Fields to update.

        Returns:
            TagPydantic: The updated tag.

        Raises:
            TagNotFoundError: If the tag is not found.
            TagUpdateError: If update fails.
        """
        tag_uuid = uuid.UUID(tag_id)
        tag = self.db.query(Tag).filter(Tag.id == tag_uuid).first()

        if not tag:
            raise TagNotFoundError(f"Tag with id {tag_id} not found")

        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(tag, field, value)
        tag.updated_at = datetime.now(timezone.utc)

        try:
            self.db.commit()
            self.db.refresh(tag)
            return TagPydantic.model_validate(tag)
        except Exception as e:
            raise TagUpdateError(f"Failed to update tag '{tag_id}': {str(e)}") from e

    def get_tags_by_document_id(self, document_id: str) -> List[TagPydantic]:
        """
        Returns all tags associated with a document.

        Args:
            document_id (str): UUID string of the document.

        Returns:
            List[TagPydantic]: Tags linked to the document.

        Raises:
            DocumentNotFoundError: If the document is not found.
        """
        document_uuid = uuid.UUID(document_id)
        document = self.db.query(Document).filter(Document.id == document_uuid).first()

        if not document:
            raise DocumentNotFoundError(f"Unable to get document with id {document_id}")

        return [TagPydantic.model_validate(tag) for tag in document.tags]

    def get_similar_tags(self, query_embedding: list[float], top_k: int = 5) -> List[SimilarTag]:
        """
        Retrieves tags most similar to the input embedding using pgvector similarity.

        Args:
            query_embedding (list[float]): The embedding to compare against.
            top_k (int): Number of most similar tags to retrieve.

        Returns:
            List[SimilarTag]: Top-k similar tags with distances.

        Raises:
            SimilarTagSearchError: If the query fails.
        
        Notes:
            This uses PostgreSQL + pgvector's '<->' operator for L2 distance sorting.
            The query returns tags with non-null embeddings ordered by similarity.
        """
        sql = text("""
            SELECT id, text, embedding <-> (:query_vector)::vector AS distance
            FROM tags
            WHERE embedding IS NOT NULL
            ORDER BY embedding <-> (:query_vector)::vector
            LIMIT :top_k
        """)

        try:
            tags_from_db = self.db.execute(sql, {
                "query_vector": query_embedding,
                "top_k": top_k
            }).fetchall()
        except Exception as e:
            raise SimilarTagSearchError(f"Error while fetching similar tags: {str(e)}") from e

        tags = []
        for row in tags_from_db:
            try:
                tag_obj = self.get_tag_by_id(str(row.id))
            except TagNotFoundError as e:
                print(str(e))
                continue

            tag_dict = tag_obj.model_dump()
            tag_dict["distance"] = row.distance
            tag = SimilarTag.model_validate(tag_dict)
            tags.append(tag)

        return tags