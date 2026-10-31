from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class User:
    display_name: str
    email: str | None = None
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class OAuthIdentity:
    """Vínculo entre um usuário e a conta num provedor externo (hoje, só o GitHub).

    `provider_user_id` é o id numérico imutável do provedor, nunca o username.
    """

    provider: str
    provider_user_id: str
    user_id: UUID
