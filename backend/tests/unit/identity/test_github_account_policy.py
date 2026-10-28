from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.identity.domain.github_account_policy import (
    GithubAccountTooNewError,
    ensure_account_old_enough,
)

NOW = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)


def test_accepts_account_older_than_minimum():
    ensure_account_old_enough(NOW - timedelta(days=30), min_age_days=7, now=NOW)


def test_accepts_account_exactly_at_minimum():
    ensure_account_old_enough(NOW - timedelta(days=7), min_age_days=7, now=NOW)


def test_rejects_account_younger_than_minimum():
    with pytest.raises(GithubAccountTooNewError) as exc:
        ensure_account_old_enough(NOW - timedelta(days=6, hours=23), min_age_days=7, now=NOW)

    assert exc.value.min_age_days == 7


def test_rejects_account_created_in_the_future():
    with pytest.raises(GithubAccountTooNewError):
        ensure_account_old_enough(NOW + timedelta(minutes=5), min_age_days=7, now=NOW)


def test_zero_minimum_disables_the_rule():
    ensure_account_old_enough(NOW, min_age_days=0, now=NOW)


def test_rejects_naive_datetime():
    with pytest.raises(ValueError, match="fuso"):
        ensure_account_old_enough(datetime(2026, 1, 1), min_age_days=7, now=NOW)


def test_default_minimum_is_seven_days():
    assert Settings().github_min_account_age_days == 7


def test_minimum_can_be_overridden_by_environment(monkeypatch):
    monkeypatch.setenv("APP_GITHUB_MIN_ACCOUNT_AGE_DAYS", "14")

    assert Settings().github_min_account_age_days == 14


def test_negative_minimum_is_invalid(monkeypatch):
    monkeypatch.setenv("APP_GITHUB_MIN_ACCOUNT_AGE_DAYS", "-1")

    with pytest.raises(ValidationError):
        Settings()
