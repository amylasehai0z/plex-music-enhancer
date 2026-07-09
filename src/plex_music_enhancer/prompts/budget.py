"""Prompt budgeting for AI generation."""

from __future__ import annotations

from logging import getLogger

from pydantic import BaseModel, ConfigDict, Field

from plex_music_enhancer.prompts.renderer import PLACEHOLDER_PATTERN, RenderedPrompt

DEFAULT_PROMPT_BUDGET = 20_000
LOGGER = getLogger(__name__)


class PromptBudgetSource(BaseModel):
    """One prompt variable contribution to the rendered prompt budget."""

    model_config = ConfigDict(frozen=True)

    name: str
    original_size: int = Field(ge=0)
    final_size: int = Field(ge=0)
    trimmed: bool = False


class PromptBudgetDiagnostics(BaseModel):
    """Diagnostics for one prompt budgeting operation."""

    model_config = ConfigDict(frozen=True)

    max_characters: int = Field(ge=1)
    original_size: int = Field(ge=0)
    final_size: int = Field(ge=0)
    trimmed_size: int = Field(ge=0)
    trimmed: bool = False
    per_source_contribution: list[PromptBudgetSource] = Field(default_factory=list)
    prompt_budget: int = Field(ge=1)
    prompt_budget_used: int = Field(ge=0)
    prompt_budget_trimmed: int = Field(ge=0)
    source_sizes: dict[str, int] = Field(default_factory=dict)
    source_priorities: dict[str, int] = Field(default_factory=dict)
    trim_operations: list[str] = Field(default_factory=list)


class PromptBudgetManager:
    """Trim rendered prompts to a configured character budget."""

    def __init__(self, max_characters: int = DEFAULT_PROMPT_BUDGET) -> None:
        """Create a prompt budget manager."""
        self._max_characters = max_characters

    @property
    def max_characters(self) -> int:
        """Return the configured maximum prompt size."""
        return self._max_characters

    def fit(self, prompt: RenderedPrompt) -> RenderedPrompt:
        """Return a prompt that fits within the configured budget."""
        return self.fit_with_diagnostics(prompt)[0]

    def fit_with_diagnostics(
        self,
        prompt: RenderedPrompt,
    ) -> tuple[RenderedPrompt, PromptBudgetDiagnostics]:
        """Return a budgeted prompt and diagnostics."""
        original_size = len(prompt.rendered_text)
        original_variables = prompt.variables
        variables = (
            _pre_reduce_variables(original_variables)
            if original_size > self._max_characters
            else dict(original_variables)
        )
        pre_reduced_text = _render_from_variables(prompt, variables)
        if original_size <= self._max_characters and variables == original_variables:
            diagnostics = _diagnostics(
                prompt=prompt,
                original_variables=original_variables,
                final_variables=variables,
                max_characters=self._max_characters,
                original_size=original_size,
            )
            return (
                prompt.model_copy(update={"budget_diagnostics": diagnostics.model_dump()}),
                diagnostics,
            )

        if original_size > self._max_characters or variables != original_variables:
            LOGGER.info(
                "Prompt exceeded configured budget. Applying intelligent context reduction.",
                extra={
                    "prompt_budget": self._max_characters,
                    "prompt_size": original_size,
                },
            )

        if len(pre_reduced_text) <= self._max_characters:
            budgeted = prompt.model_copy(
                update={"rendered_text": pre_reduced_text, "variables": variables}
            )
            diagnostics = _diagnostics(
                prompt=budgeted,
                original_variables=original_variables,
                final_variables=variables,
                max_characters=self._max_characters,
                original_size=original_size,
            )
            budgeted = budgeted.model_copy(update={"budget_diagnostics": diagnostics.model_dump()})
            return budgeted, diagnostics

        for source in _trim_order(variables):
            variables[source] = _trim_variable_until_fit(
                prompt=prompt,
                variables=variables,
                source=source,
                max_characters=self._max_characters,
            )
            rendered = _render_from_variables(prompt, variables)
            if len(rendered) <= self._max_characters:
                break

        rendered_text = _render_from_variables(prompt, variables)
        if len(rendered_text) > self._max_characters and "additional_metadata" in variables:
            variables["additional_metadata"] = _emergency_reduce_structured_metadata(
                variables["additional_metadata"],
                _variable_budget(
                    prompt=prompt,
                    variables=variables,
                    source="additional_metadata",
                    max_characters=self._max_characters,
                ),
            )
            rendered_text = _render_from_variables(prompt, variables)

        budgeted = prompt.model_copy(
            update={"rendered_text": rendered_text, "variables": variables}
        )
        diagnostics = _diagnostics(
            prompt=budgeted,
            original_variables=prompt.variables,
            final_variables=variables,
            max_characters=self._max_characters,
            original_size=original_size,
        )
        budgeted = budgeted.model_copy(update={"budget_diagnostics": diagnostics.model_dump()})
        return budgeted, diagnostics


def _trim_order(variables: dict[str, str]) -> list[str]:
    """Return prompt variables from lowest to highest priority."""
    order = [
        "current_summary",
        "lastfm_context",
        "lastfm_summary",
        "discogs_context",
        "discogs_summary",
        "wikipedia_extract",
        "knowledge_context",
        "additional_metadata",
    ]
    return [source for source in order if source in variables]


def _source_priorities(variables: dict[str, str]) -> dict[str, int]:
    """Return stable priority values where higher means more important."""
    priorities = {
        "additional_metadata": 100,
        "knowledge_context": 90,
        "wikipedia_extract": 70,
        "discogs_summary": 60,
        "discogs_context": 60,
        "lastfm_summary": 50,
        "lastfm_context": 50,
        "current_summary": 10,
    }
    return {name: priorities.get(name, 80) for name in variables}


