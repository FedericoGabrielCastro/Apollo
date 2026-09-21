import pytest


def test_env_helpers(monkeypatch) -> None:
    from config.settings import env, env_bool, env_list

    monkeypatch.setenv("SAMPLE_FLAG", "true")
    monkeypatch.setenv("SAMPLE_LIST", "a, b, c")
    monkeypatch.setenv("SAMPLE_EMPTY", "")

    assert env("SAMPLE_MISSING", "fallback") == "fallback"
    assert env_bool("SAMPLE_FLAG") is True
    assert env_list("SAMPLE_LIST") == ["a", "b", "c"]
    assert env("SAMPLE_EMPTY", "fallback") == "fallback"


def test_whitenoise_is_enabled() -> None:
    from django.conf import settings

    assert "whitenoise.middleware.WhiteNoiseMiddleware" in settings.MIDDLEWARE
    assert "whitenoise.storage.CompressedStaticFilesStorage" in str(
        settings.STORAGES["staticfiles"]["BACKEND"]
    )


def test_check_interval_setting() -> None:
    from django.conf import settings

    assert isinstance(settings.CHECK_INTERVAL_SECONDS, int)
    assert settings.CHECK_INTERVAL_SECONDS >= 1


def test_database_url_parsing() -> None:
    import dj_database_url

    config = dj_database_url.parse("postgres://apollo:apollo@db:5432/apollo")
    assert config["ENGINE"].endswith("postgresql")
    assert config["NAME"] == "apollo"
    assert config["HOST"] == "db"
