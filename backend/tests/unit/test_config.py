import pytest

from sgtrace_app.config import Settings


def test_settings_require_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        Settings.from_env()


def test_settings_redacts_secrets_and_validates_bounds(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///" + str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_SECRET", "private-value")
    monkeypatch.setenv("MAX_MATERIAL_BYTES", "1048576")
    settings = Settings.from_env()
    assert settings.database_url.startswith("sqlite+aiosqlite")
    assert "private-value" not in repr(settings)
    assert settings.max_material_bytes == 1048576


def test_settings_reject_invalid_material_limit(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///app.db")
    monkeypatch.setenv("MAX_MATERIAL_BYTES", "0")
    with pytest.raises(ValueError, match="MAX_MATERIAL_BYTES"):
        Settings.from_env()


def test_settings_repr_does_not_reveal_database_password(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql+asyncmy://reader:private-db-password@127.0.0.1/sgtrace")
    settings = Settings.from_env()
    assert "private-db-password" not in repr(settings)


@pytest.mark.parametrize("url", ["https://example.com/db", "mysql://user:password@127.0.0.1/db"])
def test_settings_reject_non_async_database_urls(monkeypatch, url):
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        Settings.from_env()