def _pre_reduce_variables(variables: dict[str, str]) -> dict[str, str]:
    """Compress known verbose low-priority variables before full budgeting."""
    reduced = dict(variables)
    limits = {
        "current_summary": 0,
        "wikipedia_extract": 6000,
        "discogs_summary": 2500,
        "discogs_context": 2500,
        "lastfm_summary": 1200,
        "lastfm_context": 1200,
    }
    for key, limit in limits.items():
        if key in reduced and len(reduced[key]) > limit:
            reduced[key] = _trim_text(reduced[key], limit)
    return reduced


def _trim_variable_until_fit(
    *,
    prompt: RenderedPrompt,
    variables: dict[str, str],
    source: str,
    max_characters: int,
) -> str:
    """Trim one variable progressively until the prompt fits or the variable is empty."""
    value = variables[source]
    available = _variable_budget(
        prompt=prompt,
        variables=variables,
        source=source,
        max_characters=max_characters,
    )
    if source == "additional_metadata":
        return _trim_structured_metadata(value, max(available, 0))
    if available <= 0:
        return ""
    return _trim_text(value, available)


def _variable_budget(
    *,
    prompt: RenderedPrompt,
    variables: dict[str, str],
    source: str,
    max_characters: int,
) -> int:
    """Return the available size for one variable inside the whole prompt."""
    value = variables[source]
    return max(0, max_characters - (len(_render_from_variables(prompt, variables)) - len(value)))


def _trim_structured_metadata(value: str, budget: int) -> str:
    """Trim structured metadata while preserving verified facts where possible."""
    if len(value) <= budget:
        return value
    sections = value.split("\n")
    protected: list[str] = []
    optional: list[str] = []
    protect = False
    for line in sections:
        if line.startswith(("Verified facts:", "Writing guidance:")):
            protect = True
        elif line.endswith(":"):
            protect = False
        if protect or line.startswith(("Opening focus:", "Recommended story order:")):
            protected.append(line)
        else:
            optional.append(line)

    protected_text = "\n".join(protected).strip()
    if len(protected_text) >= budget:
        return _trim_text(protected_text, budget)
    remaining = budget - len(protected_text) - 2
    optional_text = _trim_text("\n".join(optional).strip(), max(remaining, 0))
    return "\n\n".join(part for part in (protected_text, optional_text) if part)


def _emergency_reduce_structured_metadata(value: str, budget: int) -> str:
    """Perform a second reduction pass that keeps only compact protected metadata."""
    if budget <= 0:
        return ""
    lines = value.splitlines()
    kept: list[str] = []
    keep_prefixes = (
        "Opening focus:",
        "Recommended story order:",
        "Verified facts:",
        "Probable facts:",
        "Writing guidance:",
        "Avoid topics:",
    )
    capture = False
    for line in lines:
        if line.startswith(keep_prefixes):
            capture = True
            kept.append(line)
            continue
        if line.endswith(":"):
            capture = False
        if capture and line.strip():
            kept.append(line)
    return _trim_text("\n".join(kept).strip(), budget)


def _render_from_variables(prompt: RenderedPrompt, variables: dict[str, str]) -> str:
    """Render a prompt template from normalized variables."""
    return PLACEHOLDER_PATTERN.sub(lambda match: variables.get(match.group(1), ""), prompt.template)


def _trim_text(text: str, max_characters: int) -> str:
    """Trim text at paragraph, sentence, or word boundaries."""
    if max_characters <= 0:
        return ""
    if len(text) <= max_characters:
        return text

    marker = "\n\n[Trimmed to fit prompt budget.]"
    if max_characters <= len(marker) + 8:
        return text[:max_characters].rstrip()

    content_budget = max_characters - len(marker)
    selected = text[:content_budget].rstrip()
    for separator in ("\n\n", ". ", "! ", "? ", "\n", " "):
        index = selected.rfind(separator)
        if index > content_budget * 0.55:
            selected = selected[: index + (1 if separator.strip() in {".", "!", "?"} else 0)]
            break
    return selected.rstrip(" ,;:-") + marker


def _diagnostics(
    *,
    prompt: RenderedPrompt,
    original_variables: dict[str, str],
    final_variables: dict[str, str],
    max_characters: int,
    original_size: int,
) -> PromptBudgetDiagnostics:
    """Build budget diagnostics."""
    final_size = len(prompt.rendered_text)
    sources = [
        PromptBudgetSource(
            name=name,
            original_size=len(value),
            final_size=len(final_variables.get(name, "")),
            trimmed=len(final_variables.get(name, "")) < len(value),
        )
        for name, value in sorted(original_variables.items())
    ]
    source_sizes = {source.name: source.final_size for source in sources}
    trim_operations = [
        f"{source.name}: {source.original_size}->{source.final_size}"
        for source in sources
        if source.trimmed
    ]
    return PromptBudgetDiagnostics(
        max_characters=max_characters,
        original_size=original_size,
        final_size=final_size,
        trimmed_size=max(0, original_size - final_size),
        trimmed=final_size < original_size,
        per_source_contribution=sources,
        prompt_budget=max_characters,
        prompt_budget_used=final_size,
        prompt_budget_trimmed=max(0, original_size - final_size),
        source_sizes=source_sizes,
        source_priorities=_source_priorities(original_variables),
        trim_operations=trim_operations,
    )
