from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.pipeline import PipelineType


class PipelineBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    pipeline_type: PipelineType
    yaml_content: str


class PipelineCreate(PipelineBase):
    pass


class PipelineUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    yaml_content: Optional[str] = None
    is_active: Optional[bool] = None


class PipelineResponse(PipelineBase):
    id: UUID
    docstore_id: UUID
    created_by: UUID
    version: int
    is_active: bool
    deployed: bool
    deployed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
