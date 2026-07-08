"""Configuration tests."""

from __future__ import annotations

from pathlib import Path

from plex_music_enhancer.config import Settings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_URL", "http://localhost:32400/")
    monkeypatch.setenv("PLEX_ENHANCER_PLEX_TOKEN", "secret-token")

    settings = Settings()

    assert str(settings.plex_url) == "http://localhost:32400/"
    assert settings.plex_token is not None
    assert settings.has_plex_configuration is True


def test_settings_ignore_dotenv_during_tests(monkeypatch, tmp_path: Path) -> None:
    """Settings should not inherit developer-local dotenv files during tests."""
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_URL", raising=False)
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)
    dotenv_content = (
        "PLEX_ENHANCER_PLEX_URL=http://localhost:32400\n" "PLEX_ENHANCER_PLEX_TOKEN=secret-token\n"
    )
    Path(".env").write_text(
        dotenv_content,
        encoding="utf-8",
    )

    settings = Settings()

    assert settings.plex_url is None
    assert settings.plex_token is None
    assert settings.has_plex_configuration is False
