from typing import List, Optional, Tuple
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db: Session):
        super().__init__(Project, db)

    def get_by_id_and_org(self, project_id: int, organization_id: int) -> Optional[Project]:
        return (
            self.db.query(Project)
            .options(joinedload(Project.owner))
            .filter(Project.id == project_id, Project.organization_id == organization_id)
            .first()
        )

    def list_by_org(
        self,
        organization_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[ProjectStatus] = None,
        search: Optional[str] = None,
        owner_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Tuple[List[Project], int]:
        query = (
            self.db.query(Project)
            .options(joinedload(Project.owner))
            .filter(Project.organization_id == organization_id)
        )

        if status:
            query = query.filter(Project.status == status)

        if owner_id:
            query = query.filter(Project.owner_id == owner_id)

        if search:
            search_fmt = f"%{search}%"
            query = query.filter(
                or_(
                    Project.name.ilike(search_fmt),
                    Project.description.ilike(search_fmt),
                )
            )

        if user_id:
            # If user_id provided (e.g. for Project Manager / Team Member view),
            # filter to projects owned by user or where user is in project_members
            query = query.outerjoin(ProjectMember, Project.id == ProjectMember.project_id).filter(
                or_(
                    Project.owner_id == user_id,
                    ProjectMember.user_id == user_id,
                )
            ).distinct()

        total = query.count()
        projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
        return projects, total

    def add_member(self, project_id: int, user_id: int) -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id)
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, project_id: int, user_id: int) -> bool:
        member = (
            self.db.query(ProjectMember)
            .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
            .first()
        )
        if member:
            self.db.delete(member)
            self.db.commit()
            return True
        return False

    def is_member(self, project_id: int, user_id: int) -> bool:
        return (
            self.db.query(ProjectMember)
            .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
            .first()
            is not None
        )

    def list_members(self, project_id: int) -> List[ProjectMember]:
        return (
            self.db.query(ProjectMember)
            .options(joinedload(ProjectMember.user))
            .filter(ProjectMember.project_id == project_id)
            .all()
        )

    def get_task_and_member_counts(self, project_id: int) -> Tuple[int, int]:
        member_count = (
            self.db.query(func.count(ProjectMember.id))
            .filter(ProjectMember.project_id == project_id)
            .scalar()
            or 0
        )
        task_count = (
            self.db.query(func.count(Task.id))
            .filter(Task.project_id == project_id)
            .scalar()
            or 0
        )
        return member_count, task_count
