"""Packaging configuration regression tests."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict[str, Any]:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_web_static_assets_are_packaged_once_through_the_package_tree() -> None:
    """Static web assets must not be duplicated through Hatchling include rules."""
    config = _pyproject()
    hatch = config["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert hatch["packages"] == ["src/plex_music_enhancer"]
    assert "force-include" not in hatch
    assert "include" not in hatch
    assert "artifacts" not in hatch
    assert "only-include" not in hatch

    shared_data = hatch.get("shared-data", {})
    assert "src/plex_music_enhancer/web/static" not in shared_data
    assert "plex_music_enhancer/web/static" not in shared_data.values()


def test_prompt_templates_are_the_only_shared_data() -> None:
    """Prompt templates live outside the package and are installed as shared data."""
    config = _pyproject()
    hatch = config["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert hatch.get("shared-data") == {"prompts": "prompts"}
