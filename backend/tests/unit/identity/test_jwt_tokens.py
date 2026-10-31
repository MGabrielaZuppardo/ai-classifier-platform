from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.modules.identity.infrastructure.jwt_tokens import InvalidTokenError, JwtAccessTokenService

SECRET = "a" * 40


def service(secret: str = SECRET, ttl: int = 15) -> JwtAccessTokenService:
    return JwtAccessTokenService(secret, ttl)


def test_issued_token_verifies_to_the_same_user():
    user_id = uuid4()

    assert service().verify(service().issue(user_id)) == user_id


def test_expired_token_is_rejected():
    old = datetime.now(UTC) - timedelta(hours=1)
    token = service().issue(uuid4(), now=old)

    with pytest.raises(InvalidTokenError):
        service().verify(token)


def test_token_signed_with_another_secret_is_rejected():
    token = service("b" * 40).issue(uuid4())

    with pytest.raises(InvalidTokenError):
        service().verify(token)


def test_tampered_token_is_rejected():
    token = service().issue(uuid4())
    header, payload, signature = token.split(".")

    with pytest.raises(InvalidTokenError):
        service().verify(f"{header}.{payload}x.{signature}")


def test_unsigned_token_is_rejected():
    claims = {"sub": str(uuid4()), "typ": "access", "jti": "x", "iat": 1, "exp": 9999999999}
    token = jwt.encode(claims, key=None, algorithm="none")

    with pytest.raises(InvalidTokenError):
        service().verify(token)


def test_token_of_another_type_is_rejected():
    claims = {
        "sub": str(uuid4()),
        "typ": "refresh",
        "jti": "x",
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    token = jwt.encode(claims, SECRET, algorithm="HS256")

    with pytest.raises(InvalidTokenError):
        service().verify(token)


def test_token_without_required_claims_is_rejected():
    token = jwt.encode({"sub": str(uuid4())}, SECRET, algorithm="HS256")

    with pytest.raises(InvalidTokenError):
        service().verify(token)


def test_garbage_is_rejected():
    with pytest.raises(InvalidTokenError):
        service().verify("não-é-um-jwt")


def test_expires_in_matches_ttl():
    assert service(ttl=15).expires_in_seconds == 900
