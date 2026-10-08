from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    organization_id: int
    event_type: str
    title: str
    message: str
    is_read: bool
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    unread_count: int
    items: List[NotificationResponse]
