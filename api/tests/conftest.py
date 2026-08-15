"""Общие фикстуры pytest. Переменные окружения выставляются ДО импорта app.*,
потому что Settings() и PRICING читаются один раз на уровне модуля."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

TEST_DB_PATH = API_DIR / f"test_{uuid.uuid4().hex}.db"
TEST_ADMIN_PASSWORD = "testpass123"

os.environ["BUILD_ENV"] = "dev"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["JWT_SECRET"] = "test-secret-not-for-prod"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["IP_HASH_SALT"] = "test-salt"
os.environ["CORS_ORIGIN"] = "http://localhost:8080"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""

import bcrypt  # noqa: E402

os.environ["ADMIN_PASSWORD_HASH"] = bcrypt.hashpw(TEST_ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.limiter import limiter  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def admin_password() -> str:
    return TEST_ADMIN_PASSWORD


def make_valid_lead_payload(**overrides) -> dict:
    import datetime

    payload = {
        "name": "Test User",
        "phone": "0555123456",
        "service_type": "general",
        "property_type": "apartment",
        "area_m2": 60,
        "bathrooms": 1,
        "addons": {},
        "urgency": "normal",
        "frequency": "once",
        "rendered_at": (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=10)
        ).isoformat(),
    }
    payload.update(overrides)
    return payload
