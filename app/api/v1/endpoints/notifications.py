from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user, get_organization_context
from app.core.response import APIResponse
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=APIResponse[NotificationListResponse])
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NotificationService(db)
    skip = (page - 1) * page_size
    data = service.list_notifications(
        org_id=org_id,
        user=current_user,
        skip=skip,
        limit=page_size,
        unread_only=unread_only
    )
    return APIResponse(success=True, data=data)


@router.patch("/{notification_id}/read", response_model=APIResponse[NotificationResponse])
def mark_as_read(
    notification_id: int,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NotificationService(db)
    notif = service.mark_as_read(org_id, notification_id, current_user)
    return APIResponse(success=True, data=notif)


@router.patch("/read-all", response_model=APIResponse[dict])
def mark_all_read(
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NotificationService(db)
    count = service.mark_all_read(org_id, current_user)
    return APIResponse(success=True, data={"message": f"{count} notifications marked as read"})
