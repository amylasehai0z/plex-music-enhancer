"""Prompt template rendering."""

from __future__ import annotations

from re import Pattern, compile
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

PLACEHOLDER_PATTERN: Pattern[str] = compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")


class RenderedPrompt(BaseModel):
    """A prompt rendered from a Markdown template."""

    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    rendered_text: str
    variables: dict[str, str] = Field(default_factory=dict)
    template: str


class PromptRenderer:
    """Render Markdown prompt templates with strict variable substitution."""

    def render(
        self,
        *,
        name: str,
        version: str,
        template: str,
        variables: dict[str, Any],
    ) -> RenderedPrompt:
        """Render a prompt template."""
        placeholders = extract_placeholders(template)
        normalized_variables = {
            key: _string(value)
            for key, value in variables.items()
            if key in placeholders and _string(value) is not None
        }
        missing = sorted(
            placeholder for placeholder in placeholders if placeholder not in normalized_variables
        )
        if missing:
            joined = ", ".join(missing)
            msg = f"Missing required prompt variables: {joined}."
            raise ValueError(msg)

        rendered_text = PLACEHOLDER_PATTERN.sub(
            lambda match: normalized_variables[match.group(1)],
            template,
        )

        return RenderedPrompt(
            name=name,
            version=version,
            rendered_text=rendered_text,
            variables=normalized_variables,
            template=template,
        )


def extract_placeholders(template: str) -> set[str]:
    """Return placeholders used by a template."""
    return set(PLACEHOLDER_PATTERN.findall(template))


def _string(value: object) -> str | None:
    """Return a string representation suitable for prompt substitution."""
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())

    text = str(value).strip()
    return text or None
