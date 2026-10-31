from dataclasses import replace

import pytest

from app.modules.identity.application.login_with_github import (
    AccountDisabledError,
    LoginWithGithub,
    SignUpRejectedError,
)
from tests.unit.identity.fakes import NOW, InMemoryUserRepository, profile


def make() -> tuple[LoginWithGithub, InMemoryUserRepository]:
    repo = InMemoryUserRepository()
    return LoginWithGithub(repo, min_account_age_days=7), repo


def test_first_login_creates_the_user_with_github_id_as_identity():
    use_case, repo = make()

    user = use_case.execute(profile(42), now=NOW)

    assert repo.get_by_identity("github", "42") == user
    assert user.email == "dev@example.com"
    assert user.display_name == "User 42"


def test_second_login_returns_the_same_user():
    use_case, repo = make()
    first = use_case.execute(profile(42), now=NOW)

    second = use_case.execute(profile(42), now=NOW)

    assert second.id == first.id
    assert len(repo.users) == 1


def test_account_younger_than_minimum_cannot_sign_up():
    use_case, repo = make()

    with pytest.raises(SignUpRejectedError):
        use_case.execute(profile(7, age_days=3), now=NOW)

    assert repo.users == {}


def test_existing_user_is_not_blocked_by_account_age_rule():
    use_case, repo = make()
    user = use_case.execute(profile(9, age_days=30), now=NOW)

    # A regra vale só para o cadastro: quem já existe continua entrando.
    again = use_case.execute(replace(profile(9), created_at=NOW), now=NOW)

    assert again.id == user.id


def test_disabled_user_cannot_log_in():
    use_case, repo = make()
    user = use_case.execute(profile(5), now=NOW)
    repo.users[user.id] = replace(user, is_active=False)

    with pytest.raises(AccountDisabledError):
        use_case.execute(profile(5), now=NOW)


def test_email_already_used_by_another_user_is_not_reused():
    use_case, repo = make()
    use_case.execute(profile(1, email="same@example.com"), now=NOW)

    second = use_case.execute(profile(2, email="same@example.com"), now=NOW)

    assert second.email is None


def test_login_without_email_is_allowed():
    use_case, _ = make()

    assert use_case.execute(profile(3, email=None), now=NOW).email is None


def test_display_name_falls_back_to_login():
    use_case, _ = make()

    user = use_case.execute(replace(profile(4), name=None), now=NOW)

    assert user.display_name == "user4"
