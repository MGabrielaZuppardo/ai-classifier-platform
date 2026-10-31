from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.domain.user import OAuthIdentity, User
from app.modules.identity.infrastructure.models import OAuthIdentityModel, UserModel


def _to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        display_name=model.display_name,
        email=model.email,
        is_active=model.is_active,
        created_at=model.created_at,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User, identity: OAuthIdentity) -> None:
        self._session.add(
            UserModel(
                id=user.id,
                display_name=user.display_name,
                email=user.email,
                is_active=user.is_active,
                created_at=user.created_at,
            )
        )
        # Garante o INSERT do usuário antes da identidade que o referencia.
        self._session.flush()
        self._session.add(
            OAuthIdentityModel(
                id=uuid4(),
                user_id=identity.user_id,
                provider=identity.provider,
                provider_user_id=identity.provider_user_id,
            )
        )
        self._session.flush()

    def get_by_id(self, user_id: UUID) -> User | None:
        model = self._session.get(UserModel, user_id)
        return _to_entity(model) if model else None

    def get_by_identity(self, provider: str, provider_user_id: str) -> User | None:
        stmt = (
            select(UserModel)
            .join(OAuthIdentityModel, OAuthIdentityModel.user_id == UserModel.id)
            .where(
                OAuthIdentityModel.provider == provider,
                OAuthIdentityModel.provider_user_id == provider_user_id,
            )
        )
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_entity(model) if model else None
