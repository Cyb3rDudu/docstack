from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.document import ProcessingStatus


class DocumentBase(BaseModel):
    filename: str
    original_filename: str


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    mime_type: str = Field(..., serialization_alias='file_type')
    size_bytes: int = Field(..., serialization_alias='file_size_bytes')
    checksum: str
    processing_status: ProcessingStatus
    uploaded_at: datetime = Field(..., serialization_alias='created_at')
    docstore_id: UUID

    class Config:
        from_attributes = True
        populate_by_name = True


class DocumentResponse(DocumentUploadResponse):
    chunk_count: int
    page_count: Optional[int]
    processing_error: Optional[str] = Field(None, serialization_alias='error_message')
    processed_at: Optional[datetime]
    uploaded_by: UUID

    class Config:
        from_attributes = True
        populate_by_name = True


class DocumentUpdate(BaseModel):
    processing_status: Optional[ProcessingStatus] = None
    chunk_count: Optional[int] = None
    page_count: Optional[int] = None
    processing_error: Optional[str] = None
