"""Typed developer-mode diagnostic models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PromptDebugStats:
    """Computed statistics for a rendered prompt."""

    characters: int
    words: int
    estimated_tokens: int
    budget: int | None = None
    prompt_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "characters": self.characters,
            "words": self.words,
            "estimatedTokens": self.estimated_tokens,
            "budget": self.budget,
            "promptVersion": self.prompt_version,
        }


@dataclass(frozen=True)
class PromptDebugDocument:
    """Last prompt debug dump."""

    path: Path
    exists: bool
    content: str
    stats: PromptDebugStats

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "path": str(self.path),
            "exists": self.exists,
            "content": self.content,
            "stats": self.stats.to_dict(),
        }


@dataclass(frozen=True)
class PromptMetaDocument:
    """Structured prompt metadata dump."""

    path: Path
    exists: bool
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "path": str(self.path),
            "exists": self.exists,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class ReviewLogDocument:
    """Parsed temporary review log."""

    path: Path
    exists: bool
    content: str
    sections: dict[str, str]

    def section(self, name: str) -> str:
        """Return a section by relaxed name."""
        normalized = _normalize_section_name(name)
        aliases = {
            "coverage": "evidence_coverage",
            "prompt": "prompt",
            "editorial": "editorial_quality",
            "verification": "verification",
        }
        normalized = aliases.get(normalized, normalized)
        for section_name, content in self.sections.items():
            if _normalize_section_name(section_name) == normalized:
                return content
        for section_name, content in self.sections.items():
            if normalized in _normalize_section_name(section_name):
                return content
        return ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "path": str(self.path),
            "exists": self.exists,
            "content": self.content,
            "sections": self.sections,
        }


@dataclass(frozen=True)
class DeveloperExplanation:
    """Explainability summary derived from existing debug logs."""

    summary: list[str] = field(default_factory=list)
    prompt_size: int | None = None
    estimated_tokens: int | None = None
    used_sources: dict[str, str] = field(default_factory=dict)
    prompt_decisions: dict[str, list[str]] = field(default_factory=dict)
    missed_opportunities: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "summary": self.summary,
            "promptSize": self.prompt_size,
            "estimatedTokens": self.estimated_tokens,
            "usedSources": self.used_sources,
            "promptDecisions": self.prompt_decisions,
            "missedOpportunities": self.missed_opportunities,
            "recommendations": self.recommendations,
        }


@dataclass(frozen=True)
class DeveloperDoctorReport:
    """Full developer-mode diagnostic report."""

    prompt: PromptDebugDocument
    meta: PromptMetaDocument
    review: ReviewLogDocument
    explanation: DeveloperExplanation
    checks: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "prompt": self.prompt.to_dict(),
            "meta": self.meta.to_dict(),
            "review": self.review.to_dict(),
            "explanation": self.explanation.to_dict(),
            "checks": self.checks,
        }


def _normalize_section_name(value: str) -> str:
    """Normalize a review-log section name for lookup."""
    return value.casefold().replace(" ", "_").replace("-", "_")
