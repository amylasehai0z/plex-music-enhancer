"""Prompt budgeting for AI generation."""

from __future__ import annotations

import re
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
    budget_breakdown: dict[str, dict[str, int | float]] = Field(default_factory=dict)
    evidence_scores: dict[str, dict[str, int | float | str]] = Field(default_factory=dict)
    evidence_ranking: dict[str, int] = Field(default_factory=dict)
    prompt_decisions: dict[str, list[str]] = Field(default_factory=dict)
    prompt_quality: dict[str, int | str] = Field(default_factory=dict)


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
        "current_summary": 900,
        "wikipedia_extract": 6000,
        "discogs_summary": 2500,
        "discogs_context": 2500,
        "lastfm_summary": 1200,
        "lastfm_context": 1200,
    }
    for key, limit in limits.items():
        if key in reduced and len(reduced[key]) > limit:
            reduced[key] = _trim_evidence_text(reduced[key], limit, source=key)
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
    if source in _NARRATIVE_SOURCES:
        return _trim_evidence_text(value, available, source=source)
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
    optional_text = _trim_evidence_text(
        "\n".join(optional).strip(),
        max(remaining, 0),
        source="additional_metadata",
    )
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


def _trim_evidence_text(text: str, max_characters: int, *, source: str) -> str:
    """Trim evidence by preserving high-value narrative facts first."""
    if max_characters <= 0:
        return ""
    if len(text) <= max_characters:
        return text
    units = _evidence_units(text)
    if not units:
        return _trim_text(text, max_characters)

    marker = "\n\n[Trimmed to fit prompt budget.]"
    content_budget = max(0, max_characters - len(marker))
    ranked = sorted(
        enumerate(units),
        key=lambda item: (_evidence_unit_score(item[1], source=source), -item[0]),
        reverse=True,
    )
    selected_indexes: list[int] = []
    selected_claims: set[str] = set()
    used = 0
    for index, unit in ranked:
        claim = _semantic_claim_key(unit)
        if claim and claim in selected_claims:
            continue
        next_used = used + len(unit) + (2 if selected_indexes else 0)
        if next_used <= content_budget:
            selected_indexes.append(index)
            if claim:
                selected_claims.add(claim)
            used = next_used
    if not selected_indexes:
        return _trim_text(text, max_characters)

    selected = "\n\n".join(units[index] for index in sorted(selected_indexes)).strip()
    if len(selected) > content_budget:
        selected = _trim_text(selected, content_budget)
    return selected.rstrip(" ,;:-") + marker


def _evidence_units(text: str) -> list[str]:
    """Split evidence into stable paragraphs or sentences."""
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    if len(paragraphs) > 1:
        return paragraphs
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
        if sentence.strip()
    ]


def _evidence_unit_score(text: str, *, source: str) -> int:
    """Return a deterministic value score for one evidence unit."""
    scores = _evidence_component_scores(text)
    source_bonus = {
        "additional_metadata": 18,
        "wikipedia_extract": 14,
        "discogs_context": 8,
        "discogs_summary": 8,
        "lastfm_context": 5,
        "lastfm_summary": 5,
        "current_summary": 3,
    }.get(source, 6)
    return (
        source_bonus
        + scores["historical_significance"]
        + scores["major_works"]
        + scores["breakthrough"]
        + scores["career_progression"]
        + scores["legacy"]
        + scores["later_career"]
        + scores["international_recognition"]
        + scores["musical_profile"]
        + scores["uniqueness"]
        + scores["information_density"]
        - scores["redundancy"]
    )


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
    evidence_scores = _evidence_scores(final_variables)
    evidence_ranking = _evidence_ranking(evidence_scores)
    prompt_decisions = _prompt_decisions(
        original_variables=original_variables,
        final_variables=final_variables,
        evidence_scores=evidence_scores,
        sources=sources,
    )
    prompt_quality = _prompt_quality(
        prompt=prompt,
        final_variables=final_variables,
        evidence_scores=evidence_scores,
        prompt_decisions=prompt_decisions,
    )
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
        budget_breakdown=_budget_breakdown(prompt),
        evidence_scores=evidence_scores,
        evidence_ranking=evidence_ranking,
        prompt_decisions=prompt_decisions,
        prompt_quality=prompt_quality,
    )


