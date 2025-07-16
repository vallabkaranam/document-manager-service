from datetime import datetime, timezone
from typing import List
import uuid
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.models.document import Document
from app.db.models.tag import Tag
from app.schemas.errors import DocumentNotFoundError, SimilarTagSearchError, TagCreationError, TagDeletionError, TagNotFoundError, TagUpdateError
from app.schemas.tag_schemas import SimilarTag, Tag as TagPydantic, TagUpdate, TagsResponse
from app.utils.document_utils import embed_text

class TagInterface:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_tags(self) -> List[TagPydantic]:
        tags = self.db.query(Tag).all()
        return [TagPydantic(id=tag.id, text=tag.text, created_at=tag.created_at, updated_at=tag.updated_at) for tag in tags]

    def create_tag(self, tag_text: str) -> TagPydantic:
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
        tag_uuid = uuid.UUID(tag_id)
        tag = self.db.query(Tag).filter(Tag.id == tag_uuid).first()

        if not tag:
            raise TagNotFoundError(f"Tag with id {tag_id} not found")

        try:
            # Create response before deleting
            response = TagPydantic.model_validate(tag)
                
            self.db.delete(tag)
            self.db.commit()
            return response
        except Exception as e:
            raise TagDeletionError(f"Failed to delete tag '{tag_id}': {str(e)}") from e
    
    def get_tag_by_id(self, tag_id: str) -> TagPydantic:
        tag_uuid = uuid.UUID(tag_id)
        tag = self.db.query(Tag).filter(Tag.id == tag_uuid).first()

        if not tag:
            raise TagNotFoundError(f"Tag with id {tag_id} not found")

        tag_response = TagPydantic.model_validate(tag)
        return tag_response
    
    def update_tag(self, tag_id: str, update_data: TagUpdate) -> TagPydantic:
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

    def get_tags_by_document_id(self, document_id: str) -> TagsResponse:
        document_uuid = uuid.UUID(document_id)
        document = self.db.query(Document).filter(Document.id == document_uuid).first()
        if not document:
            raise DocumentNotFoundError(f"Unable to get document with id {document_id}")

        tags = [TagPydantic.model_validate(tag) for tag in document.tags]

        return tags
    
    def get_similar_tags(self, query_embedding: list[float], top_k: int = 5) -> List[SimilarTag]:
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


        