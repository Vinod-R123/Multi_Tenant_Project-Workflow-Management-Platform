from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email.ilike(email)).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username.ilike(username)).first()

    def get_by_username_or_email(self, identifier: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(or_(User.email.ilike(identifier), User.username.ilike(identifier)))
            .first()
        )

    def store_refresh_token(self, user_id: int, jti: str, expires_at: datetime) -> RefreshToken:
        token_record = RefreshToken(
            user_id=user_id,
            jti=jti,
            expires_at=expires_at,
            is_revoked=False
        )
        self.db.add(token_record)
        self.db.commit()
        self.db.refresh(token_record)
        return token_record

    def get_valid_refresh_token(self, jti: str) -> Optional[RefreshToken]:
        now = datetime.now(timezone.utc)
        return (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.jti == jti,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > now,
            )
            .first()
        )

    def revoke_refresh_token(self, jti: str) -> bool:
        token_record = self.db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
        if token_record:
            token_record.is_revoked = True
            self.db.commit()
            return True
        return False

    def revoke_all_user_tokens(self, user_id: int) -> int:
        count = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
            .update({"is_revoked": True})
        )
        self.db.commit()
        return count
