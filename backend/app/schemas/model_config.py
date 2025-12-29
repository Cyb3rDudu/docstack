from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class ModelConfigBase(BaseModel):
    embedder_model: str = Field(..., min_length=1)
    embedder_settings: Optional[Dict[str, Any]] = None
    splitter_type: str = Field(..., pattern="^(sentence|word|passage)$")
    split_length: int = Field(..., gt=0, le=1000)
    split_overlap: int = Field(..., ge=0, le=500)
    splitter_settings: Optional[Dict[str, Any]] = None


class ModelConfigCreate(ModelConfigBase):
    pass


class ModelConfigUpdate(BaseModel):
    embedder_model: Optional[str] = Field(None, min_length=1)
    embedder_settings: Optional[Dict[str, Any]] = None
    splitter_type: Optional[str] = Field(None, pattern="^(sentence|word|passage)$")
    split_length: Optional[int] = Field(None, gt=0, le=1000)
    split_overlap: Optional[int] = Field(None, ge=0, le=500)
    splitter_settings: Optional[Dict[str, Any]] = None


class ModelConfigResponse(ModelConfigBase):
    id: UUID
    docstore_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
