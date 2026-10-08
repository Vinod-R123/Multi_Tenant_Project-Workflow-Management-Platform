from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.auth import UserResponse


class AttachmentResponse(BaseModel):
    id: int
    organization_id: int
    uploaded_by: Optional[int] = None
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    file_name: str
    file_size: int
    mime_type: str
    created_at: datetime
    uploaded_by_user: Optional[UserResponse] = None
    download_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
