from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class DocstoreBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class DocstoreCreate(DocstoreBase):
    """Schema for creating a new docstore with chunking configuration"""
    embedding_model: str = Field(
        ...,
        description="Sentence transformer model for embeddings (e.g., 'BAAI/bge-large-en-v1.5', 'sentence-transformers/all-MiniLM-L6-v2')"
    )
    split_by: str = Field(
        default="sentence",
        description="Chunking strategy: 'word' (fixed word count), 'sentence' (semantic by sentence), 'passage' (semantic by paragraph)"
    )
    chunk_size: int = Field(
        ...,
        ge=1,
        le=1000,
        description="Number of units per chunk (words, sentences, or passages depending on split_by)"
    )
    chunk_overlap: int = Field(
        ...,
        ge=0,
        le=500,
        description="Number of units to overlap between chunks"
    )


class DocstoreUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class DocstoreResponse(DocstoreBase):
    id: UUID
    slug: str
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
