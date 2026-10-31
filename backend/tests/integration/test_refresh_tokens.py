import secrets
from collections.abc import Iterator
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import create_session_factory, get_session
from app.main import create_app
from app.modules.identity.api.dependencies import get_github_gateway
from app.modules.identity.application.refresh_sessions import (
    InvalidRefreshTokenError,
    RefreshSessions,
    hash_token,
)
from app.modules.identity.domain.user import OAuthIdentity, User
from app.modules.identity.infrastructure.refresh_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from app.modules.identity.infrastructure.repository import SqlAlchemyUserRepository
from tests.unit.identity.fakes import NOW, FakeGithubGateway, profile

pytestmark = pytest.mark.integration

TTL = timedelta(days=30)


def _sessions(
    db_session: Session,
) -> tuple[RefreshSessions, SqlAlchemyRefreshTokenRepository, User]:
    users = SqlAlchemyUserRepository(db_session)
    user = User(display_name="Ana")
    users.add(user, OAuthIdentity("github", str(secrets.randbelow(10**9) + 10**9), user.id))
    tokens = SqlAlchemyRefreshTokenRepository(db_session)
    return RefreshSessions(tokens, users, TTL), tokens, user


def test_rotation_is_persisted_with_the_same_family(db_session: Session):
    sessions, tokens, user = _sessions(db_session)
    first = sessions.start(user.id, now=NOW)

    second = sessions.rotate(first.value, now=NOW)

    old = tokens.get_by_hash(hash_token(first.value))
    new = tokens.get_by_hash(hash_token(second.value))
    assert old is not None and new is not None
    assert old.used_at == NOW
    assert new.family_id == old.family_id


def test_reuse_revokes_every_token_of_the_family_in_the_database(db_session: Session):
    sessions, tokens, user = _sessions(db_session)
    first = sessions.start(user.id, now=NOW)
    second = sessions.rotate(first.value, now=NOW)

    with pytest.raises(InvalidRefreshTokenError):
        sessions.rotate(first.value, now=NOW)

    current = tokens.get_by_hash(hash_token(second.value))
    assert current is not None and current.revoked_at == NOW


def test_only_the_hash_is_stored(db_session: Session):
    sessions, _, user = _sessions(db_session)
    issued = sessions.start(user.id, now=NOW)

    stored = db_session.execute(text("SELECT token_hash FROM refresh_tokens")).scalars().all()

    assert hash_token(issued.value) in stored
    assert issued.value not in stored


def test_token_hash_is_unique(db_session: Session):
    sessions, tokens, user = _sessions(db_session)
    issued = sessions.start(user.id, now=NOW)
    existing = tokens.get_by_hash(hash_token(issued.value))
    assert existing is not None

    with pytest.raises(IntegrityError):
        tokens.add(replace(existing, id=uuid4()))


def test_deleting_a_user_deletes_the_refresh_tokens(db_session: Session):
    sessions, _, user = _sessions(db_session)
    sessions.start(user.id, now=NOW)

    db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user.id})

    count = db_session.execute(text("SELECT count(*) FROM refresh_tokens")).scalar_one()
    assert count == 0


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    factory = create_session_factory(engine)

    def real_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_github_gateway] = lambda: FakeGithubGateway(
        profile(secrets.randbelow(10**9) + 2 * 10**9, email=None)
    )
    app.dependency_overrides[get_session] = real_session
    yield TestClient(app, follow_redirects=False)


def test_full_flow_login_refresh_reuse_and_logout_against_the_database(
    client: TestClient, engine: Engine
):
    client.get("/api/v1/auth/github/callback")
    first = client.cookies.get("refresh_token")
    assert first is not None

    assert client.post("/api/v1/auth/refresh").status_code == 200
    second = client.cookies.get("refresh_token")
    assert second is not None and second != first

    client.cookies.set("refresh_token", first, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401  # reutilização

    # A revogação da família precisa ter sido gravada, mesmo com a resposta 401.
    client.cookies.set("refresh_token", second, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401

    with engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM users WHERE id IN "
                "(SELECT user_id FROM refresh_tokens WHERE token_hash = :a OR token_hash = :b)"
            ),
            {"a": hash_token(first), "b": hash_token(second)},
        )
