from typing import List, Optional, Tuple
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from app.models.enums import TaskPriority, TaskStatus
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, db: Session):
        super().__init__(Task, db)

    def get_by_id_and_org(self, task_id: int, organization_id: int) -> Optional[Task]:
        return (
            self.db.query(Task)
            .options(
                joinedload(Task.assignee),
                joinedload(Task.reporter),
                joinedload(Task.project),
                joinedload(Task.prerequisites).joinedload(TaskDependency.prerequisite_task),
                joinedload(Task.dependents).joinedload(TaskDependency.dependent_task),
            )
            .filter(Task.id == task_id, Task.organization_id == organization_id)
            .first()
        )

    def list_by_org(
        self,
        organization_id: int,
        skip: int = 0,
        limit: int = 20,
        project_id: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        assignee_id: Optional[int] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Task], int]:
        query = (
            self.db.query(Task)
            .options(
                joinedload(Task.assignee),
                joinedload(Task.reporter),
                joinedload(Task.project),
                joinedload(Task.prerequisites).joinedload(TaskDependency.prerequisite_task),
                joinedload(Task.dependents).joinedload(TaskDependency.dependent_task),
            )
            .filter(Task.organization_id == organization_id)
        )

        if project_id:
            query = query.filter(Task.project_id == project_id)

        if status:
            query = query.filter(Task.status == status)

        if priority:
            query = query.filter(Task.priority == priority)

        if assignee_id:
            query = query.filter(Task.assignee_id == assignee_id)

        if search:
            search_fmt = f"%{search}%"
            query = query.filter(
                or_(
                    Task.title.ilike(search_fmt),
                    Task.description.ilike(search_fmt),
                )
            )

        total = query.count()

        # Sorting
        sort_col = getattr(Task, sort_by, Task.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        tasks = query.offset(skip).limit(limit).all()
        return tasks, total

    def add_dependency(self, task_id: int, depends_on_task_id: int) -> TaskDependency:
        dep = TaskDependency(task_id=task_id, depends_on_task_id=depends_on_task_id)
        self.db.add(dep)
        self.db.commit()
        self.db.refresh(dep)
        return dep

    def remove_dependency(self, dependency_id: int, task_id: int) -> bool:
        dep = (
            self.db.query(TaskDependency)
            .filter(TaskDependency.id == dependency_id, TaskDependency.task_id == task_id)
            .first()
        )
        if dep:
            self.db.delete(dep)
            self.db.commit()
            return True
        return False

    def get_dependency(self, task_id: int, depends_on_task_id: int) -> Optional[TaskDependency]:
        return (
            self.db.query(TaskDependency)
            .filter(
                TaskDependency.task_id == task_id,
                TaskDependency.depends_on_task_id == depends_on_task_id,
            )
            .first()
        )

    def get_project_dependencies(self, project_id: int) -> List[Tuple[int, int]]:
        """Returns list of (task_id, depends_on_task_id) for cycle detection within a project"""
        query = (
            self.db.query(TaskDependency.task_id, TaskDependency.depends_on_task_id)
            .join(Task, TaskDependency.task_id == Task.id)
            .filter(Task.project_id == project_id)
        )
        return [(row[0], row[1]) for row in query.all()]

    def get_unresolved_prerequisites(self, task_id: int) -> List[Task]:
        """Finds prerequisite tasks that are NOT DONE"""
        return (
            self.db.query(Task)
            .join(TaskDependency, Task.id == TaskDependency.depends_on_task_id)
            .filter(
                TaskDependency.task_id == task_id,
                Task.status != TaskStatus.DONE,
            )
            .all()
        )
