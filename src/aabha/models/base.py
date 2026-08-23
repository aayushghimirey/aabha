from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
