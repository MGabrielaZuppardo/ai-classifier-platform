from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.identity.domain.refresh_token import RefreshToken
from app.modules.identity.infrastructure.models import RefreshTokenModel


def _to_entity(model: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=model.id,
        user_id=model.user_id,
        family_id=model.family_id,
        token_hash=model.token_hash,
        expires_at=model.expires_at,
        created_at=model.created_at,
        used_at=model.used_at,
        revoked_at=model.revoked_at,
    )


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, token: RefreshToken) -> None:
        self._session.add(
            RefreshTokenModel(
                id=token.id,
                user_id=token.user_id,
                family_id=token.family_id,
                token_hash=token.token_hash,
                expires_at=token.expires_at,
                created_at=token.created_at,
                used_at=token.used_at,
                revoked_at=token.revoked_at,
            )
        )
        self._session.flush()

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        # FOR UPDATE: duas rotações simultâneas do mesmo token são serializadas, e a
        # segunda enxerga `used_at` preenchido (reutilização).
        stmt = (
            select(RefreshTokenModel)
            .where(RefreshTokenModel.token_hash == token_hash)
            .with_for_update()
        )
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_entity(model) if model else None

    def mark_used(self, token_id: UUID, at: datetime) -> None:
        self._session.execute(
            update(RefreshTokenModel).where(RefreshTokenModel.id == token_id).values(used_at=at)
        )

    def revoke_family(self, family_id: UUID, at: datetime) -> None:
        self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.family_id == family_id, RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=at)
        )
