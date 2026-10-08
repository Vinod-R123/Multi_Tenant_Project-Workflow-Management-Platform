from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.api.dependencies import get_client_ip, get_current_user, get_organization_context
from app.core.response import APIResponse, PaginatedData, PaginatedResponse, PaginationMetadata
from app.db.session import get_db
from app.models.enums import TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.task import (
    AddDependencyRequest,
    TaskAssignRequest,
    TaskCreate,
    TaskDependencyResponse,
    TaskFilterParams,
    TaskPriorityUpdate,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=APIResponse[TaskResponse], status_code=201)
def create_task(
    req: TaskCreate,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = TaskService(db)
    ip_addr = get_client_ip(request)
    task = service.create_task(org_id, req, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=task)


@router.get("", response_model=PaginatedResponse[TaskResponse])
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[int] = None,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    assignee_id: Optional[int] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = TaskService(db)
    filters = TaskFilterParams(
        project_id=project_id,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        search=search,
    )
    skip = (page - 1) * page_size
    tasks, total = service.list_tasks(
        org_id=org_id,
        user=current_user,
        skip=skip,
        limit=page_size,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        success=True,
        data=PaginatedData(
            items=tasks,
            pagination=PaginationMetadata(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )
        )
    )


@router.get("/{task_id}", response_model=APIResponse[TaskResponse])
def get_task(
    task_id: int,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = TaskService(db)
    task = service.get_task(org_id, task_id, current_user)
    return APIResponse(success=True, data=task)


@router.put("/{task_id}", response_model=APIResponse[TaskResponse])
def update_task(
    task_id: int,
    req: TaskUpdate,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = TaskService(db)
    ip_addr = get_client_ip(request)
    updated = service.update_task(org_id, task_id, req, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=updated)


@router.delete("/{task_id}", response_model=APIResponse[dict])
def delete_task(
    task_id: int,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = TaskService(db)
    ip_addr = get_client_ip(request)
    service.delete_task(org_id, task_id, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data={"message": "Task deleted successfully"})


@router.patch("/{task_id}/status", response_model=APIResponse[TaskResponse])
def change_task_status(
    task_id: int,
    req: TaskStatusUpdate,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = TaskService(db)
    ip_addr = get_client_ip(request)
    updated = service.change_status(org_id, task_id, req, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=updated)


@router.patch("/{task_id}/assign", response_model=APIResponse[TaskResponse])
def assign_task(
    task_id: int,
    req: TaskAssignRequest,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = TaskService(db)
    ip_addr = get_client_ip(request)
    updated = service.assign_task(org_id, task_id, req.assignee_id, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=updated)


@router.patch("/{task_id}/priority", response_model=APIResponse[TaskResponse])
def change_task_priority(
    task_id: int,
    req: TaskPriorityUpdate,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = TaskService(db)
    ip_addr = get_client_ip(request)
    updated = service.change_priority(org_id, task_id, req.priority, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=updated)


@router.post("/{task_id}/dependencies", response_model=APIResponse[TaskDependencyResponse], status_code=201)
def add_task_dependency(
    task_id: int,
    req: AddDependencyRequest,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = TaskService(db)
    ip_addr = get_client_ip(request)
    dep = service.add_dependency(org_id, task_id, req, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data=dep)


@router.delete("/{task_id}/dependencies/{dependency_id}", response_model=APIResponse[dict])
def remove_task_dependency(
    task_id: int,
    dependency_id: int,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = TaskService(db)
    ip_addr = get_client_ip(request)
    service.remove_dependency(org_id, task_id, dependency_id, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data={"message": "Dependency removed successfully"})


@router.get("/{task_id}/dependencies", response_model=APIResponse[List[TaskDependencyResponse]])
def list_task_dependencies(
    task_id: int,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = TaskService(db)
    deps = service.list_dependencies(org_id, task_id, current_user)
    return APIResponse(success=True, data=deps)
