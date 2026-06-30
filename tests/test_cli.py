"""CLI tests."""

from __future__ import annotations

from typer.testing import CliRunner

from plex_music_enhancer.cli import app
from plex_music_enhancer.constants import __version__

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_doctor_reports_missing_configuration(monkeypatch) -> None:
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_URL", raising=False)
    monkeypatch.delenv("PLEX_ENHANCER_PLEX_TOKEN", raising=False)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "Python version" in result.stdout
    assert "Configuration" in result.stdout
    assert "Plex connection" in result.stdout
