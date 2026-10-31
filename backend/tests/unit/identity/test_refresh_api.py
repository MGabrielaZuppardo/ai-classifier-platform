from collections.abc import Iterator
from dataclasses import replace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_session
from app.main import create_app
from app.modules.identity.api.dependencies import (
    get_github_gateway,
    get_refresh_token_repository,
    get_user_repository,
)
from tests.unit.identity.fakes import (
    FakeGithubGateway,
    InMemoryRefreshTokenRepository,
    InMemoryUserRepository,
    profile,
)

LOGIN = "/api/v1/auth/github/callback"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"


@pytest.fixture
def repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def client(repo: InMemoryUserRepository) -> Iterator[TestClient]:
    app = create_app()
    refresh_repo = InMemoryRefreshTokenRepository()
    app.dependency_overrides[get_user_repository] = lambda: repo
    app.dependency_overrides[get_refresh_token_repository] = lambda: refresh_repo
    app.dependency_overrides[get_github_gateway] = lambda: FakeGithubGateway(profile(21))
    app.dependency_overrides[get_session] = lambda: MagicMock()
    yield TestClient(app, follow_redirects=False)


def _refresh_cookie(client: TestClient) -> str | None:
    return client.cookies.get("refresh_token")


def test_login_sets_a_hardened_refresh_cookie(client: TestClient):
    response = client.get(LOGIN)

    header = response.headers["set-cookie"].lower()
    assert "refresh_token=" in header
    assert "httponly" in header
    assert "samesite=strict" in header
    assert "path=/api/v1/auth" in header
    assert f"max-age={30 * 24 * 3600}" in header


def test_refresh_token_is_never_in_the_response_body(client: TestClient):
    response = client.get(LOGIN)

    assert _refresh_cookie(client) not in response.text


def test_refresh_returns_new_access_token_and_rotates_the_cookie(client: TestClient):
    client.get(LOGIN)
    before = _refresh_cookie(client)

    response = client.post(REFRESH)

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert _refresh_cookie(client) not in (None, before)


def test_access_token_from_refresh_works_on_protected_routes(client: TestClient):
    client.get(LOGIN)

    token = client.post(REFRESH).json()["access_token"]

    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_refresh_without_cookie_is_refused(client: TestClient):
    assert client.post(REFRESH).status_code == 401


def test_refresh_with_garbage_cookie_is_refused_and_clears_it(client: TestClient):
    client.cookies.set("refresh_token", "lixo", path="/api/v1/auth")

    response = client.post(REFRESH)

    assert response.status_code == 401
    assert "max-age=0" in response.headers["set-cookie"].lower()


def test_reused_refresh_token_is_refused_and_kills_the_session(client: TestClient):
    client.get(LOGIN)
    stolen = _refresh_cookie(client)
    assert stolen is not None
    assert client.post(REFRESH).status_code == 200  # o dono troca o token
    legit = _refresh_cookie(client)

    client.cookies.set("refresh_token", stolen, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401  # o atacante reutiliza o antigo

    assert legit is not None
    client.cookies.set("refresh_token", legit, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401  # e o token legítimo também caiu


def test_refresh_is_refused_for_a_disabled_user(client: TestClient, repo: InMemoryUserRepository):
    client.get(LOGIN)
    user = next(iter(repo.users.values()))
    repo.users[user.id] = replace(user, is_active=False)

    assert client.post(REFRESH).status_code == 401


def test_refresh_only_accepts_post(client: TestClient):
    client.get(LOGIN)

    assert client.get(REFRESH).status_code == 405


def test_logout_revokes_the_session_and_clears_the_cookie(client: TestClient):
    client.get(LOGIN)
    cookie = _refresh_cookie(client)
    assert cookie is not None

    response = client.post(LOGOUT)

    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    client.cookies.set("refresh_token", cookie, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401


def test_logout_without_session_is_harmless(client: TestClient):
    assert client.post(LOGOUT).status_code == 204
