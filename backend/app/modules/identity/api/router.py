from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.core.database import get_session
from app.modules.identity.api.dependencies import (
    GithubGateway,
    get_current_user,
    get_github_gateway,
    get_login_use_case,
    get_token_service,
)
from app.modules.identity.application.login_with_github import (
    AccountDisabledError,
    LoginWithGithub,
    SignUpRejectedError,
)
from app.modules.identity.domain.user import User
from app.modules.identity.infrastructure.github_authlib import GithubOAuthError
from app.modules.identity.infrastructure.jwt_tokens import JwtAccessTokenService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Mensagem única para qualquer recusa, sem revelar o motivo (idade da conta, conta desativada).
LOGIN_REFUSED = "Não foi possível concluir o login"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


class MeResponse(BaseModel):
    id: UUID
    display_name: str
    email: str | None


@router.get("/github/login")
async def github_login(
    request: Request, gateway: Annotated[GithubGateway, Depends(get_github_gateway)]
) -> Response:
    return await gateway.authorize_redirect(request)


@router.get("/github/callback")
async def github_callback(
    request: Request,
    gateway: Annotated[GithubGateway, Depends(get_github_gateway)],
    use_case: Annotated[LoginWithGithub, Depends(get_login_use_case)],
    tokens: Annotated[JwtAccessTokenService, Depends(get_token_service)],
    session: Annotated[Session, Depends(get_session)],
) -> TokenResponse:
    try:
        profile = await gateway.fetch_profile(request)
    except GithubOAuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, LOGIN_REFUSED) from exc
    try:
        user = use_case.execute(profile)
    except (SignUpRejectedError, AccountDisabledError) as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, LOGIN_REFUSED) from exc
    session.commit()
    # Entrega provisória do token no corpo; o refresh em cookie httpOnly vem na próxima fatia.
    return TokenResponse(access_token=tokens.issue(user.id), expires_in=tokens.expires_in_seconds)


@router.get("/me")
def me(user: Annotated[User, Depends(get_current_user)]) -> MeResponse:
    return MeResponse(id=user.id, display_name=user.display_name, email=user.email)
