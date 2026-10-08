from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.comment import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    def __init__(self, db: Session):
        super().__init__(Comment, db)

    def get_by_id_and_org(self, comment_id: int, organization_id: int) -> Optional[Comment]:
        return (
            self.db.query(Comment)
            .options(joinedload(Comment.user))
            .filter(Comment.id == comment_id, Comment.organization_id == organization_id)
            .first()
        )

    def list_by_task(self, task_id: int, organization_id: int) -> List[Comment]:
        return (
            self.db.query(Comment)
            .options(joinedload(Comment.user))
            .filter(Comment.task_id == task_id, Comment.organization_id == organization_id)
            .order_by(Comment.created_at.asc())
            .all()
        )

    def list_by_project(self, project_id: int, organization_id: int) -> List[Comment]:
        return (
            self.db.query(Comment)
            .options(joinedload(Comment.user))
            .filter(Comment.project_id == project_id, Comment.organization_id == organization_id)
            .order_by(Comment.created_at.asc())
            .all()
        )
