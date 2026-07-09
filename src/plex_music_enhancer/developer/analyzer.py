"""Developer-mode explainability analysis."""

from __future__ import annotations

from dataclasses import dataclass

from plex_music_enhancer.developer.models import (
    DeveloperDoctorReport,
    DeveloperExplanation,
    PromptDebugDocument,
    PromptMetaDocument,
    ReviewLogDocument,
)
from plex_music_enhancer.developer.readers import (
    PromptDebugReader,
    PromptMetaReader,
    ReviewLogReader,
)


@dataclass(frozen=True)
class _SectionFacts:
    """Extracted facts from a review-log section."""

    lines: list[str]
    values: dict[str, str]


class DeveloperAnalyzer:
    """Analyze existing prompt and review debug artifacts."""

    def __init__(
        self,
        *,
        prompt_reader: PromptDebugReader | None = None,
        meta_reader: PromptMetaReader | None = None,
        review_reader: ReviewLogReader | None = None,
    ) -> None:
        """Create a developer analyzer."""
        self._prompt_reader = prompt_reader or PromptDebugReader()
        self._meta_reader = meta_reader or PromptMetaReader()
        self._review_reader = review_reader or ReviewLogReader()

    def explain(self) -> DeveloperExplanation:
        """Return an explainability summary using existing debug data only."""
        prompt = self._prompt_reader.read()
        meta = self._meta_reader.read()
        review = self._review_reader.read()
        return self.explain_documents(prompt, meta, review)

    def doctor(self) -> DeveloperDoctorReport:
        """Return a complete developer-mode diagnostic report."""
        prompt = self._prompt_reader.read()
        meta = self._meta_reader.read()
        review = self._review_reader.read()
        explanation = self.explain_documents(prompt, meta, review)
        checks = {
            "promptDump": "PASS" if prompt.exists and prompt.content else "MISSING",
            "promptMeta": "PASS" if meta.exists and meta.payload else "MISSING",
            "reviewLog": "PASS" if review.exists and review.content else "MISSING",
            "promptBudget": _budget_status(prompt, meta),
            "coverage": _section_status(review, "Evidence Coverage"),
            "quality": _section_status(review, "Prompt Quality"),
            "verification": _section_status(review, "Verification"),
        }
        return DeveloperDoctorReport(
            prompt=prompt,
            meta=meta,
            review=review,
            explanation=explanation,
            checks=checks,
        )

    def explain_documents(
        self,
        prompt: PromptDebugDocument,
        meta: PromptMetaDocument,
        review: ReviewLogDocument,
    ) -> DeveloperExplanation:
        """Explain why the last generated biography looks the way it does."""
        budget = _facts(review.section("Prompt Budget"))
        utilization = _facts(review.section("Prompt Utilization"))
        prompt_quality = _facts(review.section("Prompt Quality"))
        evidence = _facts(review.section("Evidence Coverage"))
        sources = _source_states(review.section("Used Sources"))
        decisions = _prompt_decisions(review.section("Prompt Decisions"))
        missed = _missed_opportunities(review)

        prompt_size = _first_int(
            utilization.values.get("Prompt size"),
            meta.payload.get("prompt_characters"),
            prompt.stats.characters,
        )
        estimated_tokens = _first_int(
            utilization.values.get("Estimated tokens"),
            meta.payload.get("estimated_prompt_tokens"),
            prompt.stats.estimated_tokens,
        )
        summary = _summary_lines(
            prompt_size=prompt_size,
            estimated_tokens=estimated_tokens,
            sources=sources,
            decisions=decisions,
            evidence=evidence,
            prompt_quality=prompt_quality,
            budget=budget,
        )
        recommendations = _recommendations(
            prompt=prompt,
            meta=meta,
            sources=sources,
            prompt_quality=prompt_quality,
            evidence=evidence,
            missed=missed,
        )
        return DeveloperExplanation(
            summary=summary,
            prompt_size=prompt_size,
            estimated_tokens=estimated_tokens,
            used_sources=sources,
            prompt_decisions=decisions,
            missed_opportunities=missed,
            recommendations=recommendations,
        )


def _facts(section: str) -> _SectionFacts:
    """Parse simple key-value and line facts from a text section."""
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    values: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return _SectionFacts(lines=lines, values=values)


def _source_states(section: str) -> dict[str, str]:
    """Parse used/omitted source states."""
    states: dict[str, str] = {}
    for line in section.splitlines():
        if ":" not in line:
            continue
        source, state = line.split(":", 1)
        states[source.strip()] = state.strip()
    return states


def _prompt_decisions(section: str) -> dict[str, list[str]]:
    """Parse Included, Removed, and Trimmed prompt decisions."""
    decisions = {"included": [], "removed": [], "trimmed": []}
    current: str | None = None
    headings = {"included": "included", "removed": "removed", "trimmed": "trimmed"}
    for raw_line in section.splitlines():
        line = raw_line.strip()
        normalized = line.casefold()
        if normalized in headings:
            current = headings[normalized]
            continue
        if current and line and line != "None.":
            decisions[current].append(line.lstrip("✓- ").strip())
    return decisions


