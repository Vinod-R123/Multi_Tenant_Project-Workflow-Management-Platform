from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.auth import UserResponse


class TaskDependencyResponse(BaseModel):
    id: int
    task_id: int
    depends_on_task_id: int
    created_at: datetime
    prerequisite_title: Optional[str] = None
    prerequisite_status: Optional[TaskStatus] = None
    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    project_id: int
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    estimated_hours: Optional[Decimal] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[Decimal] = None
    actual_hours: Optional[Decimal] = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskPriorityUpdate(BaseModel):
    priority: TaskPriority


class TaskAssignRequest(BaseModel):
    assignee_id: Optional[int] = None


class AddDependencyRequest(BaseModel):
    depends_on_task_id: int


class TaskResponse(BaseModel):
    id: int
    organization_id: int
    project_id: int
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    reporter_id: int
    priority: TaskPriority
    status: TaskStatus
    due_date: Optional[datetime] = None
    estimated_hours: Optional[Decimal] = None
    actual_hours: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    project_name: Optional[str] = None
    assignee: Optional[UserResponse] = None
    reporter: Optional[UserResponse] = None
    prerequisites: List[TaskDependencyResponse] = []
    dependents: List[TaskDependencyResponse] = []
    model_config = ConfigDict(from_attributes=True)


class TaskFilterParams(BaseModel):
    project_id: Optional[int] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee_id: Optional[int] = None
    search: Optional[str] = None
    due_date_from: Optional[datetime] = None
    due_date_to: Optional[datetime] = None
