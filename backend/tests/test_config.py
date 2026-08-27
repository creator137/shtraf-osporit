from app.config import Settings


def test_settings_load_database_url() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://user:password@localhost:5432/database",
        _env_file=None,
    )

    assert settings.database_url.scheme == "postgresql+asyncpg"
    assert settings.database_url.hosts()[0]["host"] == "localhost"
    assert settings.database_url.path == "/database"
    assert settings.admin_origin == "http://localhost:5173"
    assert settings.ocr_provider == "ocrspace"
    assert settings.ocr_space_language == "rus"
