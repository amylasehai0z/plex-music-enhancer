"""Prompt template registry."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from plex_music_enhancer.prompts.loader import PromptLoader
from plex_music_enhancer.prompts.renderer import extract_placeholders

SUPPORTED_PLACEHOLDERS = {
    "artist",
    "album",
    "genres",
    "release_date",
    "wikipedia_extract",
    "current_summary",
    "language",
    "additional_metadata",
}
PROMPT_VERSION = "1.1"


class PromptTemplate(BaseModel):
    """Loaded Markdown prompt template."""

    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    template: str
    placeholders: set[str]


class PromptRegistry:
    """Discover, load, validate, and cache prompt templates."""

    def __init__(self, loader: PromptLoader | None = None) -> None:
        """Create a prompt registry."""
        self._loader = loader or PromptLoader()
        self._cache: dict[str, PromptTemplate] = {}

    def discover(self) -> list[str]:
        """Return available template names."""
        return [path.stem for path in self._loader.discover()]

    def get(self, name: str) -> PromptTemplate:
        """Return a cached prompt template by name."""
        if name not in self._cache:
            template = self._loader.load(name)
            self._cache[name] = self._build_template(name=name, template=template)

        return self._cache[name]

    def clear_cache(self) -> None:
        """Clear cached templates."""
        self._cache.clear()

    def _build_template(self, *, name: str, template: str) -> PromptTemplate:
        """Build and validate a prompt template."""
        placeholders = extract_placeholders(template)
        unknown = sorted(placeholders - SUPPORTED_PLACEHOLDERS)
        if unknown:
            joined = ", ".join(unknown)
            msg = f'Prompt template "{name}" uses unsupported placeholders: {joined}.'
            raise ValueError(msg)

        return PromptTemplate(
            name=name,
            version=PROMPT_VERSION,
            template=template,
            placeholders=placeholders,
        )
