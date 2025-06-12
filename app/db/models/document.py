# app/models/document.py

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.base import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(String, nullable=True)
    user_id = Column(Integer, nullable=False, index=True)