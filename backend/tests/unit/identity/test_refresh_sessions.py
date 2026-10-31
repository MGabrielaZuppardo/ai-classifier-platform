from dataclasses import replace
from datetime import timedelta
from uuid import UUID

import pytest

from app.modules.identity.application.refresh_sessions import (
    InvalidRefreshTokenError,
    RefreshSessions,
    hash_token,
)
from app.modules.identity.domain.user import User
from tests.unit.identity.fakes import NOW, InMemoryRefreshTokenRepository, InMemoryUserRepository

TTL = timedelta(days=30)


def make() -> tuple[RefreshSessions, InMemoryRefreshTokenRepository, InMemoryUserRepository, User]:
    users = InMemoryUserRepository()
    user = User(display_name="Ana")
    users.users[user.id] = user
    tokens = InMemoryRefreshTokenRepository()
    return RefreshSessions(tokens, users, TTL), tokens, users, user


def test_start_stores_only_the_hash():
    sessions, tokens, _, user = make()

    issued = sessions.start(user.id, now=NOW)

    stored = next(iter(tokens.tokens.values()))
    assert stored.token_hash == hash_token(issued.value)
    assert issued.value not in stored.token_hash
    assert stored.expires_at == NOW + TTL


def test_tokens_are_random_and_unique():
    sessions, _, _, user = make()

    values = {sessions.start(user.id, now=NOW).value for _ in range(50)}

    assert len(values) == 50
    assert all(len(v) >= 43 for v in values)  # 32 bytes em base64url


def test_rotate_returns_a_new_token_in_the_same_family_and_marks_the_old_as_used():
    sessions, tokens, _, user = make()
    first = sessions.start(user.id, now=NOW)

    second = sessions.rotate(first.value, now=NOW + timedelta(minutes=10))

    assert second.value != first.value
    old = tokens.get_by_hash(hash_token(first.value))
    new = tokens.get_by_hash(hash_token(second.value))
    assert old is not None and new is not None
    assert old.used_at == NOW + timedelta(minutes=10)
    assert new.family_id == old.family_id
    assert new.used_at is None


def test_rotated_token_can_be_rotated_again():
    sessions, _, _, user = make()
    first = sessions.start(user.id, now=NOW)
    second = sessions.rotate(first.value, now=NOW)

    third = sessions.rotate(second.value, now=NOW)

    assert third.value not in (first.value, second.value)


def test_reusing_a_rotated_token_revokes_the_whole_family():
    sessions, tokens, _, user = make()
    first = sessions.start(user.id, now=NOW)
    second = sessions.rotate(first.value, now=NOW)

    with pytest.raises(InvalidRefreshTokenError):
        sessions.rotate(first.value, now=NOW)  # reutilização: possível roubo

    assert all(t.revoked_at is not None for t in tokens.tokens.values())
    with pytest.raises(InvalidRefreshTokenError):
        sessions.rotate(second.value, now=NOW)  # o token legítimo também caiu


def test_reuse_in_one_family_does_not_affect_another_session_of_the_same_user():
    sessions, _, _, user = make()
    phone = sessions.start(user.id, now=NOW)
    laptop = sessions.start(user.id, now=NOW)
    phone2 = sessions.rotate(phone.value, now=NOW)

    with pytest.raises(InvalidRefreshTokenError):
        sessions.rotate(phone.value, now=NOW)

    assert sessions.rotate(laptop.value, now=NOW).value
    with pytest.raises(InvalidRefreshTokenError):
        sessions.rotate(phone2.value, now=NOW)


def test_unknown_token_is_rejected():
    sessions, _, _, _ = make()

    with pytest.raises(InvalidRefreshTokenError):
        sessions.rotate("nao-existe", now=NOW)


def test_expired_token_is_rejected():
    sessions, _, _, user = make()
    issued = sessions.start(user.id, now=NOW)

    with pytest.raises(InvalidRefreshTokenError):
        sessions.rotate(issued.value, now=NOW + TTL)


def test_token_is_valid_just_before_expiry():
    sessions, _, _, user = make()
    issued = sessions.start(user.id, now=NOW)

    assert sessions.rotate(issued.value, now=NOW + TTL - timedelta(seconds=1)).value


def test_revoked_token_is_rejected():
    sessions, _, _, user = make()
    issued = sessions.start(user.id, now=NOW)
    sessions.revoke(issued.value, now=NOW)

    with pytest.raises(InvalidRefreshTokenError):
        sessions.rotate(issued.value, now=NOW)


def test_disabled_user_cannot_rotate_and_the_family_is_revoked():
    sessions, tokens, users, user = make()
    issued = sessions.start(user.id, now=NOW)
    users.users[user.id] = replace(user, is_active=False)

    with pytest.raises(InvalidRefreshTokenError):
        sessions.rotate(issued.value, now=NOW)

    assert all(t.revoked_at is not None for t in tokens.tokens.values())


def test_deleted_user_cannot_rotate():
    sessions, _, users, user = make()
    issued = sessions.start(user.id, now=NOW)
    users.users.clear()

    with pytest.raises(InvalidRefreshTokenError):
        sessions.rotate(issued.value, now=NOW)


def test_revoke_ends_the_whole_session_including_rotated_tokens():
    sessions, _, _, user = make()
    first = sessions.start(user.id, now=NOW)
    second = sessions.rotate(first.value, now=NOW)

    sessions.revoke(second.value, now=NOW)

    with pytest.raises(InvalidRefreshTokenError):
        sessions.rotate(second.value, now=NOW)


def test_revoking_an_unknown_token_is_silent():
    sessions, _, _, _ = make()

    sessions.revoke("nao-existe", now=NOW)


def test_tokens_of_different_users_are_isolated():
    sessions, tokens, users, ana = make()
    bia = User(display_name="Bia")
    users.users[bia.id] = bia
    ana_token = sessions.start(ana.id, now=NOW)
    sessions.start(bia.id, now=NOW)

    rotated = sessions.rotate(ana_token.value, now=NOW)

    assert rotated.user_id == ana.id
    assert {t.user_id for t in tokens.tokens.values()} == {ana.id, bia.id}
    assert isinstance(rotated.user_id, UUID)
