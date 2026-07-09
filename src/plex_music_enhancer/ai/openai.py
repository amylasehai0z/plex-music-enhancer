"""OpenAI AI provider implementation."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from json import dumps
from os import environ
from pathlib import Path
from time import sleep
from typing import Any

from pydantic import SecretStr

from plex_music_enhancer.ai.base import AIProvider
from plex_music_enhancer.ai.exceptions import (
    AIProviderConfigurationError,
    AIProviderRequestError,
)
from plex_music_enhancer.ai.models import AICapabilities, AIProviderMetadata, GeneratedSummary
from plex_music_enhancer.config import AISettings, Settings
from plex_music_enhancer.prompts.renderer import RenderedPrompt

PROVIDER_NAME = "openai"
DEFAULT_CONFIDENCE = 0.85
PROMPT_DEBUG_DUMP_PATH = Path("/tmp/openai_prompt.txt")  # noqa: S108 - requested debug path.
PROMPT_DEBUG_METADATA_PATH = Path("/tmp/openai_prompt_meta.json")  # noqa: S108 - debug path.


class OpenAIProvider(AIProvider):
    """AI provider backed by the official OpenAI Python SDK."""

    name = PROVIDER_NAME

    def __init__(
        self,
        *,
        settings: AISettings | None = None,
        client: Any | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Create an OpenAI provider."""
        self._settings = settings or Settings().ai
        self._model = self._settings.model
        self._api_key = _api_key(self._settings.api_key)
        self._client = client
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    @property
    def model(self) -> str:
        """Return the configured OpenAI model."""
        return self._model

    def validate_configuration(self) -> None:
        """Validate OpenAI provider configuration."""
        if not self._api_key:
            msg = "OpenAI provider requires OPENAI_API_KEY or PLEX_ENHANCER_AI__API_KEY."
            raise AIProviderConfigurationError(msg)

        if not self._model.strip():
            msg = "OpenAI provider requires a non-empty model name."
            raise AIProviderConfigurationError(msg)

    def capabilities(self) -> AICapabilities:
        """Return OpenAI provider capabilities."""
        return AICapabilities(
            provider=self.name,
            album_summary=True,
            artist_summary=True,
            network_required=True,
        )

    def provider_metadata(self) -> AIProviderMetadata:
        """Return OpenAI provider metadata."""
        return AIProviderMetadata(
            provider=self.name,
            model=self.model,
            configured=bool(self._api_key),
            capabilities=self.capabilities(),
            details={
                "timeout_seconds": self._settings.timeout_seconds,
                "max_retries": self._settings.max_retries,
                "max_prompt_characters": self._settings.max_prompt_characters,
            },
        )

    def generate_album_summary(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Generate an album summary using OpenAI."""
        return self._generate(prompt)

    def generate_artist_summary(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Generate an artist summary using OpenAI."""
        return self._generate(prompt)

    def _generate(self, prompt: RenderedPrompt) -> GeneratedSummary:
        """Generate a summary for a rendered prompt."""
        self.validate_configuration()
        _validate_prompt(prompt, max_characters=self._settings.max_prompt_characters)

        response = self._request_with_retries(prompt)
        text = _response_text(response)
        if not text:
            msg = "OpenAI returned an empty summary."
            raise AIProviderRequestError(msg)

        usage = _response_usage(response)
        return GeneratedSummary(
            language=prompt.variables.get("language", "en"),
            text=text,
            provider=self.name,
            model=self.model,
            prompt_name=prompt.name,
            prompt_version=prompt.version,
            created_at=self._clock(),
            confidence=DEFAULT_CONFIDENCE,
            source_count=_source_count(prompt),
            metadata={
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "finish_reason": _finish_reason(response),
            },
        )

    def _request_with_retries(self, prompt: RenderedPrompt) -> Any:
        """Call the OpenAI SDK with simple transient retry handling."""
        attempts = self._settings.max_retries + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                _dump_prompt_for_debugging(
                    prompt,
                    provider=self.name,
                    model=self.model,
                    max_prompt_characters=self._settings.max_prompt_characters,
                    timestamp=self._clock(),
                )
                return self._client_instance().responses.create(
                    model=self.model,
                    input=prompt.rendered_text,
                )
            except Exception as exc:  # noqa: BLE001 - SDK error hierarchy is optional.
                if not _is_transient_error(exc) or attempt == attempts - 1:
                    raise _map_openai_error(exc) from exc

                last_error = exc
                sleep(min(0.25 * (attempt + 1), 1.0))

        msg = f"OpenAI request retry loop exited unexpectedly: {last_error}"
        raise AIProviderRequestError(msg)

    def _client_instance(self) -> Any:
        """Return an OpenAI SDK client."""
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError as exc:
            msg = "OpenAI provider requires the optional 'ai' dependency: openai>=1.0,<2.0."
            raise AIProviderConfigurationError(msg) from exc

        self._client = OpenAI(
            api_key=self._api_key,
            timeout=self._settings.timeout_seconds,
            max_retries=self._settings.max_retries,
        )
        return self._client


class _Usage:
    """Token usage parsed from an OpenAI response."""

    def __init__(self, *, prompt_tokens: int | None, completion_tokens: int | None) -> None:
        """Create usage data."""
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


def _api_key(configured: SecretStr | None) -> str | None:
    """Return the configured OpenAI API key."""
    if configured is not None and configured.get_secret_value().strip():
        return configured.get_secret_value().strip()

    return environ.get("OPENAI_API_KEY")


def _validate_prompt(prompt: RenderedPrompt, *, max_characters: int) -> None:
    """Validate prompt text before sending it to OpenAI."""
    if not prompt.rendered_text.strip():
        msg = "OpenAI provider refuses to send an empty prompt."
        raise AIProviderConfigurationError(msg)

    if len(prompt.rendered_text) > max_characters:
        msg = (
            "OpenAI provider refuses to send a prompt longer than " f"{max_characters} characters."
        )
        raise AIProviderConfigurationError(msg)


def _dump_prompt_for_debugging(
    prompt: RenderedPrompt,
    *,
    provider: str,
    model: str,
    max_prompt_characters: int,
    timestamp: datetime,
) -> None:
    """Temporarily dump the exact OpenAI prompt and metadata for local debugging."""
    with suppress(OSError):
        PROMPT_DEBUG_DUMP_PATH.write_text(prompt.rendered_text, encoding="utf-8")
    with suppress(OSError):
        PROMPT_DEBUG_METADATA_PATH.write_text(
            dumps(
                {
                    "timestamp": timestamp.isoformat(),
                    "provider": provider,
                    "model": model,
                    "target": prompt.name,
                    "prompt_version": prompt.version,
                    "prompt_characters": len(prompt.rendered_text),
                    "estimated_prompt_tokens": _estimate_tokens(prompt.rendered_text),
                    "max_prompt_characters": max_prompt_characters,
                    "word_limits": _word_limits(prompt),
                    "budget_diagnostics": prompt.budget_diagnostics,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )


def _estimate_tokens(text: str) -> int:
    """Return a conservative local token estimate for debug output."""
    return max(1, round(len(text) / 4)) if text else 0


def _word_limits(prompt: RenderedPrompt) -> dict[str, str]:
    """Return configured prompt word limits when present."""
    limits: dict[str, str] = {}
    minimum = prompt.variables.get("minimum_words")
    maximum = prompt.variables.get("maximum_words")
    if minimum:
        limits["minimum_words"] = minimum
    if maximum:
        limits["maximum_words"] = maximum
    return limits


def _response_text(response: Any) -> str:
    """Extract generated text from an OpenAI SDK response."""
    output_text = _attribute(response, "output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    choices = _attribute(response, "choices")
    if isinstance(choices, list) and choices:
        message = _attribute(choices[0], "message")
        content = _attribute(message, "content")
        if isinstance(content, str):
            return content.strip()

    output = _attribute(response, "output")
    if isinstance(output, list):
        texts: list[str] = []
        for item in output:
            content_items = _attribute(item, "content")
            if not isinstance(content_items, list):
                continue
            for content_item in content_items:
                text = _attribute(content_item, "text")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())
        return "\n".join(texts).strip()

    return ""


def _response_usage(response: Any) -> _Usage:
    """Extract token usage from an OpenAI SDK response."""
    usage = _attribute(response, "usage")
    return _Usage(
        prompt_tokens=_int(
            _attribute(usage, "prompt_tokens")
            or _attribute(usage, "input_tokens")
            or _attribute(usage, "total_input_tokens")
        ),
        completion_tokens=_int(
            _attribute(usage, "completion_tokens")
            or _attribute(usage, "output_tokens")
            or _attribute(usage, "total_output_tokens")
        ),
    )


def _finish_reason(response: Any) -> str | None:
    """Extract a finish reason from an OpenAI SDK response."""
    choices = _attribute(response, "choices")
    if isinstance(choices, list) and choices:
        finish_reason = _attribute(choices[0], "finish_reason")
        if isinstance(finish_reason, str):
            return finish_reason

    status = _attribute(response, "status")
    return status if isinstance(status, str) else None


def _source_count(prompt: RenderedPrompt) -> int:
    """Estimate source count from prompt variables."""
    source_variables = {"current_summary", "wikipedia_extract", "genres", "release_date"}
    return sum(1 for variable in source_variables if prompt.variables.get(variable))


def _is_transient_error(exc: Exception) -> bool:
    """Return whether an SDK error appears transient."""
    status_code = _int(_attribute(exc, "status_code"))
    if status_code in {408, 409, 429, 500, 502, 503, 504}:
        return True

    name = exc.__class__.__name__.lower()
    return any(token in name for token in ("timeout", "rate", "connection", "apierror"))


def _map_openai_error(exc: Exception) -> AIProviderRequestError:
    """Map OpenAI SDK exceptions to a project exception."""
    status_code = _attribute(exc, "status_code")
    detail = str(exc) or exc.__class__.__name__
    if status_code is not None:
        return AIProviderRequestError(f"OpenAI request failed with HTTP {status_code}: {detail}")

    return AIProviderRequestError(f"OpenAI request failed: {detail}")


def _attribute(value: Any, name: str) -> Any:
    """Read an attribute or dictionary key."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get(name)

    return getattr(value, name, None)


def _int(value: Any) -> int | None:
    """Return an integer if possible."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None

    return None
