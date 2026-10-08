from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.auth import UserResponse


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    project_id: Optional[int] = None
    task_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    id: int
    organization_id: int
    user_id: int
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    content: str
    created_at: datetime
    updated_at: datetime
    user: Optional[UserResponse] = None
    model_config = ConfigDict(from_attributes=True)
