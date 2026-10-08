from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user, get_organization_context
from app.core.response import PaginatedData, PaginatedResponse, PaginationMetadata
from app.db.session import get_db
from app.models.user import User
from app.schemas.audit_log import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    target_user_id: Optional[int] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AuditService(db)
    skip = (page - 1) * page_size
    logs, total = service.list_logs(
        org_id=org_id,
        user=current_user,
        skip=skip,
        limit=page_size,
        target_user_id=target_user_id,
        action=action,
        entity_type=entity_type,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        success=True,
        data=PaginatedData(
            items=logs,
            pagination=PaginationMetadata(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )
        )
    )
