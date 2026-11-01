from collections.abc import Iterator
from typing import Annotated
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.core.database import get_session
from app.main import create_app
from app.modules.datasets.api.dependencies import get_dataset_repository
from app.modules.datasets.domain.dataset import Dataset
from app.modules.identity.api.dependencies import (
    get_current_user,
    get_github_gateway,
    get_refresh_token_repository,
    get_user_repository,
)
from app.modules.identity.domain.user import User
from tests.unit.identity.fakes import (
    FakeGithubGateway,
    InMemoryRefreshTokenRepository,
    InMemoryUserRepository,
    profile,
)


class InMemoryDatasetRepository:
    """Armazém compartilhado, mas cada instância só enxerga os datasets do seu dono."""

    def __init__(self, store: dict[UUID, Dataset], owner_id: UUID) -> None:
        self._store = store
        self._owner_id = owner_id

    def add(self, dataset: Dataset) -> None:
        self._store[dataset.id] = dataset

    def get(self, dataset_id: UUID) -> Dataset | None:
        found = self._store.get(dataset_id)
        return found if found and found.owner_id == self._owner_id else None

    def get_by_name(self, name: str) -> Dataset | None:
        return next((d for d in self.list_all() if d.name == name), None)

    def list_all(self) -> list[Dataset]:
        return [d for d in self._store.values() if d.owner_id == self._owner_id]

    def delete(self, dataset_id: UUID) -> bool:
        if self.get(dataset_id) is None:
            return False
        del self._store[dataset_id]
        return True


@pytest.fixture
def store() -> dict[UUID, Dataset]:
    return {}


@pytest.fixture
def gateway() -> FakeGithubGateway:
    return FakeGithubGateway()


@pytest.fixture
def client(store: dict[UUID, Dataset], gateway: FakeGithubGateway) -> Iterator[TestClient]:
    users = InMemoryUserRepository()
    app = create_app()
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_refresh_token_repository] = InMemoryRefreshTokenRepository
    app.dependency_overrides[get_github_gateway] = lambda: gateway
    app.dependency_overrides[get_session] = lambda: MagicMock()

    # Mantém a autenticação real (JWT); só troca o banco pelo armazém em memória.
    def repository(user: Annotated[User, Depends(get_current_user)]) -> InMemoryDatasetRepository:
        return InMemoryDatasetRepository(store, user.id)

    app.dependency_overrides[get_dataset_repository] = repository
    yield TestClient(app, follow_redirects=False)


def _auth(client: TestClient, gateway: FakeGithubGateway, github_id: int) -> dict[str, str]:
    gateway.result = profile(github_id)
    token = client.get("/api/v1/auth/github/callback").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def alice(client: TestClient, gateway: FakeGithubGateway) -> dict[str, str]:
    return _auth(client, gateway, 1)


@pytest.fixture
def bob(client: TestClient, gateway: FakeGithubGateway) -> dict[str, str]:
    return _auth(client, gateway, 2)


def _create(client: TestClient, headers: dict[str, str], name: str = "cifar10") -> dict:
    response = client.post("/api/v1/datasets", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_requires_authentication(client: TestClient):
    assert client.get("/api/v1/datasets").status_code == 401
    assert client.post("/api/v1/datasets", json={"name": "x"}).status_code == 401


def test_create_and_get_dataset(client: TestClient, alice: dict[str, str]):
    created = _create(client, alice)

    response = client.get(f"/api/v1/datasets/{created['id']}", headers=alice)

    assert response.status_code == 200
    assert response.json()["name"] == "cifar10"


def test_name_is_trimmed(client: TestClient, alice: dict[str, str]):
    response = client.post("/api/v1/datasets", json={"name": "  cifar10  "}, headers=alice)

    assert response.json()["name"] == "cifar10"


def test_blank_name_is_rejected(client: TestClient, alice: dict[str, str]):
    response = client.post("/api/v1/datasets", json={"name": "   "}, headers=alice)

    assert response.status_code == 422


def test_duplicate_name_for_same_user_conflicts(client: TestClient, alice: dict[str, str]):
    _create(client, alice)

    response = client.post("/api/v1/datasets", json={"name": "cifar10"}, headers=alice)

    assert response.status_code == 409


def test_same_name_is_allowed_for_different_users(
    client: TestClient, alice: dict[str, str], bob: dict[str, str]
):
    _create(client, alice)

    assert _create(client, bob)["name"] == "cifar10"


def test_listing_shows_only_own_datasets(
    client: TestClient, alice: dict[str, str], bob: dict[str, str]
):
    _create(client, alice, "a1")
    _create(client, bob, "b1")

    names = [d["name"] for d in client.get("/api/v1/datasets", headers=alice).json()]

    assert names == ["a1"]


def test_other_user_cannot_read_dataset_by_id(
    client: TestClient, alice: dict[str, str], bob: dict[str, str]
):
    created = _create(client, alice)

    response = client.get(f"/api/v1/datasets/{created['id']}", headers=bob)

    assert response.status_code == 404


def test_other_user_cannot_delete_dataset_by_id(
    client: TestClient, alice: dict[str, str], bob: dict[str, str]
):
    created = _create(client, alice)

    assert client.delete(f"/api/v1/datasets/{created['id']}", headers=bob).status_code == 404
    assert client.get(f"/api/v1/datasets/{created['id']}", headers=alice).status_code == 200


def test_foreign_and_missing_ids_are_indistinguishable(
    client: TestClient, alice: dict[str, str], bob: dict[str, str]
):
    created = _create(client, alice)

    foreign = client.get(f"/api/v1/datasets/{created['id']}", headers=bob)
    missing = client.get(f"/api/v1/datasets/{uuid4()}", headers=bob)

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


def test_owner_can_delete_dataset(client: TestClient, alice: dict[str, str]):
    created = _create(client, alice)

    assert client.delete(f"/api/v1/datasets/{created['id']}", headers=alice).status_code == 204
    assert client.get(f"/api/v1/datasets/{created['id']}", headers=alice).status_code == 404