def _budget_breakdown(prompt: RenderedPrompt) -> dict[str, dict[str, int | float]]:
    """Return grouped prompt budget usage by semantic section."""
    total = max(1, len(prompt.rendered_text))
    values = prompt.variables
    groups = {
        "Verified facts": _verified_fact_size(values.get("additional_metadata", "")),
        "Wikipedia": len(values.get("wikipedia_extract", "")),
        "Discogs": _line_size(values.get("additional_metadata", ""), "Discogs"),
        "Last.fm": _line_size(values.get("additional_metadata", ""), "Last.fm"),
        "Current biography": len(values.get("current_summary", "")),
        "Instructions": _instruction_size(prompt.rendered_text, before="Writing style:"),
        "Editorial Rules": _section_size(prompt.rendered_text, "Writing style:", "Factual safety:"),
        "Safety Rules": _section_size(prompt.rendered_text, "Factual safety:", "Return only"),
    }
    return {
        name: {
            "characters": size,
            "estimated_tokens": _estimate_tokens(size),
            "percentage": round((size / total) * 100, 1),
        }
        for name, size in groups.items()
    }


def _verified_fact_size(metadata: str) -> int:
    """Return the size of verified fact lines."""
    return sum(len(line) for line in metadata.splitlines() if line.startswith("Verified facts:"))


def _line_size(text: str, marker: str) -> int:
    """Return total line size for lines containing a marker."""
    return sum(len(line) for line in text.splitlines() if marker.casefold() in line.casefold())


def _instruction_size(text: str, *, before: str) -> int:
    """Return instruction size before a marker, excluding source variables."""
    index = text.find(before)
    return len(text[:index]) if index >= 0 else 0


def _section_size(text: str, start: str, end: str) -> int:
    """Return rendered prompt section size between two markers."""
    start_index = text.find(start)
    if start_index < 0:
        return 0
    end_index = text.find(end, start_index + len(start))
    if end_index < 0:
        end_index = len(text)
    return max(0, end_index - start_index)


def _estimate_tokens(characters: int) -> int:
    """Return a rough token estimate for character counts."""
    return max(1, round(characters / 4)) if characters else 0


def _evidence_scores(variables: dict[str, str]) -> dict[str, dict[str, int | float | str]]:
    """Return internal quality scores for each available evidence source."""
    source_texts = {
        "Verified facts": _verified_lines(variables.get("additional_metadata", "")),
        "Wikipedia": variables.get("wikipedia_extract", ""),
        "Discogs unique facts": _context_lines(variables.get("additional_metadata", ""), "Discogs"),
        "Last.fm style": _context_lines(variables.get("additional_metadata", ""), "Last.fm"),
        "Existing Plex biography": variables.get("current_summary", ""),
    }
    return {
        name: _evidence_score(name=name, text=text)
        for name, text in source_texts.items()
        if text.strip()
    }


def _evidence_score(*, name: str, text: str) -> dict[str, int | float | str]:
    """Return deterministic component scores for one evidence source."""
    components = _evidence_component_scores(text)
    source_weight = {
        "Verified facts": 1.0,
        "Wikipedia": 0.9,
        "Discogs unique facts": 0.75,
        "Last.fm style": 0.55,
        "Existing Plex biography": 0.5,
    }.get(name, 0.6)
    raw = (
        components["historical_significance"]
        + components["major_works"]
        + components["breakthrough"]
        + components["career_progression"]
        + components["legacy"]
        + components["later_career"]
        + components["international_recognition"]
        + components["musical_profile"]
        + components["uniqueness"]
        + components["information_density"]
        - components["redundancy"]
    )
    score = max(0, min(100, round(raw * source_weight)))
    return {
        "score": score,
        "confidence": round(source_weight, 2),
        "historical_significance": components["historical_significance"],
        "major_works": components["major_works"],
        "breakthrough": components["breakthrough"],
        "career_progression": components["career_progression"],
        "legacy": components["legacy"],
        "later_career": components["later_career"],
        "international_recognition": components["international_recognition"],
        "musical_profile": components["musical_profile"],
        "uniqueness": components["uniqueness"],
        "information_density": components["information_density"],
        "redundancy": components["redundancy"],
    }


