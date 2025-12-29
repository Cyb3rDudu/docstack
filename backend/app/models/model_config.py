from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    docstore_id = Column(UUID(as_uuid=True), ForeignKey("docstores.id", ondelete="CASCADE"), nullable=False)

    # Embedder configuration
    embedder_model = Column(String, nullable=False)  # e.g., "BAAI/bge-large-en-v1.5"
    embedder_settings = Column(JSONB, nullable=True)  # normalize, batch_size, etc.

    # Splitter configuration
    splitter_type = Column(String, nullable=False)  # 'sentence', 'word', 'passage'
    split_length = Column(Integer, nullable=False)
    split_overlap = Column(Integer, nullable=False)
    splitter_settings = Column(JSONB, nullable=True)

    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    docstore = relationship("Docstore", back_populates="model_configs")
