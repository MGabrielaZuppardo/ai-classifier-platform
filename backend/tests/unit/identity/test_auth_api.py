from collections.abc import Iterator
from dataclasses import replace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_session
from app.main import create_app
from app.modules.identity.api.dependencies import (
    get_github_gateway,
    get_refresh_token_repository,
    get_user_repository,
)
from app.modules.identity.application.login_with_github import GithubProfile
from tests.unit.identity.fakes import (
    FakeGithubGateway,
    InMemoryRefreshTokenRepository,
    InMemoryUserRepository,
    profile,
)


@pytest.fixture
def repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def refresh_repo() -> InMemoryRefreshTokenRepository:
    return InMemoryRefreshTokenRepository()


@pytest.fixture
def gateway() -> FakeGithubGateway:
    return FakeGithubGateway()


@pytest.fixture
def client(
    repo: InMemoryUserRepository,
    refresh_repo: InMemoryRefreshTokenRepository,
    gateway: FakeGithubGateway,
) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_user_repository] = lambda: repo
    app.dependency_overrides[get_refresh_token_repository] = lambda: refresh_repo
    app.dependency_overrides[get_github_gateway] = lambda: gateway
    app.dependency_overrides[get_session] = lambda: MagicMock()
    yield TestClient(app, follow_redirects=False)


def _login(client: TestClient, gateway: FakeGithubGateway, p: GithubProfile) -> str:
    gateway.result = p
    response = client.get("/api/v1/auth/github/callback")
    assert response.status_code == 200
    return str(response.json()["access_token"])


def test_login_redirects_to_github(client: TestClient):
    response = client.get("/api/v1/auth/github/login")

    assert response.status_code == 307
    assert response.headers["location"].startswith("https://github.com/login/oauth/authorize")


def test_callback_creates_user_and_returns_access_token(client: TestClient):
    response = client.get("/api/v1/auth/github/callback")

    body = response.json()
    assert response.status_code == 200
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["access_token"]


def test_token_from_callback_authenticates_me(client: TestClient, gateway: FakeGithubGateway):
    token = _login(client, gateway, profile(11, email="me@example.com"))

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
    assert response.json()["display_name"] == "User 11"


def test_new_account_is_refused_with_generic_message(
    client: TestClient, gateway: FakeGithubGateway, repo: InMemoryUserRepository
):
    gateway.result = profile(12, age_days=2)

    response = client.get("/api/v1/auth/github/callback")

    assert response.status_code == 403
    assert response.json()["detail"] == "Não foi possível concluir o login"
    assert repo.users == {}


def test_disabled_account_gets_the_same_generic_refusal(
    client: TestClient, gateway: FakeGithubGateway, repo: InMemoryUserRepository
):
    _login(client, gateway, profile(13))
    user = next(iter(repo.users.values()))
    repo.users[user.id] = replace(user, is_active=False)

    response = client.get("/api/v1/auth/github/callback")

    assert response.status_code == 403
    assert response.json()["detail"] == "Não foi possível concluir o login"


def test_github_failure_returns_generic_error(client: TestClient, gateway: FakeGithubGateway):
    gateway.fail = True

    response = client.get("/api/v1/auth/github/callback")

    assert response.status_code == 400
    assert response.json()["detail"] == "Não foi possível concluir o login"


def test_me_requires_a_token(client: TestClient):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_rejects_an_invalid_token(client: TestClient):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer lixo"})

    assert response.status_code == 401


def test_me_rejects_token_of_a_deleted_user(
    client: TestClient, gateway: FakeGithubGateway, repo: InMemoryUserRepository
):
    token = _login(client, gateway, profile(14))
    repo.users.clear()

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_me_rejects_token_of_a_disabled_user(
    client: TestClient, gateway: FakeGithubGateway, repo: InMemoryUserRepository
):
    token = _login(client, gateway, profile(15))
    user = next(iter(repo.users.values()))
    repo.users[user.id] = replace(user, is_active=False)

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_token_for_unknown_user_id_is_rejected(client: TestClient):
    from app.modules.identity.api.dependencies import get_token_service

    token = get_token_service().issue(uuid4())

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
