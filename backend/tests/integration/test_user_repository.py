import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.identity.domain.user import OAuthIdentity, User
from app.modules.identity.infrastructure.repository import SqlAlchemyUserRepository

pytestmark = pytest.mark.integration


def _register(repo: SqlAlchemyUserRepository, github_id: str, email: str | None = None) -> User:
    user = User(display_name=f"user-{github_id}", email=email)
    repo.add(user, OAuthIdentity("github", github_id, user.id))
    return user


def test_find_user_by_id(db_session: Session):
    repo = SqlAlchemyUserRepository(db_session)
    user = _register(repo, "1001", "a@example.com")

    found = repo.get_by_id(user.id)

    assert found is not None
    assert found.email == "a@example.com"
    assert found.is_active is True


def test_find_user_by_github_id(db_session: Session):
    repo = SqlAlchemyUserRepository(db_session)
    user = _register(repo, "1002")

    found = repo.get_by_identity("github", "1002")

    assert found is not None
    assert found.id == user.id


def test_unknown_identity_returns_none(db_session: Session):
    repo = SqlAlchemyUserRepository(db_session)

    assert repo.get_by_identity("github", "999999") is None


def test_same_github_account_cannot_register_twice(db_session: Session):
    repo = SqlAlchemyUserRepository(db_session)
    _register(repo, "1003")

    with pytest.raises(IntegrityError):
        _register(repo, "1003")


def test_email_must_be_unique_but_may_be_missing(db_session: Session):
    repo = SqlAlchemyUserRepository(db_session)
    _register(repo, "1004")
    _register(repo, "1005")  # dois usuários sem e-mail são permitidos
    _register(repo, "1006", "dup@example.com")

    with pytest.raises(IntegrityError):
        _register(repo, "1007", "dup@example.com")
