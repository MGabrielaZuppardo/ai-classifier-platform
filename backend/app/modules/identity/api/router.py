from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.modules.identity.api.dependencies import (
    GithubGateway,
    get_current_user,
    get_github_gateway,
    get_login_use_case,
    get_refresh_sessions,
    get_token_service,
)
from app.modules.identity.application.login_with_github import (
    AccountDisabledError,
    LoginWithGithub,
    SignUpRejectedError,
)
from app.modules.identity.application.refresh_sessions import (
    InvalidRefreshTokenError,
    IssuedRefreshToken,
    RefreshSessions,
)
from app.modules.identity.domain.user import User
from app.modules.identity.infrastructure.github_authlib import GithubOAuthError
from app.modules.identity.infrastructure.jwt_tokens import JwtAccessTokenService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Mensagem única para qualquer recusa, sem revelar o motivo (idade da conta, conta desativada).
LOGIN_REFUSED = "Não foi possível concluir o login"
REFRESH_COOKIE = "refresh_token"
# O cookie só viaja para as rotas de autenticação, nunca para o resto da API.
COOKIE_PATH = "/api/v1/auth"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


class MeResponse(BaseModel):
    id: UUID
    display_name: str
    email: str | None


def _set_refresh_cookie(response: Response, issued: IssuedRefreshToken, settings: Settings) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        issued.value,
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=COOKIE_PATH,
    )


def _delete_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        REFRESH_COOKIE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=COOKIE_PATH,
    )


def _refresh_refused(settings: Settings) -> HTTPException:
    """401 que também apaga o cookie do navegador."""
    carrier = Response()
    _delete_refresh_cookie(carrier, settings)
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Sessão inválida",
        headers={"set-cookie": carrier.headers["set-cookie"]},
    )


@router.get("/github/login")
async def github_login(
    request: Request, gateway: Annotated[GithubGateway, Depends(get_github_gateway)]
) -> Response:
    return await gateway.authorize_redirect(request)


@router.get("/github/callback")
async def github_callback(
    request: Request,
    response: Response,
    gateway: Annotated[GithubGateway, Depends(get_github_gateway)],
    use_case: Annotated[LoginWithGithub, Depends(get_login_use_case)],
    sessions: Annotated[RefreshSessions, Depends(get_refresh_sessions)],
    tokens: Annotated[JwtAccessTokenService, Depends(get_token_service)],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    try:
        profile = await gateway.fetch_profile(request)
    except GithubOAuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, LOGIN_REFUSED) from exc
    try:
        user = use_case.execute(profile)
    except (SignUpRejectedError, AccountDisabledError) as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, LOGIN_REFUSED) from exc
    issued = sessions.start(user.id)
    session.commit()
    _set_refresh_cookie(response, issued, settings)
    return TokenResponse(access_token=tokens.issue(user.id), expires_in=tokens.expires_in_seconds)


@router.post("/refresh")
def refresh(
    request: Request,
    response: Response,
    sessions: Annotated[RefreshSessions, Depends(get_refresh_sessions)],
    tokens: Annotated[JwtAccessTokenService, Depends(get_token_service)],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Troca o refresh token (cookie) por um novo access token e um novo refresh token."""
    value = request.cookies.get(REFRESH_COOKIE)
    if not value:
        raise _refresh_refused(settings)
    try:
        issued = sessions.rotate(value)
    except InvalidRefreshTokenError as exc:
        # Persiste a revogação da família quando o motivo foi reutilização.
        session.commit()
        raise _refresh_refused(settings) from exc
    session.commit()
    _set_refresh_cookie(response, issued, settings)
    return TokenResponse(
        access_token=tokens.issue(issued.user_id), expires_in=tokens.expires_in_seconds
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    sessions: Annotated[RefreshSessions, Depends(get_refresh_sessions)],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Encerra a sessão: revoga a família do refresh token e apaga o cookie."""
    value = request.cookies.get(REFRESH_COOKIE)
    if value:
        sessions.revoke(value)
        session.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _delete_refresh_cookie(response, settings)
    return response


@router.get("/me")
def me(user: Annotated[User, Depends(get_current_user)]) -> MeResponse:
    return MeResponse(id=user.id, display_name=user.display_name, email=user.email)
