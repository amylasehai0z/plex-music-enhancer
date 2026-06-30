"""Configuration tests."""

from __future__ import annotations

from plex_music_enhancer.config import Settings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400/")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")

    settings = Settings()

    assert str(settings.plex_url) == "http://localhost:32400/"
    assert settings.plex_token is not None
    assert settings.has_plex_configuration is True
