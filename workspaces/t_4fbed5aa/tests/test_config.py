"""Tests for gridmind configuration and settings."""

from gridmind.config import Settings, get_settings


class TestSettings:
    """Tests for the Settings model."""

    def test_default_settings(self):
        settings = Settings()
        assert settings.app_name == "GridMind AI Platform"
        assert settings.app_version == "1.0.0"
        assert settings.debug is False
        assert settings.redis_host == "localhost"
        assert settings.redis_port == 6379
        assert settings.redis_db == 0
        assert settings.redis_password is None
        assert settings.model_predictions_ttl == 3600

    def test_custom_settings(self):
        settings = Settings(
            app_name="TestGrid",
            debug=True,
            redis_port=6380,
            model_predictions_ttl=7200,
        )
        assert settings.app_name == "TestGrid"
        assert settings.debug is True
        assert settings.redis_port == 6380
        assert settings.model_predictions_ttl == 7200

    def test_settings_caching(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_settings_with_password(self):
        settings = Settings(redis_password="secret123")
        assert settings.redis_password == "secret123"

    def test_env_file_encoding(self):
        settings = Settings()
        assert hasattr(settings.Config, "env_file")
        assert settings.Config.env_file == ".env"
