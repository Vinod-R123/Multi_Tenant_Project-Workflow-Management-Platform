from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.attachment import Attachment
from app.repositories.base import BaseRepository


class FileRepository(BaseRepository[Attachment]):
    def __init__(self, db: Session):
        super().__init__(Attachment, db)

    def get_by_id_and_org(self, attachment_id: int, organization_id: int) -> Optional[Attachment]:
        return (
            self.db.query(Attachment)
            .options(joinedload(Attachment.uploaded_by_user))
            .filter(Attachment.id == attachment_id, Attachment.organization_id == organization_id)
            .first()
        )

    def list_by_task(self, task_id: int, organization_id: int) -> List[Attachment]:
        return (
            self.db.query(Attachment)
            .options(joinedload(Attachment.uploaded_by_user))
            .filter(Attachment.task_id == task_id, Attachment.organization_id == organization_id)
            .order_by(Attachment.created_at.desc())
            .all()
        )

    def list_by_project(self, project_id: int, organization_id: int) -> List[Attachment]:
        return (
            self.db.query(Attachment)
            .options(joinedload(Attachment.uploaded_by_user))
            .filter(Attachment.project_id == project_id, Attachment.organization_id == organization_id)
            .order_by(Attachment.created_at.desc())
            .all()
        )
