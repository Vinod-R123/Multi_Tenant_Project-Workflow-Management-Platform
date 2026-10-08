from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.api.dependencies import get_client_ip, get_current_user, get_organization_context
from app.core.response import APIResponse, PaginatedData, PaginatedResponse, PaginationMetadata
from app.db.session import get_db
from app.models.enums import ProjectStatus
from app.models.user import User
from app.schemas.project import (
    AddProjectMemberRequest,
    ProjectCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=APIResponse[ProjectResponse], status_code=201)
def create_project(
    req: ProjectCreate,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    ip_addr = get_client_ip(request)
    proj = service.create_project(org_id, req, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=proj)


@router.get("", response_model=PaginatedResponse[ProjectResponse])
def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[ProjectStatus] = None,
    search: Optional[str] = None,
    owner_id: Optional[int] = None,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    skip = (page - 1) * page_size
    projects, total = service.list_projects(
        org_id=org_id,
        user=current_user,
        skip=skip,
        limit=page_size,
        status=status,
        search=search,
        owner_id=owner_id,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        success=True,
        data=PaginatedData(
            items=projects,
            pagination=PaginationMetadata(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )
        )
    )


@router.get("/{project_id}", response_model=APIResponse[ProjectResponse])
def get_project(
    project_id: int,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    proj = service.get_project(org_id, project_id, current_user)
    return APIResponse(success=True, data=proj)


@router.put("/{project_id}", response_model=APIResponse[ProjectResponse])
def update_project(
    project_id: int,
    req: ProjectUpdate,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    ip_addr = get_client_ip(request)
    updated = service.update_project(org_id, project_id, req, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=updated)


@router.patch("/{project_id}/archive", response_model=APIResponse[ProjectResponse])
def archive_project(
    project_id: int,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    ip_addr = get_client_ip(request)
    archived = service.archive_project(org_id, project_id, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=archived)


@router.delete("/{project_id}", response_model=APIResponse[dict])
def delete_project(
    project_id: int,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    ip_addr = get_client_ip(request)
    service.delete_project(org_id, project_id, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data={"message": "Project deleted successfully"})


@router.post("/{project_id}/members", response_model=APIResponse[ProjectMemberResponse], status_code=201)
def add_project_member(
    project_id: int,
    req: AddProjectMemberRequest,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    ip_addr = get_client_ip(request)
    member = service.add_project_member(org_id, project_id, req, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=member)


@router.delete("/{project_id}/members/{user_id}", response_model=APIResponse[dict])
def remove_project_member(
    project_id: int,
    user_id: int,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    ip_addr = get_client_ip(request)
    service.remove_project_member(org_id, project_id, user_id, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data={"message": "Project member removed successfully"})


@router.get("/{project_id}/members", response_model=APIResponse[List[ProjectMemberResponse]])
def list_project_members(
    project_id: int,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ProjectService(db)
    members = service.list_project_members(org_id, project_id, current_user)
    return APIResponse(success=True, data=members)
