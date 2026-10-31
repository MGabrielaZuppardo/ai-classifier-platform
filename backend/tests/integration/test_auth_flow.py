import secrets
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.core.database import create_session_factory, get_session
from app.main import create_app
from app.modules.identity.api.dependencies import get_github_gateway
from tests.unit.identity.fakes import FakeGithubGateway, profile

pytestmark = pytest.mark.integration


def _new_github_id() -> int:
    return secrets.randbelow(10**9) + 10**9


@pytest.fixture
def gateway() -> FakeGithubGateway:
    return FakeGithubGateway()


@pytest.fixture
def client(engine: Engine, gateway: FakeGithubGateway) -> Iterator[TestClient]:
    factory = create_session_factory(engine)

    def real_session() -> Iterator[object]:
        with factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_github_gateway] = lambda: gateway
    app.dependency_overrides[get_session] = real_session
    yield TestClient(app, follow_redirects=False)


@pytest.fixture
def created_github_ids(engine: Engine) -> Iterator[list[int]]:
    ids: list[int] = []
    yield ids
    with engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM users WHERE id IN (SELECT user_id FROM oauth_identities "
                "WHERE provider = 'github' AND provider_user_id = ANY(:ids))"
            ),
            {"ids": [str(i) for i in ids]},
        )


def test_first_login_persists_the_user_and_second_login_reuses_it(
    client: TestClient, gateway: FakeGithubGateway, created_github_ids: list[int]
):
    github_id = _new_github_id()
    created_github_ids.append(github_id)
    gateway.result = profile(github_id, email=None)

    first = client.get("/api/v1/auth/github/callback").json()["access_token"]
    second = client.get("/api/v1/auth/github/callback").json()["access_token"]

    ids = {
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t}"}).json()["id"]
        for t in (first, second)
    }
    assert len(ids) == 1


def test_refused_account_is_not_persisted(
    client: TestClient,
    gateway: FakeGithubGateway,
    engine: Engine,
    created_github_ids: list[int],
):
    github_id = _new_github_id()
    created_github_ids.append(github_id)
    gateway.result = profile(github_id, age_days=1)

    response = client.get("/api/v1/auth/github/callback")

    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT count(*) FROM oauth_identities WHERE provider_user_id = :i"),
            {"i": str(github_id)},
        ).scalar_one()
    assert response.status_code == 403
    assert count == 0


def test_user_cannot_reach_me_with_someone_elses_identity_swap(
    client: TestClient, gateway: FakeGithubGateway, created_github_ids: list[int]
):
    """Cada token enxerga só o próprio usuário, mesmo com dois usuários no banco."""
    id_a, id_b = _new_github_id(), _new_github_id()
    created_github_ids.extend([id_a, id_b])
    gateway.result = profile(id_a, email=None)
    token_a = client.get("/api/v1/auth/github/callback").json()["access_token"]
    gateway.result = profile(id_b, email=None)
    token_b = client.get("/api/v1/auth/github/callback").json()["access_token"]

    me_a = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"}).json()
    me_b = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"}).json()

    assert me_a["id"] != me_b["id"]
    assert me_a["display_name"] == f"User {id_a}"
    assert me_b["display_name"] == f"User {id_b}"
