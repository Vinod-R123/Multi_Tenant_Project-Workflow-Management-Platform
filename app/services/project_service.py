from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.enums import AuditAction, OrganizationRole, ProjectStatus
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.repositories.audit_log_repo import AuditLogRepository
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository
from app.schemas.project import (
    AddProjectMemberRequest,
    ProjectCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
)

# Valid Project Status Transitions map
VALID_PROJECT_TRANSITIONS = {
    ProjectStatus.PLANNING: {ProjectStatus.ACTIVE, ProjectStatus.ON_HOLD, ProjectStatus.ARCHIVED},
    ProjectStatus.ACTIVE: {ProjectStatus.ON_HOLD, ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED},
    ProjectStatus.ON_HOLD: {ProjectStatus.ACTIVE, ProjectStatus.ARCHIVED},
    ProjectStatus.COMPLETED: {ProjectStatus.ARCHIVED, ProjectStatus.ACTIVE},
    ProjectStatus.ARCHIVED: {ProjectStatus.ACTIVE},
}


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.user_repo = UserRepository(db)
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

    def create_project(
        self,
        org_id: int,
        req: ProjectCreate,
        user: User,
        ip_address: Optional[str] = None
    ) -> ProjectResponse:
        role = self._verify_org_access(org_id, user)
        # Org Admin and Project Manager can create projects
        if role not in [OrganizationRole.ORGANIZATION_ADMIN, OrganizationRole.PROJECT_MANAGER]:
            raise ForbiddenError(
                message="Only Organization Admins and Project Managers can create projects",
                code="INSUFFICIENT_PERMISSIONS"
            )

        project = Project(
            organization_id=org_id,
            owner_id=user.id,
            name=req.name,
            description=req.description,
            status=req.status or ProjectStatus.PLANNING,
            start_date=req.start_date,
            due_date=req.due_date,
        )
        created_project = self.project_repo.create(project)

        # Automatically add owner as project member
        self.project_repo.add_member(created_project.id, user.id)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.PROJECT_CREATED.value,
            entity_type="Project",
            entity_id=created_project.id,
            user_id=user.id,
            ip_address=ip_address,
            details={"name": created_project.name, "status": created_project.status.value}
        )

        resp = ProjectResponse.model_validate(created_project)
        resp.member_count = 1
        resp.task_count = 0
        return resp

    def get_project(self, org_id: int, project_id: int, user: User) -> ProjectResponse:
        self._verify_org_access(org_id, user)
        project = self.project_repo.get_by_id_and_org(project_id, org_id)
        if not project:
            raise NotFoundError(message="Project not found in this organization", code="PROJECT_NOT_FOUND")

        member_count, task_count = self.project_repo.get_task_and_member_counts(project_id)
        resp = ProjectResponse.model_validate(project)
        resp.member_count = member_count
        resp.task_count = task_count
        return resp

    def list_projects(
        self,
        org_id: int,
        user: User,
        skip: int = 0,
        limit: int = 20,
        status: Optional[ProjectStatus] = None,
        search: Optional[str] = None,
        owner_id: Optional[int] = None,
    ) -> Tuple[List[ProjectResponse], int]:
        role = self._verify_org_access(org_id, user)
        
        # If user is a Viewer or Team Member, we can let them see projects in org or projects they belong to
        # But per requirements, projects are org-isolated
        projects, total = self.project_repo.list_by_org(
            organization_id=org_id,
            skip=skip,
            limit=limit,
            status=status,
            search=search,
            owner_id=owner_id,
        )

        result: List[ProjectResponse] = []
        for p in projects:
            m_count, t_count = self.project_repo.get_task_and_member_counts(p.id)
            resp = ProjectResponse.model_validate(p)
            resp.member_count = m_count
            resp.task_count = t_count
            result.append(resp)

        return result, total

    def update_project(
        self,
        org_id: int,
        project_id: int,
        req: ProjectUpdate,
        user: User,
        ip_address: Optional[str] = None
    ) -> ProjectResponse:
        role = self._verify_org_access(org_id, user)
        project = self.project_repo.get_by_id_and_org(project_id, org_id)
        if not project:
            raise NotFoundError(message="Project not found", code="PROJECT_NOT_FOUND")

        # Permission check: Org Admin, or Project Owner, or Project Manager
        if role not in [OrganizationRole.ORGANIZATION_ADMIN, OrganizationRole.PROJECT_MANAGER] and project.owner_id != user.id:
            raise ForbiddenError(
                message="You do not have permission to update this project",
                code="INSUFFICIENT_PERMISSIONS"
            )

        # Validate status transition if status is being updated
        if req.status is not None and req.status != project.status:
            allowed = VALID_PROJECT_TRANSITIONS.get(project.status, set())
            if req.status not in allowed:
                raise BadRequestError(
                    message=f"Invalid status transition from {project.status.value} to {req.status.value}",
                    code="INVALID_PROJECT_STATUS_TRANSITION"
                )
            project.status = req.status

        if req.name is not None:
            project.name = req.name
        if req.description is not None:
            project.description = req.description
        if req.start_date is not None:
            project.start_date = req.start_date
        if req.due_date is not None:
            project.due_date = req.due_date

        updated_project = self.project_repo.update(project)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.PROJECT_UPDATED.value,
            entity_type="Project",
            entity_id=project_id,
            user_id=user.id,
            ip_address=ip_address,
            details=req.model_dump(exclude_unset=True)
        )

        member_count, task_count = self.project_repo.get_task_and_member_counts(project_id)
        resp = ProjectResponse.model_validate(updated_project)
        resp.member_count = member_count
        resp.task_count = task_count
        return resp

    def archive_project(
        self,
        org_id: int,
        project_id: int,
        user: User,
        ip_address: Optional[str] = None
    ) -> ProjectResponse:
        role = self._verify_org_access(org_id, user)
        project = self.project_repo.get_by_id_and_org(project_id, org_id)
        if not project:
            raise NotFoundError(message="Project not found", code="PROJECT_NOT_FOUND")

        if role not in [OrganizationRole.ORGANIZATION_ADMIN, OrganizationRole.PROJECT_MANAGER] and project.owner_id != user.id:
            raise ForbiddenError(
                message="You do not have permission to archive this project",
                code="INSUFFICIENT_PERMISSIONS"
            )

        allowed = VALID_PROJECT_TRANSITIONS.get(project.status, set())
        if ProjectStatus.ARCHIVED not in allowed:
            raise BadRequestError(
                message=f"Cannot archive project from status {project.status.value}",
                code="INVALID_PROJECT_STATUS_TRANSITION"
            )

        project.status = ProjectStatus.ARCHIVED
        updated = self.project_repo.update(project)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.PROJECT_ARCHIVED.value,
            entity_type="Project",
            entity_id=project_id,
            user_id=user.id,
            ip_address=ip_address
        )

        member_count, task_count = self.project_repo.get_task_and_member_counts(project_id)
        resp = ProjectResponse.model_validate(updated)
        resp.member_count = member_count
        resp.task_count = task_count
        return resp

    def delete_project(
        self,
        org_id: int,
        project_id: int,
        user: User,
        ip_address: Optional[str] = None
    ) -> bool:
        role = self._verify_org_access(org_id, user)
        project = self.project_repo.get_by_id_and_org(project_id, org_id)
        if not project:
            raise NotFoundError(message="Project not found", code="PROJECT_NOT_FOUND")

        # Deleting project permitted ONLY to Org Admin or Project Owner
        if role != OrganizationRole.ORGANIZATION_ADMIN and project.owner_id != user.id:
            raise ForbiddenError(
                message="Only Organization Admins or Project Owners can delete projects",
                code="INSUFFICIENT_PERMISSIONS"
            )

        self.project_repo.delete(project)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.PROJECT_DELETED.value,
            entity_type="Project",
            entity_id=project_id,
            user_id=user.id,
            ip_address=ip_address
        )
        return True

    def add_project_member(
        self,
        org_id: int,
        project_id: int,
        req: AddProjectMemberRequest,
        actor_user: User,
        ip_address: Optional[str] = None
    ) -> ProjectMemberResponse:
        role = self._verify_org_access(org_id, actor_user)
        project = self.project_repo.get_by_id_and_org(project_id, org_id)
        if not project:
            raise NotFoundError(message="Project not found", code="PROJECT_NOT_FOUND")

        if role not in [OrganizationRole.ORGANIZATION_ADMIN, OrganizationRole.PROJECT_MANAGER] and project.owner_id != actor_user.id:
            raise ForbiddenError(
                message="Only Org Admins or Project Managers can add project members",
                code="INSUFFICIENT_PERMISSIONS"
            )

        # Target user MUST be an active member of the organization
        target_org_member = self.org_repo.get_member(org_id, req.user_id)
        if not target_org_member or not target_org_member.is_active:
            raise BadRequestError(
                message="User must be an active member of the organization before joining a project",
                code="USER_NOT_IN_ORGANIZATION"
            )

        # Check if already a project member
        if self.project_repo.is_member(project_id, req.user_id):
            raise ConflictError(
                message="User is already a member of this project",
                code="DUPLICATE_PROJECT_MEMBERSHIP"
            )

        member = self.project_repo.add_member(project_id, req.user_id)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.PROJECT_MEMBER_ADDED.value,
            entity_type="ProjectMember",
            entity_id=member.id,
            user_id=actor_user.id,
            ip_address=ip_address,
            details={"project_id": project_id, "user_id": req.user_id}
        )

        return ProjectMemberResponse.model_validate(member)

    def remove_project_member(
        self,
        org_id: int,
        project_id: int,
        target_user_id: int,
        actor_user: User,
        ip_address: Optional[str] = None
    ) -> bool:
        role = self._verify_org_access(org_id, actor_user)
        project = self.project_repo.get_by_id_and_org(project_id, org_id)
        if not project:
            raise NotFoundError(message="Project not found", code="PROJECT_NOT_FOUND")

        if role not in [OrganizationRole.ORGANIZATION_ADMIN, OrganizationRole.PROJECT_MANAGER] and project.owner_id != actor_user.id:
            raise ForbiddenError(
                message="Only Org Admins or Project Managers can remove project members",
                code="INSUFFICIENT_PERMISSIONS"
            )

        if target_user_id == project.owner_id:
            raise BadRequestError(
                message="Cannot remove project owner from project members",
                code="CANNOT_REMOVE_PROJECT_OWNER"
            )

        success = self.project_repo.remove_member(project_id, target_user_id)
        if not success:
            raise NotFoundError(message="User is not a member of this project", code="MEMBER_NOT_FOUND")

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.PROJECT_MEMBER_REMOVED.value,
            entity_type="ProjectMember",
            entity_id=project_id,
            user_id=actor_user.id,
            ip_address=ip_address,
            details={"target_user_id": target_user_id}
        )
        return True

    def list_project_members(
        self,
        org_id: int,
        project_id: int,
        user: User
    ) -> List[ProjectMemberResponse]:
        self._verify_org_access(org_id, user)
        project = self.project_repo.get_by_id_and_org(project_id, org_id)
        if not project:
            raise NotFoundError(message="Project not found", code="PROJECT_NOT_FOUND")

        members = self.project_repo.list_members(project_id)
        return [ProjectMemberResponse.model_validate(m) for m in members]