def _missed_opportunities(review: ReviewLogDocument) -> list[str]:
    """Extract missed opportunities from coverage sections."""
    missed: list[str] = []
    for section_name in ("Editorial Coverage", "Evidence Coverage"):
        section = review.section(section_name)
        for line in section.splitlines():
            stripped = line.strip()
            if stripped.startswith("✗ "):
                missed.append(stripped.removeprefix("✗ ").strip())
            elif stripped.startswith("Missed:"):
                missed.append(stripped.removeprefix("Missed:").strip())
    return _unique(missed)


def _summary_lines(
    *,
    prompt_size: int | None,
    estimated_tokens: int | None,
    sources: dict[str, str],
    decisions: dict[str, list[str]],
    evidence: _SectionFacts,
    prompt_quality: _SectionFacts,
    budget: _SectionFacts,
) -> list[str]:
    """Build concise human-readable explanation lines."""
    lines: list[str] = []
    if prompt_size is not None:
        token_text = f" etwa {estimated_tokens} Tokens" if estimated_tokens is not None else ""
        lines.append(f"Prompt war {prompt_size} Zeichen lang{token_text}.")
    used = [source for source, state in sources.items() if state == "used"]
    omitted = [source for source, state in sources.items() if state != "used"]
    if used:
        lines.append("Genutzte Quellen: " + ", ".join(used) + ".")
    if omitted:
        lines.append("Nicht genutzte Quellen: " + ", ".join(omitted) + ".")
    removed = decisions.get("removed", [])
    trimmed = decisions.get("trimmed", [])
    if removed:
        lines.append(f"{len(removed)} Prompt-Elemente wurden entfernt oder dedupliziert.")
    if trimmed:
        lines.append(f"{len(trimmed)} Prompt-Elemente wurden gekürzt.")
    coverage = evidence.values.get("Coverage")
    if coverage:
        lines.append(f"Die Biografie nutzt {coverage} der hochwertigen Evidenz.")
    efficiency = prompt_quality.values.get("Prompt efficiency")
    if efficiency:
        lines.append(f"Prompt Efficiency: {efficiency}.")
    dominant_source = _dominant_budget_source(budget)
    if dominant_source:
        lines.append(f"Größter Prompt-Anteil: {dominant_source}.")
    return lines or ["Keine ausreichenden Debug-Daten vorhanden."]


def _recommendations(
    *,
    prompt: PromptDebugDocument,
    meta: PromptMetaDocument,
    sources: dict[str, str],
    prompt_quality: _SectionFacts,
    evidence: _SectionFacts,
    missed: list[str],
) -> list[str]:
    """Return practical developer recommendations."""
    recommendations: list[str] = []
    budget = _first_int(meta.payload.get("max_prompt_characters"), prompt.stats.budget)
    if budget and prompt.stats.characters > budget * 0.9:
        recommendations.append(
            "Prompt liegt nahe am Budget; niedrig priorisierte Narrative prüfen."
        )
    if "Wikipedia" in sources and sources.get("Wikipedia") == "used":
        recommendations.append(
            "Wikipedia dominiert häufig historische Einordnung; auf Dopplungen prüfen."
        )
    if sources.get("Discogs") == "omitted":
        recommendations.append("Discogs lieferte keinen sichtbaren Mehrwert für diesen Lauf.")
    redundancy = prompt_quality.values.get("Prompt redundancy")
    if redundancy and redundancy not in {"LOW", "low", "not reported"}:
        recommendations.append("Prompt enthält vermutlich redundante Quellen.")
    coverage = _first_int(evidence.values.get("Coverage"))
    if coverage is not None and coverage < 80:
        recommendations.append("Nicht alle hochwertigen Evidenzen wurden in der Ausgabe genutzt.")
    if missed:
        recommendations.append("Missed Opportunities prüfen: " + ", ".join(missed[:5]) + ".")
    return recommendations or ["Keine auffälligen Optimierungshinweise gefunden."]


def _budget_status(prompt: PromptDebugDocument, meta: PromptMetaDocument) -> str:
    """Return prompt-budget status."""
    budget = _first_int(meta.payload.get("max_prompt_characters"), prompt.stats.budget)
    if not budget:
        return "UNKNOWN"
    if prompt.stats.characters <= budget:
        return "PASS"
    return "FAILED"


def _section_status(review: ReviewLogDocument, section_name: str) -> str:
    """Return whether a review-log section exists."""
    return "PASS" if review.section(section_name) else "MISSING"


def _first_int(*values: object) -> int | None:
    """Return the first integer value found in heterogeneous values."""
    for value in values:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            digits = "".join(char for char in value if char.isdigit())
            if digits:
                return int(digits)
    return None


def _dominant_budget_source(budget: _SectionFacts) -> str | None:
    """Return the source with the largest reported character contribution."""
    best_name: str | None = None
    best_value = -1
    for line in budget.lines:
        if ":" not in line or "chars" not in line:
            continue
        name, value = line.split(":", 1)
        characters = _first_int(value)
        if characters is not None and characters > best_value:
            best_name = name.strip()
            best_value = characters
    return best_name


def _unique(values: list[str]) -> list[str]:
    """Return values without duplicates while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result
