from datetime import datetime, timezone
from typing import List
import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.models.tag import Tag
from app.schemas.tag_schemas import Tag as TagPydantic

class TagInterface:
    def __init__(self, db: Session):
        self.db = db

    def get_all_tags(self) -> List[TagPydantic]:
        tags = self.db.query(Tag).all()
        return [TagPydantic(id=tag.id, text=tag.text, created_at=tag.created_at, updated_at=tag.updated_at) for tag in tags]

    def create_tag(self, tag_text: str) -> TagPydantic:
        tag = Tag(text=tag_text)
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return TagPydantic(id=tag.id, text=tag.text, created_at=tag.created_at, updated_at=tag.updated_at) 

    def delete_tag(self, tag_id: str) -> TagPydantic:
        tag_uuid = uuid.UUID(tag_id)
        tag = self.db.query(Tag).filter(Tag.id == tag_uuid).first()

        if not tag:
            raise HTTPException(
                status_code=404,
                detail=f"Tag with id {tag_id} not found"
            )

        # Create response before deleting
        response = TagPydantic.model_validate(tag)
            
        self.db.delete(tag)
        self.db.commit()
        return response
    
    def get_tag_by_id(self, tag_id: str) -> TagPydantic:
        tag_uuid = uuid.UUID(tag_id)
        tag = self.db.query(Tag).filter(Tag.id == tag_uuid).first()

        if not tag:
            raise HTTPException(
                status_code=404,
                detail=f"Tag with id {tag_id} not found"
            )

        tag_response = TagPydantic.model_validate(tag)
        return tag_response
    
    def update_tag(self, tag_id: str, update_data):
        tag_uuid = uuid.UUID(tag_id)
        tag = self.db.query(Tag).filter(Tag.id == tag_uuid).first()
        if not tag:
            raise HTTPException(
                status_code=404,
                detail=f"Tag with id {tag_id} not found"
            )
        
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(tag, field, value)
        tag.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(tag)
        
        return TagPydantic.model_validate(tag)
        