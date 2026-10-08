from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.api.dependencies import get_client_ip, get_current_user, get_organization_context
from app.core.response import APIResponse
from app.db.session import get_db
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.services.comment_service import CommentService

router = APIRouter(prefix="/comments", tags=["Comments"])


@router.post("", response_model=APIResponse[CommentResponse], status_code=201)
def add_comment(
    req: CommentCreate,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = CommentService(db)
    ip_addr = get_client_ip(request)
    comment = service.create_comment(org_id, req, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=comment)


@router.get("", response_model=APIResponse[List[CommentResponse]])
def list_comments(
    task_id: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = CommentService(db)
    comments = service.list_comments(org_id, current_user, task_id=task_id, project_id=project_id)
    return APIResponse(success=True, data=comments)


@router.put("/{comment_id}", response_model=APIResponse[CommentResponse])
def update_comment(
    comment_id: int,
    req: CommentUpdate,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = CommentService(db)
    ip_addr = get_client_ip(request)
    updated = service.update_comment(org_id, comment_id, req, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=updated)


@router.delete("/{comment_id}", response_model=APIResponse[dict])
def delete_comment(
    comment_id: int,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = CommentService(db)
    ip_addr = get_client_ip(request)
    service.delete_comment(org_id, comment_id, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data={"message": "Comment deleted successfully"})
