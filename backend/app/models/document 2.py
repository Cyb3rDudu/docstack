from sqlalchemy import Column, String, DateTime, Integer, BigInteger, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.database import Base


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    docstore_id = Column(UUID(as_uuid=True), ForeignKey("docstores.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # File metadata
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    checksum = Column(String(64), nullable=False, index=True)  # SHA256

    # Processing metadata
    processing_status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    processing_error = Column(String, nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    page_count = Column(Integer, nullable=True)
    source_id = Column(String, nullable=True)  # ID in OpenSearch

    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    docstore = relationship("Docstore", back_populates="documents")
    uploader = relationship("User", back_populates="documents")
