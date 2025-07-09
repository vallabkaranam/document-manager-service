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
        return [TagPydantic(id=tag.id, text=tag.text, created_at=tag.created_at) for tag in tags]

    def create_tag(self, tag_text: str) -> TagPydantic:
        tag = Tag(text=tag_text)
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return TagPydantic(id=tag.id, text=tag.text, created_at=tag.created_at) 

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