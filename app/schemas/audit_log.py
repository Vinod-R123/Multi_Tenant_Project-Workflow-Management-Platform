from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.auth import UserResponse


class AuditLogResponse(BaseModel):
    id: int
    organization_id: int
    user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    ip_address: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime
    user: Optional[UserResponse] = None
    model_config = ConfigDict(from_attributes=True)
