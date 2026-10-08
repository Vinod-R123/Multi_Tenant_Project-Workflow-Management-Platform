import re
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models.comment import Comment
from app.models.enums import AuditAction, NotificationEventType, OrganizationRole
from app.models.user import User
from app.repositories.audit_log_repo import AuditLogRepository
from app.repositories.comment_repo import CommentRepository
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.task_repo import TaskRepository
from app.repositories.user_repo import UserRepository
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.services.notification_service import NotificationService


class CommentService:
    def __init__(self, db: Session):
        self.db = db
        self.comment_repo = CommentRepository(db)
        self.task_repo = TaskRepository(db)
        self.project_repo = ProjectRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditLogRepository(db)
        self.notif_service = NotificationService(db)

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

    def create_comment(
        self,
        org_id: int,
        req: CommentCreate,
        user: User,
        ip_address: Optional[str] = None
    ) -> CommentResponse:
        role = self._verify_org_access(org_id, user)
        if role == OrganizationRole.VIEWER:
            raise ForbiddenError(message="Viewers cannot create comments", code="INSUFFICIENT_PERMISSIONS")

        if not req.project_id and not req.task_id:
            raise BadRequestError(
                message="Either project_id or task_id must be provided for a comment",
                code="MISSING_COMMENT_TARGET"
            )

        task = None
        project = None
        if req.task_id:
            task = self.task_repo.get_by_id_and_org(req.task_id, org_id)
            if not task:
                raise NotFoundError(message="Task not found in this organization", code="TASK_NOT_FOUND")
            # Set project_id if not supplied
            req.project_id = task.project_id
        elif req.project_id:
            project = self.project_repo.get_by_id_and_org(req.project_id, org_id)
            if not project:
                raise NotFoundError(message="Project not found in this organization", code="PROJECT_NOT_FOUND")

        comment = Comment(
            organization_id=org_id,
            user_id=user.id,
            project_id=req.project_id,
            task_id=req.task_id,
            content=req.content,
        )
        created_comment = self.comment_repo.create(comment)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.COMMENT_CREATED.value,
            entity_type="Comment",
            entity_id=created_comment.id,
            user_id=user.id,
            ip_address=ip_address,
            details={"task_id": req.task_id, "project_id": req.project_id}
        )

        # 1. Parse @username mentions
        mentioned_usernames = set(re.findall(r"@([a-zA-Z0-9_\.\-]+)", req.content))
        target_name = f"task '{task.title}'" if task else f"project '{project.name}'" if project else "item"

        for uname in mentioned_usernames:
            mentioned_user = self.user_repo.get_by_username(uname)
            if mentioned_user and mentioned_user.id != user.id:
                # Check mentioned user belongs to organization
                m_member = self.org_repo.get_member(org_id, mentioned_user.id)
                if m_member and m_member.is_active:
                    self.notif_service.create_notification(
                        organization_id=org_id,
                        user_id=mentioned_user.id,
                        event_type=NotificationEventType.USER_MENTIONED.value,
                        title="You were mentioned",
                        message=f"{user.username} mentioned you in a comment on {target_name}",
                        entity_type="Comment",
                        entity_id=created_comment.id,
                    )

        # 2. General comment notification to task assignee & reporter
        if task:
            recipients = {task.assignee_id, task.reporter_id} - {user.id, None}
            for r_id in recipients:
                self.notif_service.create_notification(
                    organization_id=org_id,
                    user_id=r_id,
                    event_type=NotificationEventType.COMMENT_ADDED.value,
                    title="New Comment Added",
                    message=f"{user.username} commented on task '{task.title}'",
                    entity_type="Task",
                    entity_id=task.id,
                )

        return CommentResponse.model_validate(created_comment)

    def list_comments(
        self,
        org_id: int,
        user: User,
        task_id: Optional[int] = None,
        project_id: Optional[int] = None
    ) -> List[CommentResponse]:
        self._verify_org_access(org_id, user)
        if task_id:
            comments = self.comment_repo.list_by_task(task_id, org_id)
        elif project_id:
            comments = self.comment_repo.list_by_project(project_id, org_id)
        else:
            raise BadRequestError(message="Either task_id or project_id must be provided", code="MISSING_TARGET")

        return [CommentResponse.model_validate(c) for c in comments]

    def update_comment(
        self,
        org_id: int,
        comment_id: int,
        req: CommentUpdate,
        user: User,
        ip_address: Optional[str] = None
    ) -> CommentResponse:
        role = self._verify_org_access(org_id, user)
        comment = self.comment_repo.get_by_id_and_org(comment_id, org_id)
        if not comment:
            raise NotFoundError(message="Comment not found", code="COMMENT_NOT_FOUND")

        # Normal users can only edit their own comment; Org Admin can moderate
        if comment.user_id != user.id and role != OrganizationRole.ORGANIZATION_ADMIN:
            raise ForbiddenError(message="You can only edit your own comment", code="UNAUTHORIZED_COMMENT_MODIFICATION")

        comment.content = req.content
        updated_comment = self.comment_repo.update(comment)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.COMMENT_UPDATED.value,
            entity_type="Comment",
            entity_id=comment_id,
            user_id=user.id,
            ip_address=ip_address
        )

        return CommentResponse.model_validate(updated_comment)

    def delete_comment(
        self,
        org_id: int,
        comment_id: int,
        user: User,
        ip_address: Optional[str] = None
    ) -> bool:
        role = self._verify_org_access(org_id, user)
        comment = self.comment_repo.get_by_id_and_org(comment_id, org_id)
        if not comment:
            raise NotFoundError(message="Comment not found", code="COMMENT_NOT_FOUND")

        if comment.user_id != user.id and role != OrganizationRole.ORGANIZATION_ADMIN:
            raise ForbiddenError(message="You can only delete your own comment", code="UNAUTHORIZED_COMMENT_MODIFICATION")

        self.comment_repo.delete(comment)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.COMMENT_DELETED.value,
            entity_type="Comment",
            entity_id=comment_id,
            user_id=user.id,
            ip_address=ip_address
        )
        return True
