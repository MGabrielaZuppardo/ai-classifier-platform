from typing import Protocol
from uuid import UUID

from app.modules.identity.domain.user import OAuthIdentity, User


class UserRepository(Protocol):
    def add(self, user: User, identity: OAuthIdentity) -> None: ...

    def get_by_id(self, user_id: UUID) -> User | None: ...

    def get_by_identity(self, provider: str, provider_user_id: str) -> User | None: ...
