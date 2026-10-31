from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"  # noqa: S105


class InvalidTokenError(Exception):
    pass


class JwtAccessTokenService:
    def __init__(self, secret: str, ttl_minutes: int) -> None:
        self._secret = secret
        self._ttl = timedelta(minutes=ttl_minutes)

    @property
    def expires_in_seconds(self) -> int:
        return int(self._ttl.total_seconds())

    def issue(self, user_id: UUID, now: datetime | None = None) -> str:
        issued_at = now or datetime.now(UTC)
        claims = {
            "sub": str(user_id),
            "typ": ACCESS_TOKEN_TYPE,
            "jti": uuid4().hex,
            "iat": issued_at,
            "exp": issued_at + self._ttl,
        }
        return jwt.encode(claims, self._secret, algorithm=ALGORITHM)

    def verify(self, token: str) -> UUID:
        """Devolve o id do usuário ou levanta InvalidTokenError."""
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[ALGORITHM],
                options={"require": ["sub", "exp", "iat", "jti"]},
            )
            if claims.get("typ") != ACCESS_TOKEN_TYPE:
                raise InvalidTokenError("tipo de token inesperado")
            return UUID(claims["sub"])
        except (jwt.PyJWTError, ValueError) as exc:
            raise InvalidTokenError("token inválido") from exc
