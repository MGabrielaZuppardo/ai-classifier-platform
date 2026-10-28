import pytest
import redis
from sqlalchemy import create_engine, text

from app.core.config import get_settings

pytestmark = pytest.mark.integration


def test_postgres_accepts_connections():
    engine = create_engine(get_settings().database_url)

    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1


def test_redis_answers_ping():
    client = redis.Redis.from_url(get_settings().redis_url)

    assert client.ping() is True
