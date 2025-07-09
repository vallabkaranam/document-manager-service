from typing import List
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