from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.datasets.domain.dataset import Dataset
from app.modules.datasets.infrastructure.repository import SqlAlchemyDatasetRepository
from app.modules.identity.domain.user import OAuthIdentity, User
from app.modules.identity.infrastructure.repository import SqlAlchemyUserRepository

pytestmark = pytest.mark.integration


def _user(session: Session, n: int) -> User:
    user = User(display_name=f"u{n}", email=f"u{n}-{uuid4().hex[:6]}@example.com")
    SqlAlchemyUserRepository(session).add(user, OAuthIdentity("github", str(uuid4()), user.id))
    return user


def test_roundtrip_and_isolation_between_owners(db_session: Session):
    alice, bob = _user(db_session, 1), _user(db_session, 2)
    repo_alice = SqlAlchemyDatasetRepository(db_session, alice.id)
    repo_bob = SqlAlchemyDatasetRepository(db_session, bob.id)
    dataset = Dataset(owner_id=alice.id, name="cifar10", description="d")
    repo_alice.add(dataset)

    assert repo_alice.get(dataset.id) == dataset
    assert repo_alice.get_by_name("cifar10") == dataset
    assert repo_bob.get(dataset.id) is None
    assert repo_bob.get_by_name("cifar10") is None
    assert repo_bob.list_all() == []
    assert repo_bob.delete(dataset.id) is False
    assert repo_alice.delete(dataset.id) is True


def test_database_enforces_unique_name_per_owner(db_session: Session):
    alice = _user(db_session, 1)
    repo = SqlAlchemyDatasetRepository(db_session, alice.id)
    repo.add(Dataset(owner_id=alice.id, name="dup"))

    with pytest.raises(IntegrityError), db_session.begin_nested():
        repo.add(Dataset(owner_id=alice.id, name="dup"))
