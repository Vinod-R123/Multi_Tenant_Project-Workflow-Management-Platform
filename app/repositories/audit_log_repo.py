import json
from datetime import datetime
from typing import Any, List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db: Session):
        super().__init__(AuditLog, db)

    def log(
        self,
        organization_id: int,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        details: Optional[Any] = None,
    ) -> AuditLog:
        details_str = json.dumps(details, default=str) if details is not None else None
        audit = AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            details=details_str,
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        return audit

    def list_logs(
        self,
        organization_id: int,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> Tuple[List[AuditLog], int]:
        query = (
            self.db.query(AuditLog)
            .options(joinedload(AuditLog.user))
            .filter(AuditLog.organization_id == organization_id)
        )
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)

        total = query.count()
        logs = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
        return logs, total
