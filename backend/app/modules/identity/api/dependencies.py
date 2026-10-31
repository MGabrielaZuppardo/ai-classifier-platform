from functools import lru_cache
from typing import Annotated, Protocol

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.core.config import get_settings
from app.core.database import get_session
from app.modules.identity.application.login_with_github import GithubProfile, LoginWithGithub
from app.modules.identity.application.ports import UserRepository
from app.modules.identity.domain.user import User
from app.modules.identity.infrastructure.github_authlib import AuthlibGithubGateway
from app.modules.identity.infrastructure.jwt_tokens import (
    InvalidTokenError,
    JwtAccessTokenService,
)
from app.modules.identity.infrastructure.repository import SqlAlchemyUserRepository

_bearer = HTTPBearer(auto_error=False)


class GithubGateway(Protocol):
    async def authorize_redirect(self, request: Request) -> Response: ...

    async def fetch_profile(self, request: Request) -> GithubProfile: ...


@lru_cache
def get_github_gateway() -> GithubGateway:
    settings = get_settings()
    return AuthlibGithubGateway(
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret.get_secret_value(),
        redirect_uri=settings.github_redirect_uri,
    )


@lru_cache
def get_token_service() -> JwtAccessTokenService:
    settings = get_settings()
    return JwtAccessTokenService(
        settings.jwt_secret.get_secret_value(), settings.access_token_ttl_minutes
    )


def get_user_repository(session: Annotated[Session, Depends(get_session)]) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_login_use_case(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> LoginWithGithub:
    return LoginWithGithub(users, get_settings().github_min_account_age_days)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    tokens: Annotated[JwtAccessTokenService, Depends(get_token_service)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Não autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        user_id = tokens.verify(credentials.credentials)
    except InvalidTokenError as exc:
        raise unauthorized from exc
    user = users.get_by_id(user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user
