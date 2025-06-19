from sqlalchemy import Column, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base

class DocumentTag(Base):
    __tablename__ = "document_tags"

    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="document_tags")
    tag = relationship("Tag", back_populates="document_tags")