def _evidence_component_scores(text: str) -> dict[str, int]:
    """Return category scores for one evidence text."""
    return {
        "historical_significance": _keyword_score(text, _HISTORICAL_KEYWORDS, multiplier=8),
        "major_works": _keyword_score(text, _MAJOR_WORK_KEYWORDS, multiplier=8),
        "breakthrough": _keyword_score(text, _BREAKTHROUGH_KEYWORDS, multiplier=9),
        "career_progression": _keyword_score(text, _CAREER_KEYWORDS, multiplier=6),
        "legacy": _keyword_score(text, _LEGACY_KEYWORDS, multiplier=8),
        "later_career": _keyword_score(text, _LATER_CAREER_KEYWORDS, multiplier=7),
        "international_recognition": _keyword_score(
            text,
            _INTERNATIONAL_KEYWORDS,
            multiplier=7,
        ),
        "musical_profile": _keyword_score(text, _STYLE_KEYWORDS, multiplier=4),
        "uniqueness": _uniqueness_score(text),
        "information_density": _information_density_score(text),
        "redundancy": _redundancy_score(text),
    }


def _keyword_score(text: str, keywords: tuple[str, ...], *, multiplier: int) -> int:
    """Score keyword coverage for an evidence category."""
    lowered = text.casefold()
    matches = sum(1 for keyword in keywords if keyword in lowered)
    return min(24, matches * multiplier)


def _uniqueness_score(text: str) -> int:
    """Reward compact, specific evidence over generic metadata."""
    lowered = text.casefold()
    specific_matches = sum(1 for pattern in _SPECIFIC_PATTERNS if pattern.search(lowered))
    return min(20, specific_matches * 5)


def _information_density_score(text: str) -> int:
    """Reward compact evidence with useful facts per sentence."""
    units = _evidence_units(text)
    if not units:
        return 0
    specific_units = sum(
        1
        for unit in units
        if any(pattern.search(unit) for pattern in _SPECIFIC_PATTERNS)
        or any(keyword in unit.casefold() for keyword in _HIGH_VALUE_KEYWORDS)
    )
    return min(24, round((specific_units / len(units)) * 24))


def _redundancy_score(text: str) -> int:
    """Penalize repeated lines and semantically duplicated claims."""
    normalized_units = [_semantic_claim_key(unit) for unit in _evidence_units(text)]
    duplicates = len(normalized_units) - len({unit for unit in normalized_units if unit})
    return min(30, max(0, duplicates) * 8)


def _verified_lines(metadata: str) -> str:
    """Return verified fact lines from structured metadata."""
    return "\n".join(line for line in metadata.splitlines() if line.startswith("Verified facts:"))


def _context_lines(metadata: str, marker: str) -> str:
    """Return metadata lines for one provider context."""
    return "\n".join(line for line in metadata.splitlines() if marker.casefold() in line.casefold())


def _evidence_ranking(
    evidence_scores: dict[str, dict[str, int | float | str]],
) -> dict[str, int]:
    """Return evidence sources ordered by total editorial value."""
    ranked = sorted(
        (
            (name, int(scores.get("score", 0)))
            for name, scores in evidence_scores.items()
            if int(scores.get("score", 0)) > 0
        ),
        key=lambda item: (-item[1], item[0]),
    )
    return dict(ranked)


def _prompt_decisions(
    *,
    original_variables: dict[str, str],
    final_variables: dict[str, str],
    evidence_scores: dict[str, dict[str, int | float | str]],
    sources: list[PromptBudgetSource],
) -> dict[str, list[str]]:
    """Return explainable prompt inclusion, removal, and trimming decisions."""
    included = [
        _decision_label(name, scores)
        for name, scores in sorted(
            evidence_scores.items(),
            key=lambda item: int(item[1].get("score", 0)),
            reverse=True,
        )
        if int(scores.get("score", 0)) > 0
    ]
    removed = [
        f"{_source_label(name)} removed due to low prompt budget value"
        for name, original in original_variables.items()
        if original.strip() and not final_variables.get(name, "").strip()
    ]
    duplicate_claims = _duplicate_claims(original_variables)
    removed.extend(f"Duplicate {claim}" for claim in duplicate_claims)
    trimmed = [
        f"{_source_label(source.name)} ({_trim_percentage(source)}%)"
        for source in sources
        if source.trimmed and source.final_size > 0
    ]
    return {
        "included": included or ["No scored evidence available"],
        "removed": removed or ["No evidence removed"],
        "trimmed": trimmed or ["No evidence trimmed"],
    }


