from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base
from app.db.models.document_tag import DocumentTag


class Tag(Base):
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    text = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document_tags = relationship("DocumentTag", back_populates="tag", cascade="all, delete-orphan")
    documents = relationship("Document", secondary="document_tags", back_populates="tags", overlaps="document_tags,tag")