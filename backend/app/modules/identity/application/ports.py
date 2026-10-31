from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.identity.domain.refresh_token import RefreshToken
from app.modules.identity.domain.user import OAuthIdentity, User


class UserRepository(Protocol):
    def add(self, user: User, identity: OAuthIdentity) -> None: ...

    def get_by_id(self, user_id: UUID) -> User | None: ...

    def get_by_identity(self, provider: str, provider_user_id: str) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...


class RefreshTokenRepository(Protocol):
    def add(self, token: RefreshToken) -> None: ...

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Busca o token travando a linha, para serializar rotações concorrentes."""
        ...

    def mark_used(self, token_id: UUID, at: datetime) -> None: ...

    def revoke_family(self, family_id: UUID, at: datetime) -> None: ...
