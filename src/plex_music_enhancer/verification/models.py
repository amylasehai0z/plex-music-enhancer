"""Typed fact verification models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class VerificationState(StrEnum):
    """Verification state for one collected fact."""

    VERIFIED = "verified"
    PROBABLE = "probable"
    WEAK = "weak"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"


class VerifiedFact(BaseModel):
    """One fact with deterministic confidence and source attribution."""

    model_config = ConfigDict(frozen=True)

    value: str
    category: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    supporting_sources: list[str] = Field(default_factory=list)
    conflicting_sources: list[str] = Field(default_factory=list)
    preferred_source: str | None = None
    verification_state: VerificationState


class FactCollection(BaseModel):
    """Verified facts, conflicts, and missing factual categories."""

    model_config = ConfigDict(frozen=True)

    facts: list[VerifiedFact] = Field(default_factory=list)
    conflicts: list[VerifiedFact] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)

    def by_state(self, state: VerificationState) -> list[VerifiedFact]:
        """Return facts matching a verification state."""
        return [fact for fact in self.facts if fact.verification_state == state]

    def by_category(self, category: str) -> list[VerifiedFact]:
        """Return facts matching a category."""
        return [fact for fact in self.facts if fact.category == category]
