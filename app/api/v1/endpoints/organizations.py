from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.api.dependencies import get_client_ip, get_current_user
from app.core.response import APIResponse, PaginatedData, PaginatedResponse, PaginationMetadata
from app.db.session import get_db
from app.models.enums import OrganizationRole
from app.models.user import User
from app.schemas.organization import (
    AddMemberRequest,
    OrganizationCreate,
    OrganizationMemberResponse,
    OrganizationResponse,
    OrganizationUpdate,
    UpdateMemberRoleRequest,
    UpdateMemberStatusRequest,
)
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", response_model=APIResponse[OrganizationResponse], status_code=201)
def create_organization(
    req: OrganizationCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = OrganizationService(db)
    ip_addr = get_client_ip(request)
    org_resp = service.create_organization(current_user, req, ip_address=ip_addr)
    return APIResponse(success=True, data=org_resp)


@router.get("", response_model=APIResponse[List[OrganizationResponse]])
def list_my_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = OrganizationService(db)
    orgs = service.list_user_organizations(current_user)
    return APIResponse(success=True, data=orgs)


@router.get("/{org_id}", response_model=APIResponse[OrganizationResponse])
def get_organization(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = OrganizationService(db)
    org = service.get_organization(org_id, current_user)
    return APIResponse(success=True, data=org)


@router.put("/{org_id}", response_model=APIResponse[OrganizationResponse])
def update_organization(
    org_id: int,
    req: OrganizationUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = OrganizationService(db)
    ip_addr = get_client_ip(request)
    updated = service.update_organization(org_id, req, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=updated)


@router.post("/{org_id}/members", response_model=APIResponse[OrganizationMemberResponse], status_code=201)
def add_member(
    org_id: int,
    req: AddMemberRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = OrganizationService(db)
    ip_addr = get_client_ip(request)
    member = service.add_member(org_id, req, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=member)


@router.delete("/{org_id}/members/{user_id}", response_model=APIResponse[dict])
def remove_member(
    org_id: int,
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = OrganizationService(db)
    ip_addr = get_client_ip(request)
    service.remove_member(org_id, user_id, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data={"message": "Member removed successfully"})


@router.patch("/{org_id}/members/{user_id}/role", response_model=APIResponse[OrganizationMemberResponse])
def update_member_role(
    org_id: int,
    user_id: int,
    req: UpdateMemberRoleRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = OrganizationService(db)
    ip_addr = get_client_ip(request)
    updated_member = service.update_member_role(org_id, user_id, req.role, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=updated_member)


@router.patch("/{org_id}/members/{user_id}/status", response_model=APIResponse[OrganizationMemberResponse])
def update_member_status(
    org_id: int,
    user_id: int,
    req: UpdateMemberStatusRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = OrganizationService(db)
    ip_addr = get_client_ip(request)
    updated_member = service.update_member_status(org_id, user_id, req.is_active, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=updated_member)


@router.get("/{org_id}/members", response_model=PaginatedResponse[OrganizationMemberResponse])
def list_organization_members(
    org_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[OrganizationRole] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = OrganizationService(db)
    skip = (page - 1) * page_size
    members, total = service.list_members(
        org_id=org_id,
        user=current_user,
        skip=skip,
        limit=page_size,
        role=role,
        is_active=is_active,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        success=True,
        data=PaginatedData(
            items=members,
            pagination=PaginationMetadata(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )
        )
    )
