from dataclasses import dataclass
from datetime import datetime

from app.modules.identity.application.ports import UserRepository
from app.modules.identity.domain.github_account_policy import (
    GithubAccountTooNewError,
    ensure_account_old_enough,
)
from app.modules.identity.domain.user import OAuthIdentity, User

PROVIDER = "github"


@dataclass(frozen=True)
class GithubProfile:
    id: int
    login: str
    created_at: datetime
    name: str | None = None
    email: str | None = None


class SignUpRejectedError(Exception):
    """Cadastro recusado pela política anti-abuso. O motivo não é exposto ao cliente."""


class AccountDisabledError(Exception):
    pass


class LoginWithGithub:
    def __init__(self, users: UserRepository, min_account_age_days: int) -> None:
        self._users = users
        self._min_account_age_days = min_account_age_days

    def execute(self, profile: GithubProfile, now: datetime | None = None) -> User:
        # A identidade é o id numérico do GitHub, nunca o username.
        provider_user_id = str(profile.id)
        existing = self._users.get_by_identity(PROVIDER, provider_user_id)
        if existing is not None:
            if not existing.is_active:
                raise AccountDisabledError
            return existing

        try:
            ensure_account_old_enough(
                profile.created_at, min_age_days=self._min_account_age_days, now=now
            )
        except GithubAccountTooNewError as exc:
            raise SignUpRejectedError from exc

        user = User(display_name=profile.name or profile.login, email=self._free_email(profile))
        self._users.add(user, OAuthIdentity(PROVIDER, provider_user_id, user.id))
        return user

    def _free_email(self, profile: GithubProfile) -> str | None:
        """Evita violar a unicidade de e-mail: se já existe outro usuário, entra sem e-mail."""
        if profile.email and self._users.get_by_email(profile.email) is None:
            return profile.email
        return None
