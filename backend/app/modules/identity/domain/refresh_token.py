from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class RefreshToken:
    """Registro de um refresh token. O valor em texto nunca é guardado, só o hash.

    Todos os tokens obtidos por rotação a partir do mesmo login compartilham a
    `family_id`; se um token já usado reaparecer, a família inteira é revogada.
    """

    id: UUID
    user_id: UUID
    family_id: UUID
    token_hash: str
    expires_at: datetime
    created_at: datetime
    used_at: datetime | None = None
    revoked_at: datetime | None = None
