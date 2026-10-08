from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.exceptions import ForbiddenError
from app.models.enums import OrganizationRole
from app.models.user import User
from app.repositories.audit_log_repo import AuditLogRepository
from app.repositories.organization_repo import OrganizationRepository
from app.schemas.audit_log import AuditLogResponse


class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_repo = AuditLogRepository(db)
        self.org_repo = OrganizationRepository(db)

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

    def list_logs(
        self,
        org_id: int,
        user: User,
        skip: int = 0,
        limit: int = 20,
        target_user_id: Optional[int] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> Tuple[List[AuditLogResponse], int]:
        role = self._verify_org_access(org_id, user)
        # Audit logs visible to Org Admin and Project Managers
        if role not in [OrganizationRole.ORGANIZATION_ADMIN, OrganizationRole.PROJECT_MANAGER]:
            raise ForbiddenError(
                message="Only Organization Admins and Project Managers can view audit logs",
                code="INSUFFICIENT_PERMISSIONS"
            )

        logs, total = self.audit_repo.list_logs(
            organization_id=org_id,
            skip=skip,
            limit=limit,
            user_id=target_user_id,
            action=action,
            entity_type=entity_type,
        )

        return [AuditLogResponse.model_validate(log) for log in logs], total
