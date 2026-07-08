"""Prompt template file loading."""

from __future__ import annotations

from pathlib import Path


class PromptLoader:
    """Load Markdown prompt templates from disk."""

    def __init__(self, template_directory: Path | None = None) -> None:
        """Create a prompt loader."""
        self._template_directory = template_directory or _default_template_directory()

    @property
    def template_directory(self) -> Path:
        """Return the configured template directory."""
        return self._template_directory

    def discover(self) -> list[Path]:
        """Return available Markdown prompt template files."""
        if not self._template_directory.exists():
            return []

        return sorted(self._template_directory.glob("*.md"))

    def load(self, name: str) -> str:
        """Load one Markdown prompt template by name."""
        path = self._template_directory / f"{name}.md"
        if not path.exists():
            msg = f'Prompt template "{name}" was not found in {self._template_directory}.'
            raise FileNotFoundError(msg)

        return path.read_text(encoding="utf-8")


def _default_template_directory() -> Path:
    """Return the default project prompt template directory."""
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "prompts"
