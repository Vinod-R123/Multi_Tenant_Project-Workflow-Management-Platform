from typing import Dict, List, Optional
from pydantic import BaseModel
from app.models.enums import OrganizationRole


class OrgAdminDashboardData(BaseModel):
    total_projects: int
    active_projects: int
    completed_projects: int
    total_users: int
    active_users: int
    total_tasks: int
    overdue_tasks: int


class ProjectManagerDashboardData(BaseModel):
    my_projects: int
    open_tasks: int
    completed_tasks: int
    overdue_tasks: int
    tasks_by_member: Dict[str, int]
    tasks_by_priority: Dict[str, int]


class TeamMemberDashboardData(BaseModel):
    my_tasks: int
    overdue_tasks: int
    tasks_due_today: int
    recently_completed_tasks: int


class DashboardResponse(BaseModel):
    role: OrganizationRole
    admin_metrics: Optional[OrgAdminDashboardData] = None
    pm_metrics: Optional[ProjectManagerDashboardData] = None
    member_metrics: Optional[TeamMemberDashboardData] = None
