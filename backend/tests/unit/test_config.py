import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_development_accepts_the_insecure_default_secrets():
    assert Settings(environment="development").environment == "development"


def test_production_rejects_default_secrets():
    with pytest.raises(ValidationError):
        Settings(environment="production")


def test_production_rejects_short_secrets():
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret="curto", session_secret="x" * 40)


def test_production_accepts_strong_secrets():
    settings = Settings(environment="production", jwt_secret="j" * 40, session_secret="s" * 40)

    assert settings.environment == "production"
