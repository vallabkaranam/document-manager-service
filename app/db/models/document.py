import enum
from sqlalchemy import Column, Enum, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base


class TagStatusEnum(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    storage_path = Column(String, nullable=False)
    upload_time = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    description = Column(String, nullable=True)
    user_id = Column(Integer, nullable=False, index=True)
    tag_status = Column(Enum(TagStatusEnum), nullable=False, default=TagStatusEnum.pending)
    tag_status_updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    # Relationships
    document_tags = relationship("DocumentTag", back_populates="document", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="document_tags", back_populates="documents", overlaps="document_tags,tag")