from datetime import datetime, timezone, timedelta
from typing import Dict
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.core.exceptions import ForbiddenError
from app.models.enums import OrganizationRole, ProjectStatus, TaskPriority, TaskStatus
from app.models.organization_member import OrganizationMember
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.repositories.organization_repo import OrganizationRepository
from app.schemas.dashboard import (
    DashboardResponse,
    OrgAdminDashboardData,
    ProjectManagerDashboardData,
    TeamMemberDashboardData,
)


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
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

    def get_dashboard_metrics(self, org_id: int, user: User) -> DashboardResponse:
        role = self._verify_org_access(org_id, user)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        admin_data = None
        pm_data = None
        member_data = None

        if role == OrganizationRole.ORGANIZATION_ADMIN:
            # Org Admin view
            total_projects = self.db.query(func.count(Project.id)).filter(Project.organization_id == org_id).scalar() or 0
            active_projects = self.db.query(func.count(Project.id)).filter(
                Project.organization_id == org_id,
                Project.status == ProjectStatus.ACTIVE
            ).scalar() or 0
            completed_projects = self.db.query(func.count(Project.id)).filter(
                Project.organization_id == org_id,
                Project.status == ProjectStatus.COMPLETED
            ).scalar() or 0

            total_users = self.db.query(func.count(OrganizationMember.id)).filter(
                OrganizationMember.organization_id == org_id
            ).scalar() or 0
            active_users = self.db.query(func.count(OrganizationMember.id)).filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.is_active == True
            ).scalar() or 0

            total_tasks = self.db.query(func.count(Task.id)).filter(Task.organization_id == org_id).scalar() or 0
            overdue_tasks = self.db.query(func.count(Task.id)).filter(
                Task.organization_id == org_id,
                Task.due_date < now,
                Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED])
            ).scalar() or 0

            admin_data = OrgAdminDashboardData(
                total_projects=total_projects,
                active_projects=active_projects,
                completed_projects=completed_projects,
                total_users=total_users,
                active_users=active_users,
                total_tasks=total_tasks,
                overdue_tasks=overdue_tasks,
            )

        if role in [OrganizationRole.ORGANIZATION_ADMIN, OrganizationRole.PROJECT_MANAGER]:
            # Project Manager view (either for PM role or Admin inspecting PM view)
            pm_project_ids = [
                row[0] for row in (
                    self.db.query(Project.id)
                    .outerjoin(ProjectMember, Project.id == ProjectMember.project_id)
                    .filter(
                        Project.organization_id == org_id,
                        or_(Project.owner_id == user.id, ProjectMember.user_id == user.id)
                    )
                    .distinct()
                    .all()
                )
            ]
            my_projects_count = len(pm_project_ids)

            open_tasks = 0
            completed_tasks = 0
            overdue_tasks_pm = 0
            tasks_by_member: Dict[str, int] = {}
            tasks_by_priority: Dict[str, int] = {}

            if pm_project_ids:
                open_tasks = self.db.query(func.count(Task.id)).filter(
                    Task.project_id.in_(pm_project_ids),
                    Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED])
                ).scalar() or 0

                completed_tasks = self.db.query(func.count(Task.id)).filter(
                    Task.project_id.in_(pm_project_ids),
                    Task.status == TaskStatus.DONE
                ).scalar() or 0

                overdue_tasks_pm = self.db.query(func.count(Task.id)).filter(
                    Task.project_id.in_(pm_project_ids),
                    Task.due_date < now,
                    Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED])
                ).scalar() or 0

                # Breakdown by member
                member_breakdown = (
                    self.db.query(User.username, func.count(Task.id))
                    .join(Task, User.id == Task.assignee_id)
                    .filter(Task.project_id.in_(pm_project_ids))
                    .group_by(User.username)
                    .all()
                )
                tasks_by_member = {uname: count for uname, count in member_breakdown}

                # Breakdown by priority
                priority_breakdown = (
                    self.db.query(Task.priority, func.count(Task.id))
                    .filter(Task.project_id.in_(pm_project_ids))
                    .group_by(Task.priority)
                    .all()
                )
                tasks_by_priority = {str(p.value): count for p, count in priority_breakdown}

            pm_data = ProjectManagerDashboardData(
                my_projects=my_projects_count,
                open_tasks=open_tasks,
                completed_tasks=completed_tasks,
                overdue_tasks=overdue_tasks_pm,
                tasks_by_member=tasks_by_member,
                tasks_by_priority=tasks_by_priority,
            )

        # Team Member view
        my_tasks = self.db.query(func.count(Task.id)).filter(
            Task.organization_id == org_id,
            Task.assignee_id == user.id,
            Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED])
        ).scalar() or 0

        overdue_my_tasks = self.db.query(func.count(Task.id)).filter(
            Task.organization_id == org_id,
            Task.assignee_id == user.id,
            Task.due_date < now,
            Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED])
        ).scalar() or 0

        tasks_due_today = self.db.query(func.count(Task.id)).filter(
            Task.organization_id == org_id,
            Task.assignee_id == user.id,
            Task.due_date >= today_start,
            Task.due_date < today_end,
            Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED])
        ).scalar() or 0

        recently_completed = self.db.query(func.count(Task.id)).filter(
            Task.organization_id == org_id,
            Task.assignee_id == user.id,
            Task.status == TaskStatus.DONE,
            Task.updated_at >= (now - timedelta(days=7))
        ).scalar() or 0

        member_data = TeamMemberDashboardData(
            my_tasks=my_tasks,
            overdue_tasks=overdue_my_tasks,
            tasks_due_today=tasks_due_today,
            recently_completed_tasks=recently_completed,
        )

        return DashboardResponse(
            role=role,
            admin_metrics=admin_data,
            pm_metrics=pm_data,
            member_metrics=member_data,
        )
