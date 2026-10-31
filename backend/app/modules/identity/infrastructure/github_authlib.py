from datetime import datetime
from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from starlette.responses import Response

from app.modules.identity.application.login_with_github import GithubProfile

GITHUB_SCOPE = "read:user user:email"


class GithubOAuthError(Exception):
    pass


class AuthlibGithubGateway:
    """Fluxo OAuth do GitHub (código de autorização com PKCE e `state`) via Authlib.

    O `state` e o verificador PKCE ficam na sessão assinada (SessionMiddleware).
    """

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self._redirect_uri = redirect_uri
        oauth = OAuth()
        oauth.register(
            name="github",
            client_id=client_id,
            client_secret=client_secret,
            access_token_url="https://github.com/login/oauth/access_token",  # noqa: S106
            authorize_url="https://github.com/login/oauth/authorize",
            api_base_url="https://api.github.com/",
            client_kwargs={"scope": GITHUB_SCOPE, "code_challenge_method": "S256"},
        )
        self._client: Any = oauth.github

    async def authorize_redirect(self, request: Request) -> Response:
        response: Response = await self._client.authorize_redirect(request, self._redirect_uri)
        return response

    async def fetch_profile(self, request: Request) -> GithubProfile:
        try:
            token = await self._client.authorize_access_token(request)
            user = (await self._client.get("user", token=token)).json()
            emails = (await self._client.get("user/emails", token=token)).json()
            return GithubProfile(
                id=int(user["id"]),
                login=user["login"],
                name=user.get("name"),
                email=_primary_verified_email(emails),
                created_at=datetime.fromisoformat(user["created_at"]),
            )
        except Exception as exc:  # falhas de rede, state inválido, resposta inesperada
            raise GithubOAuthError("falha ao concluir o login com o GitHub") from exc


def _primary_verified_email(emails: object) -> str | None:
    """Só confia em e-mail marcado pelo GitHub como primário e verificado."""
    if not isinstance(emails, list):
        return None
    for item in emails:
        if isinstance(item, dict) and item.get("primary") and item.get("verified"):
            email = item.get("email")
            return email if isinstance(email, str) else None
    return None
