from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.database import Base


class PipelineType(str, enum.Enum):
    INDEXING = "indexing"
    QUERY = "query"


class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    docstore_id = Column(UUID(as_uuid=True), ForeignKey("docstores.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Pipeline metadata
    name = Column(String, nullable=False)
    pipeline_type = Column(SQLEnum(PipelineType), nullable=False)
    yaml_content = Column(String, nullable=False)  # Full YAML content
    version = Column(Integer, default=1, nullable=False)

    # Deployment status
    is_active = Column(Boolean, default=False, nullable=False)
    deployed = Column(Boolean, default=False, nullable=False)
    deployed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    docstore = relationship("Docstore", back_populates="pipelines")
    creator = relationship("User", back_populates="pipelines")
