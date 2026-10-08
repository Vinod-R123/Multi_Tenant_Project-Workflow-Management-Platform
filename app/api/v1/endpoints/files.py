from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session
from app.api.dependencies import get_client_ip, get_current_user, get_organization_context
from app.core.response import APIResponse
from app.db.session import get_db
from app.models.user import User
from app.schemas.attachment import AttachmentResponse
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", response_model=APIResponse[AttachmentResponse], status_code=201)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    project_id: Optional[int] = Form(None),
    task_id: Optional[int] = Form(None),
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = FileService(db)
    ip_addr = get_client_ip(request)
    attachment = await service.upload_file(
        org_id=org_id,
        file=file,
        user=current_user,
        project_id=project_id,
        task_id=task_id,
        ip_address=ip_addr,
    )
    return APIResponse(success=True, data=attachment)


@router.get("/{file_id}", response_model=APIResponse[AttachmentResponse])
def get_file_metadata(
    file_id: int,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = FileService(db)
    meta = service.get_file_metadata(org_id, file_id, current_user)
    return APIResponse(success=True, data=meta)


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = FileService(db)
    return service.download_file(org_id, file_id, current_user)


@router.get("", response_model=APIResponse[List[AttachmentResponse]])
def list_files(
    task_id: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = FileService(db)
    files = service.list_files(org_id, current_user, task_id=task_id, project_id=project_id)
    return APIResponse(success=True, data=files)


@router.delete("/{file_id}", response_model=APIResponse[dict])
def delete_file(
    file_id: int,
    request: Request,
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = FileService(db)
    ip_addr = get_client_ip(request)
    service.delete_file(org_id, file_id, current_user, ip_address=ip_addr)
    return APIResponse(success=True, data={"message": "File deleted successfully"})
