import asyncio
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.websocket_manager import ws_manager
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.repositories.organization_repo import OrganizationRepository
from app.schemas.notification import NotificationListResponse, NotificationResponse


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.notif_repo = NotificationRepository(db)
        self.org_repo = OrganizationRepository(db)

    def create_notification(
        self,
        organization_id: int,
        user_id: int,
        event_type: str,
        title: str,
        message: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
    ) -> Notification:
        notif = Notification(
            organization_id=organization_id,
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            is_read=False,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        created_notif = self.notif_repo.create(notif)

        # Dispatch real-time WebSocket notification if event loop is running
        payload = {
            "type": "NOTIFICATION",
            "data": {
                "id": created_notif.id,
                "event_type": created_notif.event_type,
                "title": created_notif.title,
                "message": created_notif.message,
                "entity_type": created_notif.entity_type,
                "entity_id": created_notif.entity_id,
                "created_at": created_notif.created_at.isoformat(),
            }
        }
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(ws_manager.send_personal_message(payload, user_id))
        except Exception:
            pass

        return created_notif

    def list_notifications(
        self,
        org_id: int,
        user: User,
        skip: int = 0,
        limit: int = 20,
        unread_only: bool = False
    ) -> NotificationListResponse:
        # Check org membership
        if not user.is_super_admin:
            member = self.org_repo.get_member(org_id, user.id)
            if not member or not member.is_active:
                raise ForbiddenError(message="Access denied", code="ORGANIZATION_ACCESS_DENIED")

        items, _ = self.notif_repo.list_user_notifications(
            user_id=user.id,
            organization_id=org_id,
            skip=skip,
            limit=limit,
            unread_only=unread_only
        )
        unread_count = self.notif_repo.count_unread(user.id, org_id)

        return NotificationListResponse(
            unread_count=unread_count,
            items=[NotificationResponse.model_validate(n) for n in items]
        )

    def mark_as_read(self, org_id: int, notification_id: int, user: User) -> NotificationResponse:
        notif = self.notif_repo.get(notification_id)
        if not notif or notif.organization_id != org_id:
            raise NotFoundError(message="Notification not found", code="NOTIFICATION_NOT_FOUND")

        if notif.user_id != user.id and not user.is_super_admin:
            raise ForbiddenError(message="Access denied", code="FORBIDDEN")

        updated = self.notif_repo.mark_as_read(notification_id, user.id)
        return NotificationResponse.model_validate(updated)

    def mark_all_read(self, org_id: int, user: User) -> int:
        return self.notif_repo.mark_all_read(user.id, org_id)
