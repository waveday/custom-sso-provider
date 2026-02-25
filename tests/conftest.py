import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ISSUER", "http://accounts.localhost:8000")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("APP_SECRET", "test-secret")
os.environ.setdefault("SECURE_COOKIES", "false")

from app.config import get_settings  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)
