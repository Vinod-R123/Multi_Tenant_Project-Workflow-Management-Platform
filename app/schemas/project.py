from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import ProjectStatus
from app.schemas.auth import UserResponse


class ProjectBase(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


class ProjectCreate(ProjectBase):
    status: ProjectStatus = ProjectStatus.PLANNING


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


class ProjectStatusUpdate(BaseModel):
    status: ProjectStatus


class ProjectResponse(BaseModel):
    id: int
    organization_id: int
    owner_id: int
    name: str
    description: Optional[str] = None
    status: ProjectStatus
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    owner: Optional[UserResponse] = None
    member_count: Optional[int] = 0
    task_count: Optional[int] = 0
    model_config = ConfigDict(from_attributes=True)


class AddProjectMemberRequest(BaseModel):
    user_id: int


class ProjectMemberResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    joined_at: datetime
    user: Optional[UserResponse] = None
    model_config = ConfigDict(from_attributes=True)
