from sqlalchemy import Column, String, DateTime, Boolean, Integer, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Docstore(Base):
    __tablename__ = "docstores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    index_name = Column(String, nullable=False)  # OpenSearch index name

    # Foreign Keys
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Denormalized stats
    document_count = Column(Integer, default=0, nullable=False)
    chunk_count = Column(Integer, default=0, nullable=False)
    total_size_bytes = Column(BigInteger, default=0, nullable=False)

    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = relationship("User", back_populates="docstores")
    documents = relationship("Document", back_populates="docstore", cascade="all, delete-orphan")
    model_configs = relationship("ModelConfig", back_populates="docstore", cascade="all, delete-orphan")
    pipelines = relationship("Pipeline", back_populates="docstore", cascade="all, delete-orphan")
