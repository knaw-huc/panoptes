"""
Shared pytest fixtures.

Provides fake application settings so that tests never depend on the
developer's local `.env` file (which is git-ignored and may contain real
credentials).
"""

import pytest

from app.config import get_settings, Settings


@pytest.fixture(autouse=True)
def fake_settings(monkeypatch):
    """
    Ensure `get_settings()` returns deterministic, non-secret test settings
    and that nothing in the test suite accidentally reads the real `.env`.
    """
    settings = Settings(
        es_scheme="http",
        es_host="localhost",
        es_port=9200,
        es_username=None,
        es_password=None,
        mongo_connection="mongodb://localhost:27017/",
        admin_domain="admin.test",
        jwt_secret="test-secret-key-at-least-32-bytes-long",
        _env_file=None,
    )
    get_settings.cache_clear()
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.authentication.authentication.get_settings",
                         lambda: settings)
    yield settings
    get_settings.cache_clear()