def _decision_label(name: str, scores: dict[str, int | float | str]) -> str:
    """Return a concise label for an included source."""
    categories = [
        category.replace("_", " ")
        for category in (
            "historical_significance",
            "major_works",
            "breakthrough",
            "career_progression",
            "legacy",
            "later_career",
            "international_recognition",
            "musical_profile",
        )
        if int(scores.get(category, 0)) > 0
    ]
    detail = ", ".join(categories[:3]) if categories else "supporting context"
    return f"{name} ({scores.get('score', 0)}/100: {detail})"


def _source_label(name: str) -> str:
    """Return a user-facing source label for prompt variables."""
    labels = {
        "additional_metadata": "Verified and structured metadata",
        "wikipedia_extract": "Wikipedia context",
        "discogs_context": "Discogs context",
        "discogs_summary": "Discogs summary",
        "lastfm_context": "Last.fm context",
        "lastfm_summary": "Last.fm summary",
        "current_summary": "Existing biography",
        "knowledge_context": "Knowledge Builder context",
    }
    return labels.get(name, name)


def _trim_percentage(source: PromptBudgetSource) -> int:
    """Return the percentage removed from one source."""
    if source.original_size <= 0:
        return 0
    return round(((source.original_size - source.final_size) / source.original_size) * 100)


def _duplicate_claims(variables: dict[str, str]) -> list[str]:
    """Return semantically duplicated claim labels across evidence sources."""
    seen: dict[str, int] = {}
    for value in variables.values():
        for unit in _evidence_units(value):
            key = _semantic_claim_key(unit)
            if key:
                seen[key] = seen.get(key, 0) + 1
    return sorted(_SEMANTIC_CLAIM_LABELS.get(key, key) for key, count in seen.items() if count > 1)


def _semantic_claim_key(text: str) -> str:
    """Return a coarse semantic key for common duplicated music-biography claims."""
    lowered = text.casefold()
    if (
        "million" in lowered
        or "millionen" in lowered
        or "best-selling" in lowered
        or "erfolgreichsten" in lowered
    ):
        return "commercial_success"
    if "eurovision" in lowered or "waterloo" in lowered:
        return "eurovision_breakthrough"
    if "mamma mia" in lowered:
        return "mamma_mia_revival"
    if "voyage" in lowered or "reunion" in lowered or "rückkehr" in lowered:
        return "later_reunion"
    if "hall of fame" in lowered:
        return "hall_of_fame"
    if "origin" in lowered or "formed" in lowered or "gründ" in lowered:
        return "origin"
    return ""


