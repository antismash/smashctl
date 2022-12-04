import fakeredis
import pytest


@pytest.fixture
def db():
    return fakeredis.FakeRedis(encoding="utf-8", decode_responses=True)
