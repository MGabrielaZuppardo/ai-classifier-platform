from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Request
from starlette.responses import RedirectResponse, Response

from app.modules.identity.application.login_with_github import GithubProfile
from app.modules.identity.domain.refresh_token import RefreshToken
from app.modules.identity.domain.user import OAuthIdentity, User
from app.modules.identity.infrastructure.github_authlib import GithubOAuthError

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def profile(
    github_id: int = 1, *, age_days: int = 365, email: str | None = "dev@example.com"
) -> GithubProfile:
    return GithubProfile(
        id=github_id,
        login=f"user{github_id}",
        name=f"User {github_id}",
        email=email,
        created_at=NOW - timedelta(days=age_days),
    )


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}
        self.identities: dict[tuple[str, str], UUID] = {}

    def add(self, user: User, identity: OAuthIdentity) -> None:
        self.users[user.id] = user
        self.identities[(identity.provider, identity.provider_user_id)] = user.id

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    def get_by_identity(self, provider: str, provider_user_id: str) -> User | None:
        user_id = self.identities.get((provider, provider_user_id))
        return self.users[user_id] if user_id else None

    def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users.values() if u.email == email), None)


class InMemoryRefreshTokenRepository:
    def __init__(self) -> None:
        self.tokens: dict[UUID, RefreshToken] = {}

    def add(self, token: RefreshToken) -> None:
        self.tokens[token.id] = token

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return next((t for t in self.tokens.values() if t.token_hash == token_hash), None)

    def mark_used(self, token_id: UUID, at: datetime) -> None:
        self.tokens[token_id] = replace(self.tokens[token_id], used_at=at)

    def revoke_family(self, family_id: UUID, at: datetime) -> None:
        for token_id, token in list(self.tokens.items()):
            if token.family_id == family_id and token.revoked_at is None:
                self.tokens[token_id] = replace(token, revoked_at=at)


class FakeGithubGateway:
    """Substitui o GitHub nos testes: nenhuma chamada de rede."""

    def __init__(self, result: GithubProfile | None = None, *, fail: bool = False) -> None:
        self.result = result or profile()
        self.fail = fail

    async def authorize_redirect(self, request: Request) -> Response:
        return RedirectResponse("https://github.com/login/oauth/authorize?fake=1")

    async def fetch_profile(self, request: Request) -> GithubProfile:
        if self.fail:
            raise GithubOAuthError("falha simulada")
        return self.result
