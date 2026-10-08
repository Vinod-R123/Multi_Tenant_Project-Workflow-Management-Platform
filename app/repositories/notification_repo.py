from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db: Session):
        super().__init__(Notification, db)

    def list_user_notifications(
        self,
        user_id: int,
        organization_id: int,
        skip: int = 0,
        limit: int = 20,
        unread_only: bool = False
    ) -> Tuple[List[Notification], int]:
        query = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.organization_id == organization_id,
        )
        if unread_only:
            query = query.filter(Notification.is_read == False)

        total = query.count()
        items = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def count_unread(self, user_id: int, organization_id: int) -> int:
        return (
            self.db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
                Notification.is_read == False,
            )
            .count()
        )

    def mark_as_read(self, notification_id: int, user_id: int) -> Optional[Notification]:
        notif = (
            self.db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if notif:
            notif.is_read = True
            self.db.commit()
            self.db.refresh(notif)
            return notif
        return None

    def mark_all_read(self, user_id: int, organization_id: int) -> int:
        updated = (
            self.db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
                Notification.is_read == False,
            )
            .update({"is_read": True})
        )
        self.db.commit()
        return updated
