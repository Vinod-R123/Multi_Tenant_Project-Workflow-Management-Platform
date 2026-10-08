import os
import uuid
from typing import List, Optional
from fastapi import UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models.attachment import Attachment
from app.models.enums import AuditAction, OrganizationRole
from app.models.user import User
from app.repositories.audit_log_repo import AuditLogRepository
from app.repositories.file_repo import FileRepository
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.task_repo import TaskRepository
from app.schemas.attachment import AttachmentResponse

# Magic byte signatures for verification
MAGIC_SIGNATURES = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "gif": [b"GIF87a", b"GIF89a"],
    "zip": [b"PK\x03\x04"],
    "docx": [b"PK\x03\x04"],  # docx is an OpenXML ZIP archive
    "xlsx": [b"PK\x03\x04"],  # xlsx is an OpenXML ZIP archive
}


def verify_file_content(content: bytes, ext: str) -> bool:
    ext = ext.lower().lstrip(".")
    if ext in MAGIC_SIGNATURES:
        signatures = MAGIC_SIGNATURES[ext]
        return any(content.startswith(sig) for sig in signatures)

    if ext in ["txt", "csv"]:
        # Text / CSV must not contain binary null bytes
        if b"\x00" in content[:1024]:
            return False
        try:
            content[:4096].decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False

    return True


class FileService:
    def __init__(self, db: Session):
        self.db = db
        self.file_repo = FileRepository(db)
        self.project_repo = ProjectRepository(db)
        self.task_repo = TaskRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.audit_repo = AuditLogRepository(db)

    def _verify_org_access(self, org_id: int, user: User) -> OrganizationRole:
        if user.is_super_admin:
            return OrganizationRole.ORGANIZATION_ADMIN
        member = self.org_repo.get_member(org_id, user.id)
        if not member or not member.is_active:
            raise ForbiddenError(
                message="You do not have access to this organization",
                code="ORGANIZATION_ACCESS_DENIED"
            )
        return member.role

    async def upload_file(
        self,
        org_id: int,
        file: UploadFile,
        user: User,
        project_id: Optional[int] = None,
        task_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> AttachmentResponse:
        role = self._verify_org_access(org_id, user)
        if role == OrganizationRole.VIEWER:
            raise ForbiddenError(message="Viewers cannot upload files", code="INSUFFICIENT_PERMISSIONS")

        if not project_id and not task_id:
            raise BadRequestError(
                message="Either project_id or task_id must be provided for file upload",
                code="MISSING_TARGET"
            )

        # Validate task and project
        if task_id:
            task = self.task_repo.get_by_id_and_org(task_id, org_id)
            if not task:
                raise NotFoundError(message="Task not found in this organization", code="TASK_NOT_FOUND")
            project_id = task.project_id
        elif project_id:
            project = self.project_repo.get_by_id_and_org(project_id, org_id)
            if not project:
                raise NotFoundError(message="Project not found in this organization", code="PROJECT_NOT_FOUND")

        # 1. Validate file extension
        filename = file.filename or "unknown"
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise BadRequestError(
                message=f"File extension '{ext}' is not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}",
                code="INVALID_FILE_EXTENSION"
            )

        # 2. Read content and validate file size
        content = await file.read()
        file_size = len(content)
        if file_size > settings.MAX_FILE_SIZE_BYTES:
            raise BadRequestError(
                message=f"File size exceeds limit of {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB",
                code="FILE_SIZE_EXCEEDED"
            )

        if file_size == 0:
            raise BadRequestError(message="Uploaded file is empty", code="EMPTY_FILE")

        # 3. Validate content against magic bytes (never trust extension alone)
        if not verify_file_content(content, ext):
            raise BadRequestError(
                message=f"Uploaded file content does not match the claimed file extension (.{ext})",
                code="INVALID_FILE_CONTENT"
            )

        # 4. Save to secure storage path
        org_dir = os.path.join(settings.UPLOAD_DIR, str(org_id))
        os.makedirs(org_dir, exist_ok=True)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        storage_path = os.path.join(org_dir, unique_filename)

        with open(storage_path, "wb") as f:
            f.write(content)

        attachment = Attachment(
            organization_id=org_id,
            uploaded_by=user.id,
            project_id=project_id,
            task_id=task_id,
            file_name=filename,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            storage_path=storage_path,
        )
        created_attachment = self.file_repo.create(attachment)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.FILE_UPLOADED.value,
            entity_type="Attachment",
            entity_id=created_attachment.id,
            user_id=user.id,
            ip_address=ip_address,
            details={"file_name": filename, "file_size": file_size}
        )

        resp = AttachmentResponse.model_validate(created_attachment)
        resp.download_url = f"/api/v1/files/{created_attachment.id}/download"
        return resp

    def get_file_metadata(self, org_id: int, file_id: int, user: User) -> AttachmentResponse:
        self._verify_org_access(org_id, user)
        att = self.file_repo.get_by_id_and_org(file_id, org_id)
        if not att:
            raise NotFoundError(message="File not found in this organization", code="FILE_NOT_FOUND")

        resp = AttachmentResponse.model_validate(att)
        resp.download_url = f"/api/v1/files/{att.id}/download"
        return resp

    def download_file(self, org_id: int, file_id: int, user: User) -> FileResponse:
        self._verify_org_access(org_id, user)
        att = self.file_repo.get_by_id_and_org(file_id, org_id)
        if not att:
            raise NotFoundError(message="File not found in this organization", code="FILE_NOT_FOUND")

        if not os.path.exists(att.storage_path):
            raise NotFoundError(message="Physical file not found on storage", code="FILE_STORAGE_MISSING")

        return FileResponse(
            path=att.storage_path,
            filename=att.file_name,
            media_type=att.mime_type
        )

    def list_files(
        self,
        org_id: int,
        user: User,
        task_id: Optional[int] = None,
        project_id: Optional[int] = None
    ) -> List[AttachmentResponse]:
        self._verify_org_access(org_id, user)
        if task_id:
            files = self.file_repo.list_by_task(task_id, org_id)
        elif project_id:
            files = self.file_repo.list_by_project(project_id, org_id)
        else:
            raise BadRequestError(message="Either task_id or project_id must be provided", code="MISSING_TARGET")

        result = []
        for f in files:
            resp = AttachmentResponse.model_validate(f)
            resp.download_url = f"/api/v1/files/{f.id}/download"
            result.append(resp)
        return result

    def delete_file(
        self,
        org_id: int,
        file_id: int,
        user: User,
        ip_address: Optional[str] = None
    ) -> bool:
        role = self._verify_org_access(org_id, user)
        att = self.file_repo.get_by_id_and_org(file_id, org_id)
        if not att:
            raise NotFoundError(message="File not found in this organization", code="FILE_NOT_FOUND")

        # Org Admin, Project Manager, or uploader can delete
        if role not in [OrganizationRole.ORGANIZATION_ADMIN, OrganizationRole.PROJECT_MANAGER] and att.uploaded_by != user.id:
            raise ForbiddenError(message="You do not have permission to delete this file", code="INSUFFICIENT_PERMISSIONS")

        if os.path.exists(att.storage_path):
            try:
                os.remove(att.storage_path)
            except Exception:
                pass

        self.file_repo.delete(att)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.FILE_DELETED.value,
            entity_type="Attachment",
            entity_id=file_id,
            user_id=user.id,
            ip_address=ip_address,
            details={"file_name": att.file_name}
        )
        return True
