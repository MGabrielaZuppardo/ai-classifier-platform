import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.modules.identity.application.ports import RefreshTokenRepository, UserRepository
from app.modules.identity.domain.refresh_token import RefreshToken


class InvalidRefreshTokenError(Exception):
    """Token desconhecido, expirado, revogado, reutilizado ou de usuário desativado.

    O motivo não é exposto ao cliente. Quem captura isto deve persistir a transação
    antes de responder, porque uma reutilização revoga a família.
    """


@dataclass(frozen=True)
class IssuedRefreshToken:
    value: str
    user_id: UUID
    expires_at: datetime


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class RefreshSessions:
    def __init__(
        self, tokens: RefreshTokenRepository, users: UserRepository, ttl: timedelta
    ) -> None:
        self._tokens = tokens
        self._users = users
        self._ttl = ttl

    def start(self, user_id: UUID, now: datetime | None = None) -> IssuedRefreshToken:
        """Abre uma sessão nova (uma família nova de tokens) após o login."""
        return self._issue(user_id, family_id=uuid4(), now=now or datetime.now(UTC))

    def rotate(self, value: str, now: datetime | None = None) -> IssuedRefreshToken:
        current = now or datetime.now(UTC)
        token = self._tokens.get_by_hash(hash_token(value))
        if token is None:
            raise InvalidRefreshTokenError

        if token.used_at is not None:
            # Token já trocado reapareceu: possível roubo. Derruba a sessão inteira.
            self._tokens.revoke_family(token.family_id, current)
            raise InvalidRefreshTokenError
        if token.revoked_at is not None or token.expires_at <= current:
            raise InvalidRefreshTokenError

        user = self._users.get_by_id(token.user_id)
        if user is None or not user.is_active:
            self._tokens.revoke_family(token.family_id, current)
            raise InvalidRefreshTokenError

        self._tokens.mark_used(token.id, current)
        return self._issue(token.user_id, family_id=token.family_id, now=current)

    def revoke(self, value: str, now: datetime | None = None) -> None:
        """Encerra a sessão do token apresentado. Silencioso se o token for desconhecido."""
        token = self._tokens.get_by_hash(hash_token(value))
        if token is not None:
            self._tokens.revoke_family(token.family_id, now or datetime.now(UTC))

    def _issue(self, user_id: UUID, family_id: UUID, now: datetime) -> IssuedRefreshToken:
        value = secrets.token_urlsafe(32)
        expires_at = now + self._ttl
        self._tokens.add(
            RefreshToken(
                id=uuid4(),
                user_id=user_id,
                family_id=family_id,
                token_hash=hash_token(value),
                expires_at=expires_at,
                created_at=now,
            )
        )
        return IssuedRefreshToken(value=value, user_id=user_id, expires_at=expires_at)