def _prompt_quality(
    *,
    prompt: RenderedPrompt,
    final_variables: dict[str, str],
    evidence_scores: dict[str, dict[str, int | float | str]],
    prompt_decisions: dict[str, list[str]],
) -> dict[str, int | str]:
    """Return high-level quality indicators for prompt construction."""
    duplicate_count = sum(
        1 for item in prompt_decisions.get("removed", []) if item.startswith("Duplicate ")
    )
    used_sources = sum(1 for value in final_variables.values() if value.strip())
    source_balance = min(100, used_sources * 14)
    evidence_diversity = min(100, len(evidence_scores) * 20)
    information_density = (
        round(
            sum(int(scores.get("information_density", 0)) for scores in evidence_scores.values())
            / len(evidence_scores)
        )
        if evidence_scores
        else 0
    )
    historical_coverage = _coverage_score(prompt.rendered_text, _HISTORICAL_KEYWORDS)
    career_coverage = _coverage_score(prompt.rendered_text, _CAREER_KEYWORDS)
    legacy_coverage = _coverage_score(prompt.rendered_text, _LEGACY_KEYWORDS)
    prompt_redundancy = max(0, 100 - duplicate_count * 12)
    prompt_size_score = max(
        0, 100 - round((len(prompt.rendered_text) / DEFAULT_PROMPT_BUDGET) * 20)
    )
    prompt_efficiency = round(
        (
            prompt_size_score
            + prompt_redundancy
            + evidence_diversity
            + information_density
            + historical_coverage
            + career_coverage
            + legacy_coverage
        )
        / 7
    )
    reason = (
        "balanced evidence with low redundancy"
        if prompt_efficiency >= 85
        else "review source balance and missed evidence"
    )
    return {
        "prompt_redundancy": prompt_redundancy,
        "evidence_diversity": evidence_diversity,
        "information_density": information_density,
        "historical_coverage": historical_coverage,
        "career_coverage": career_coverage,
        "legacy_coverage": legacy_coverage,
        "source_balance": source_balance,
        "prompt_efficiency": prompt_efficiency,
        "prompt_efficiency_reason": reason,
    }


def _coverage_score(text: str, keywords: tuple[str, ...]) -> int:
    """Return keyword coverage as a 0-100 score."""
    lowered = text.casefold()
    if not keywords:
        return 0
    matches = sum(1 for keyword in keywords if keyword in lowered)
    return min(100, round((matches / min(len(keywords), 6)) * 100))


_NARRATIVE_SOURCES = {
    "wikipedia_extract",
    "discogs_context",
    "discogs_summary",
    "lastfm_context",
    "lastfm_summary",
    "current_summary",
}

_HISTORICAL_KEYWORDS = (
    "historical",
    "historisch",
    "bedeutung",
    "significance",
    "influence",
    "einfluss",
    "culture",
    "kultur",
)
_MAJOR_WORK_KEYWORDS = (
    "waterloo",
    "dancing queen",
    "mamma mia",
    "voyage",
    "album",
    "single",
    "work",
    "werk",
)
_BREAKTHROUGH_KEYWORDS = (
    "breakthrough",
    "durchbruch",
    "eurovision",
    "international recognition",
    "weltweit",
)
_CAREER_KEYWORDS = (
    "career",
    "karriere",
    "phase",
    "early",
    "later",
    "später",
    "reunion",
    "comeback",
)
_LEGACY_KEYWORDS = (
    "legacy",
    "vermächtnis",
    "lasting",
    "enduring",
    "continued popularity",
    "hall of fame",
    "revival",
)
_LATER_CAREER_KEYWORDS = (
    "later",
    "später",
    "reunion",
    "rückkehr",
    "comeback",
    "revival",
    "voyage",
)
_INTERNATIONAL_KEYWORDS = (
    "international",
    "worldwide",
    "global",
    "weltweit",
    "eurovision",
    "hall of fame",
)
_STYLE_KEYWORDS = (
    "style",
    "stil",
    "genre",
    "sound",
    "musical",
    "musik",
    "pop",
    "rock",
)
_HIGH_VALUE_KEYWORDS = (
    *_HISTORICAL_KEYWORDS,
    *_MAJOR_WORK_KEYWORDS,
    *_BREAKTHROUGH_KEYWORDS,
    *_CAREER_KEYWORDS,
    *_LEGACY_KEYWORDS,
    *_LATER_CAREER_KEYWORDS,
    *_INTERNATIONAL_KEYWORDS,
)
_SPECIFIC_PATTERNS = (
    re.compile(r"\b(19|20)\d{2}\b"),
    re.compile(r"\b[A-ZÄÖÜ][\wÄÖÜäöüß'!-]{3,}\b"),
    re.compile(r"\b\d+\s*(million|millionen)\b"),
)
_SEMANTIC_CLAIM_LABELS = {
    "commercial_success": "commercial success",
    "eurovision_breakthrough": "Eurovision/Waterloo breakthrough",
    "mamma_mia_revival": "Mamma Mia revival",
    "later_reunion": "later reunion",
    "hall_of_fame": "Hall of Fame recognition",
    "origin": "origin",
}
