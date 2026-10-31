from functools import lru_cache
from typing import Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEV_SECRET = "dev-only-insecure-secret-change-me"  # noqa: S105
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    app_name: str = "AI Classifier Platform"
    environment: str = "development"
    debug: bool = False
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    redis_url: str = "redis://localhost:6379/0"
    # Idade mínima da conta GitHub para cadastro; 0 desativa a regra.
    github_min_account_age_days: int = Field(default=7, ge=0)
    # OAuth App do GitHub (Settings > Developer settings > OAuth Apps).
    github_client_id: str = ""
    github_client_secret: SecretStr = SecretStr("")
    github_redirect_uri: str = "http://localhost:8000/api/v1/auth/github/callback"
    jwt_secret: SecretStr = SecretStr(INSECURE_DEV_SECRET)
    session_secret: SecretStr = SecretStr(INSECURE_DEV_SECRET)
    access_token_ttl_minutes: int = Field(default=15, gt=0)
    refresh_token_ttl_days: int = Field(default=30, gt=0)
    cookie_secure: bool = False

    @model_validator(mode="after")
    def _require_real_secrets_outside_development(self) -> Self:
        if self.environment == "development":
            return self
        if not self.cookie_secure:
            raise ValueError("cookie_secure precisa ser verdadeiro fora de development")
        for name in ("jwt_secret", "session_secret"):
            value = getattr(self, name).get_secret_value()
            if value == INSECURE_DEV_SECRET or len(value) < MIN_SECRET_LENGTH:
                raise ValueError(
                    f"{name} precisa ter ao menos {MIN_SECRET_LENGTH} caracteres "
                    "e não pode ser o valor padrão fora de development"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
