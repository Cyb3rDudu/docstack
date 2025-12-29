from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class DocstoreBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None


class DocstoreCreate(DocstoreBase):
    pass


class DocstoreUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class DocstoreResponse(DocstoreBase):
    id: UUID
    index_name: str
    created_by: UUID
    document_count: int
    chunk_count: int
    total_size_bytes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocstoreStats(BaseModel):
    id: UUID
    name: str
    slug: str
    document_count: int
    chunk_count: int
    total_size_bytes: int
    index_name: str
    is_active: bool
