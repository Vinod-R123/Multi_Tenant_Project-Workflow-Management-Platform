from collections import defaultdict, deque
from typing import List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.models.enums import (
    AuditAction,
    NotificationEventType,
    OrganizationRole,
    TaskPriority,
    TaskStatus,
)
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.models.user import User
from app.repositories.audit_log_repo import AuditLogRepository
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.task_repo import TaskRepository
from app.schemas.task import (
    AddDependencyRequest,
    TaskCreate,
    TaskDependencyResponse,
    TaskFilterParams,
    TaskPriorityUpdate,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.notification_service import NotificationService

VALID_TASK_TRANSITIONS = {
    TaskStatus.BACKLOG: {TaskStatus.TODO, TaskStatus.CANCELLED},
    TaskStatus.TODO: {TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {TaskStatus.REVIEW, TaskStatus.BLOCKED, TaskStatus.TODO, TaskStatus.CANCELLED},
    TaskStatus.BLOCKED: {TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.REVIEW: {TaskStatus.DONE, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
    TaskStatus.DONE: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.CANCELLED: {TaskStatus.BACKLOG, TaskStatus.TODO},
}


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.task_repo = TaskRepository(db)
        self.project_repo = ProjectRepository(db)
        self.org_repo = OrganizationRepository(db)
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

    def _validate_assignee(self, org_id: int, project_id: int, assignee_id: Optional[int]) -> None:
        if assignee_id is None:
            return

        # 1. Must be in organization
        org_member = self.org_repo.get_member(org_id, assignee_id)
        if not org_member or not org_member.is_active:
            raise BadRequestError(
                message="Assignee is not an active member of this organization",
                code="INVALID_ASSIGNEE_ORGANIZATION"
            )

        # 2. Viewers cannot receive tasks
        if org_member.role == OrganizationRole.VIEWER:
            raise BadRequestError(
                message="Viewers cannot be assigned tasks",
                code="VIEWER_ASSIGNMENT_FORBIDDEN"
            )

        # 3. Must be project member
        if not self.project_repo.is_member(project_id, assignee_id):
            raise BadRequestError(
                message="Assignee must be a member of the project",
                code="ASSIGNEE_NOT_PROJECT_MEMBER"
            )

    def create_task(
        self,
        org_id: int,
        req: TaskCreate,
        user: User,
        ip_address: Optional[str] = None
    ) -> TaskResponse:
        role = self._verify_org_access(org_id, user)
        if role == OrganizationRole.VIEWER:
            raise ForbiddenError(message="Viewers cannot create tasks", code="INSUFFICIENT_PERMISSIONS")

        # Project must exist in this org
        project = self.project_repo.get_by_id_and_org(req.project_id, org_id)
        if not project:
            raise NotFoundError(message="Project not found in this organization", code="PROJECT_NOT_FOUND")

        # Validate assignee
        self._validate_assignee(org_id, req.project_id, req.assignee_id)

        task = Task(
            organization_id=org_id,
            project_id=req.project_id,
            title=req.title,
            description=req.description,
            assignee_id=req.assignee_id,
            reporter_id=user.id,
            priority=req.priority or TaskPriority.MEDIUM,
            status=TaskStatus.TODO,
            due_date=req.due_date,
            estimated_hours=req.estimated_hours,
        )
        created_task = self.task_repo.create(task)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.TASK_CREATED.value,
            entity_type="Task",
            entity_id=created_task.id,
            user_id=user.id,
            ip_address=ip_address,
            details={"title": created_task.title, "project_id": req.project_id}
        )

        # Notify assignee if assigned
        if req.assignee_id and req.assignee_id != user.id:
            self.notif_service.create_notification(
                organization_id=org_id,
                user_id=req.assignee_id,
                event_type=NotificationEventType.TASK_ASSIGNED.value,
                title="New Task Assigned",
                message=f"You were assigned to task: '{created_task.title}'",
                entity_type="Task",
                entity_id=created_task.id,
            )

        return self._format_task_response(created_task)

    def get_task(self, org_id: int, task_id: int, user: User) -> TaskResponse:
        self._verify_org_access(org_id, user)
        task = self.task_repo.get_by_id_and_org(task_id, org_id)
        if not task:
            raise NotFoundError(message="Task not found in this organization", code="TASK_NOT_FOUND")
        return self._format_task_response(task)

    def list_tasks(
        self,
        org_id: int,
        user: User,
        skip: int = 0,
        limit: int = 20,
        filters: Optional[TaskFilterParams] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[TaskResponse], int]:
        self._verify_org_access(org_id, user)
        project_id = filters.project_id if filters else None
        status = filters.status if filters else None
        priority = filters.priority if filters else None
        assignee_id = filters.assignee_id if filters else None
        search = filters.search if filters else None

        tasks, total = self.task_repo.list_by_org(
            organization_id=org_id,
            skip=skip,
            limit=limit,
            project_id=project_id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return [self._format_task_response(t) for t in tasks], total

    def update_task(
        self,
        org_id: int,
        task_id: int,
        req: TaskUpdate,
        user: User,
        ip_address: Optional[str] = None
    ) -> TaskResponse:
        role = self._verify_org_access(org_id, user)
        if role == OrganizationRole.VIEWER:
            raise ForbiddenError(message="Viewers cannot edit tasks", code="INSUFFICIENT_PERMISSIONS")

        task = self.task_repo.get_by_id_and_org(task_id, org_id)
        if not task:
            raise NotFoundError(message="Task not found", code="TASK_NOT_FOUND")

        # Team member can only edit task if they are assignee or reporter
        if role == OrganizationRole.TEAM_MEMBER and task.assignee_id != user.id and task.reporter_id != user.id:
            raise ForbiddenError(message="Team members can only edit tasks assigned to or reported by them", code="INSUFFICIENT_PERMISSIONS")

        if req.title is not None:
            task.title = req.title
        if req.description is not None:
            task.description = req.description
        if req.priority is not None:
            task.priority = req.priority
        if req.due_date is not None:
            task.due_date = req.due_date
        if req.estimated_hours is not None:
            task.estimated_hours = req.estimated_hours
        if req.actual_hours is not None:
            task.actual_hours = req.actual_hours

        updated_task = self.task_repo.update(task)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.TASK_UPDATED.value,
            entity_type="Task",
            entity_id=task_id,
            user_id=user.id,
            ip_address=ip_address,
            details=req.model_dump(exclude_unset=True)
        )

        return self._format_task_response(updated_task)

    def change_status(
        self,
        org_id: int,
        task_id: int,
        req: TaskStatusUpdate,
        user: User,
        ip_address: Optional[str] = None
    ) -> TaskResponse:
        role = self._verify_org_access(org_id, user)
        if role == OrganizationRole.VIEWER:
            raise ForbiddenError(message="Viewers cannot change task status", code="INSUFFICIENT_PERMISSIONS")

        task = self.task_repo.get_by_id_and_org(task_id, org_id)
        if not task:
            raise NotFoundError(message="Task not found", code="TASK_NOT_FOUND")

        current_status = task.status
        new_status = req.status

        if current_status == new_status:
            return self._format_task_response(task)

        # 1. Check valid workflow transition
        allowed_transitions = VALID_TASK_TRANSITIONS.get(current_status, set())
        if new_status not in allowed_transitions:
            raise BadRequestError(
                message=f"Invalid task status transition from {current_status.value} to {new_status.value}",
                code="INVALID_TASK_STATUS_TRANSITION"
            )

        # 2. Task Dependency Gate:
        # Task cannot move to IN_PROGRESS, REVIEW, or DONE if prerequisite tasks are not DONE
        if new_status in [TaskStatus.IN_PROGRESS, TaskStatus.REVIEW, TaskStatus.DONE]:
            unresolved = self.task_repo.get_unresolved_prerequisites(task_id)
            if unresolved:
                unresolved_details = [
                    {"id": u.id, "title": u.title, "status": u.status.value}
                    for u in unresolved
                ]
                raise BadRequestError(
                    message=f"Cannot move task to {new_status.value} because {len(unresolved)} prerequisite task(s) are not completed",
                    code="UNRESOLVED_DEPENDENCY",
                    details=unresolved_details
                )

        old_status = task.status
        task.status = new_status
        updated_task = self.task_repo.update(task)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.TASK_STATUS_CHANGED.value,
            entity_type="Task",
            entity_id=task_id,
            user_id=user.id,
            ip_address=ip_address,
            details={"old_status": old_status.value, "new_status": new_status.value}
        )

        # Send notification to assignee and reporter
        recipients = {task.assignee_id, task.reporter_id} - {user.id, None}
        for r_id in recipients:
            self.notif_service.create_notification(
                organization_id=org_id,
                user_id=r_id,
                event_type=NotificationEventType.TASK_STATUS_CHANGED.value,
                title="Task Status Updated",
                message=f"Task '{task.title}' changed status from {old_status.value} to {new_status.value}",
                entity_type="Task",
                entity_id=task.id,
            )

        return self._format_task_response(updated_task)

    def assign_task(
        self,
        org_id: int,
        task_id: int,
        assignee_id: Optional[int],
        actor_user: User,
        ip_address: Optional[str] = None
    ) -> TaskResponse:
        role = self._verify_org_access(org_id, actor_user)
        # Only Org Admin or Project Manager can assign tasks
        if role not in [OrganizationRole.ORGANIZATION_ADMIN, OrganizationRole.PROJECT_MANAGER]:
            raise ForbiddenError(
                message="Only Organization Admins and Project Managers can assign tasks",
                code="INSUFFICIENT_PERMISSIONS"
            )

        task = self.task_repo.get_by_id_and_org(task_id, org_id)
        if not task:
            raise NotFoundError(message="Task not found", code="TASK_NOT_FOUND")

        # Validate assignee
        self._validate_assignee(org_id, task.project_id, assignee_id)

        old_assignee_id = task.assignee_id
        task.assignee_id = assignee_id
        updated_task = self.task_repo.update(task)

        action = AuditAction.TASK_REASSIGNED.value if old_assignee_id else AuditAction.TASK_ASSIGNED.value
        self.audit_repo.log(
            organization_id=org_id,
            action=action,
            entity_type="Task",
            entity_id=task_id,
            user_id=actor_user.id,
            ip_address=ip_address,
            details={"old_assignee_id": old_assignee_id, "new_assignee_id": assignee_id}
        )

        if assignee_id and assignee_id != actor_user.id:
            self.notif_service.create_notification(
                organization_id=org_id,
                user_id=assignee_id,
                event_type=NotificationEventType.TASK_ASSIGNED.value,
                title="Task Assigned",
                message=f"You were assigned to task: '{task.title}'",
                entity_type="Task",
                entity_id=task.id,
            )

        return self._format_task_response(updated_task)

    def change_priority(
        self,
        org_id: int,
        task_id: int,
        priority: TaskPriority,
        user: User,
        ip_address: Optional[str] = None
    ) -> TaskResponse:
        role = self._verify_org_access(org_id, user)
        if role == OrganizationRole.VIEWER:
            raise ForbiddenError(message="Viewers cannot change priority", code="INSUFFICIENT_PERMISSIONS")

        task = self.task_repo.get_by_id_and_org(task_id, org_id)
        if not task:
            raise NotFoundError(message="Task not found", code="TASK_NOT_FOUND")

        old_priority = task.priority
        task.priority = priority
        updated_task = self.task_repo.update(task)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.TASK_UPDATED.value,
            entity_type="Task",
            entity_id=task_id,
            user_id=user.id,
            ip_address=ip_address,
            details={"field": "priority", "old": old_priority.value, "new": priority.value}
        )

        return self._format_task_response(updated_task)

    def delete_task(
        self,
        org_id: int,
        task_id: int,
        user: User,
        ip_address: Optional[str] = None
    ) -> bool:
        role = self._verify_org_access(org_id, user)
        task = self.task_repo.get_by_id_and_org(task_id, org_id)
        if not task:
            raise NotFoundError(message="Task not found", code="TASK_NOT_FOUND")

        # Org Admin, Project Manager, or reporter can delete
        if role not in [OrganizationRole.ORGANIZATION_ADMIN, OrganizationRole.PROJECT_MANAGER] and task.reporter_id != user.id:
            raise ForbiddenError(message="You do not have permission to delete this task", code="INSUFFICIENT_PERMISSIONS")

        self.task_repo.delete(task)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.TASK_DELETED.value,
            entity_type="Task",
            entity_id=task_id,
            user_id=user.id,
            ip_address=ip_address,
            details={"title": task.title}
        )
        return True

    def add_dependency(
        self,
        org_id: int,
        task_id: int,
        req: AddDependencyRequest,
        user: User,
        ip_address: Optional[str] = None
    ) -> TaskDependencyResponse:
        role = self._verify_org_access(org_id, user)
        if role == OrganizationRole.VIEWER:
            raise ForbiddenError(message="Viewers cannot add dependencies", code="INSUFFICIENT_PERMISSIONS")

        # 1. Check self dependency
        if task_id == req.depends_on_task_id:
            raise BadRequestError(
                message="A task cannot depend on itself",
                code="SELF_DEPENDENCY_FORBIDDEN"
            )

        # 2. Fetch both tasks in same organization
        task = self.task_repo.get_by_id_and_org(task_id, org_id)
        if not task:
            raise NotFoundError(message="Dependent task not found", code="TASK_NOT_FOUND")

        prerequisite = self.task_repo.get_by_id_and_org(req.depends_on_task_id, org_id)
        if not prerequisite:
            raise NotFoundError(message="Prerequisite task not found", code="TASK_NOT_FOUND")

        # Must belong to same project
        if task.project_id != prerequisite.project_id:
            raise BadRequestError(
                message="Dependencies can only be created between tasks in the same project",
                code="CROSS_PROJECT_DEPENDENCY_FORBIDDEN"
            )

        # 3. Check existing dependency
        existing = self.task_repo.get_dependency(task_id, req.depends_on_task_id)
        if existing:
            raise ConflictError(message="This dependency already exists", code="DUPLICATE_DEPENDENCY")

        # 4. Cycle Detection using DFS
        # We want to add edge: task_id depends on req.depends_on_task_id (task_id -> prerequisite)
        # A cycle is created if there is ALREADY a path from prerequisite to task_id:
        # i.e., prerequisite directly or indirectly depends on task_id.
        existing_dependencies = self.task_repo.get_project_dependencies(task.project_id)
        adj: defaultdict[int, List[int]] = defaultdict(list)
        for u, v in existing_dependencies:
            adj[u].append(v)

        # Check if req.depends_on_task_id can reach task_id
        if self._path_exists(adj, start=req.depends_on_task_id, target=task_id):
            raise BadRequestError(
                message=f"Circular dependency detected: Task {req.depends_on_task_id} already directly or indirectly depends on Task {task_id}",
                code="CIRCULAR_DEPENDENCY_DETECTED"
            )

        dep = self.task_repo.add_dependency(task_id, req.depends_on_task_id)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.TASK_DEPENDENCY_ADDED.value,
            entity_type="TaskDependency",
            entity_id=dep.id,
            user_id=user.id,
            ip_address=ip_address,
            details={"task_id": task_id, "depends_on_task_id": req.depends_on_task_id}
        )

        return TaskDependencyResponse(
            id=dep.id,
            task_id=dep.task_id,
            depends_on_task_id=dep.depends_on_task_id,
            created_at=dep.created_at,
            prerequisite_title=prerequisite.title,
            prerequisite_status=prerequisite.status,
        )

    def remove_dependency(
        self,
        org_id: int,
        task_id: int,
        dependency_id: int,
        user: User,
        ip_address: Optional[str] = None
    ) -> bool:
        role = self._verify_org_access(org_id, user)
        if role == OrganizationRole.VIEWER:
            raise ForbiddenError(message="Viewers cannot remove dependencies", code="INSUFFICIENT_PERMISSIONS")

        task = self.task_repo.get_by_id_and_org(task_id, org_id)
        if not task:
            raise NotFoundError(message="Task not found", code="TASK_NOT_FOUND")

        success = self.task_repo.remove_dependency(dependency_id, task_id)
        if not success:
            raise NotFoundError(message="Dependency not found", code="DEPENDENCY_NOT_FOUND")

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.TASK_DEPENDENCY_REMOVED.value,
            entity_type="TaskDependency",
            entity_id=dependency_id,
            user_id=user.id,
            ip_address=ip_address,
            details={"task_id": task_id}
        )
        return True

    def list_dependencies(self, org_id: int, task_id: int, user: User) -> List[TaskDependencyResponse]:
        self._verify_org_access(org_id, user)
        task = self.task_repo.get_by_id_and_org(task_id, org_id)
        if not task:
            raise NotFoundError(message="Task not found", code="TASK_NOT_FOUND")

        result = []
        for p in task.prerequisites:
            result.append(
                TaskDependencyResponse(
                    id=p.id,
                    task_id=p.task_id,
                    depends_on_task_id=p.depends_on_task_id,
                    created_at=p.created_at,
                    prerequisite_title=p.prerequisite_task.title if p.prerequisite_task else None,
                    prerequisite_status=p.prerequisite_task.status if p.prerequisite_task else None,
                )
            )
        return result

    def _path_exists(self, adj: defaultdict[int, List[int]], start: int, target: int) -> bool:
        visited: Set[int] = set()
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if node == target:
                return True
            if node in visited:
                continue
            visited.add(node)
            for neighbor in adj[node]:
                if neighbor not in visited:
                    queue.append(neighbor)
        return False

    def _format_task_response(self, task: Task) -> TaskResponse:
        prereqs = [
            TaskDependencyResponse(
                id=p.id,
                task_id=p.task_id,
                depends_on_task_id=p.depends_on_task_id,
                created_at=p.created_at,
                prerequisite_title=p.prerequisite_task.title if p.prerequisite_task else None,
                prerequisite_status=p.prerequisite_task.status if p.prerequisite_task else None,
            )
            for p in task.prerequisites
        ]
        dependents = [
            TaskDependencyResponse(
                id=d.id,
                task_id=d.task_id,
                depends_on_task_id=d.depends_on_task_id,
                created_at=d.created_at,
                prerequisite_title=d.dependent_task.title if d.dependent_task else None,
                prerequisite_status=d.dependent_task.status if d.dependent_task else None,
            )
            for d in task.dependents
        ]

        resp = TaskResponse.model_validate(task)
        resp.project_name = task.project.name if task.project else None
        resp.prerequisites = prereqs
        resp.dependents = dependents
        return resp
