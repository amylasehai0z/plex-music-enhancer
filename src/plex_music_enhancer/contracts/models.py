"""Frontend-neutral application contract models.

These models prepare a shared boundary for the existing CLI and a future
FastAPI/React frontend. They intentionally avoid Typer, Rich, and terminal
types so that application services can return serializable documents.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ReviewTarget = Literal["album", "artist"]
ReviewMode = Literal["create", "translate", "improve"]


class PromptAnalysisContract(BaseModel):
    """Serializable prompt diagnostics shared by review and preview clients."""

    model_config = ConfigDict(frozen=True)

    prompt_name: str = Field(serialization_alias="promptName")
    prompt_version: str = Field(serialization_alias="promptVersion")
    characters: int = Field(ge=0)
    estimated_tokens: int = Field(ge=0, serialization_alias="estimatedTokens")
    budget: int | None = None
    trimmed: bool = False
    budget_diagnostics: dict[str, Any] = Field(
        default_factory=dict,
        serialization_alias="budgetDiagnostics",
    )


class VerificationReportContract(BaseModel):
    """Serializable verification summary for generated metadata."""

    model_config = ConfigDict(frozen=True)

    verified_facts: int = Field(default=0, ge=0, serialization_alias="verifiedFacts")
    probable_facts: int = Field(default=0, ge=0, serialization_alias="probableFacts")
    weak_facts: int = Field(default=0, ge=0, serialization_alias="weakFacts")
    conflicts: int = Field(default=0, ge=0)
    missing_facts: list[str] = Field(default_factory=list, serialization_alias="missingFacts")


class QualityReportContract(BaseModel):
    """Serializable quality summary for generated or edited content."""

    model_config = ConfigDict(frozen=True)

    status: str
    publishable: bool
    critical_validation: str = Field(serialization_alias="criticalValidation")
    editorial_validation: str = Field(serialization_alias="editorialValidation")
    word_count: int = Field(ge=0, serialization_alias="wordCount")
    warnings: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)


class PreviewDocumentContract(BaseModel):
    """Frontend-neutral preview document."""

    model_config = ConfigDict(frozen=True)

    target: ReviewTarget
    artist: str
    album: str | None = None
    current_summary: str | None = Field(default=None, serialization_alias="currentSummary")
    generated_summary: str = Field(serialization_alias="generatedSummary")
    provider: str
    model: str
    generation_time_seconds: float = Field(ge=0, serialization_alias="generationTimeSeconds")
    prompt: PromptAnalysisContract
    quality: QualityReportContract | None = None
    verification: VerificationReportContract | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ReviewDocumentContract(BaseModel):
    """Frontend-neutral review document."""

    model_config = ConfigDict(frozen=True)

    target: ReviewTarget
    artist: str
    album: str | None = None
    current_summary: str = Field(serialization_alias="currentSummary")
    proposed_summary: str = Field(serialization_alias="proposedSummary")
    diff: str
    quality: QualityReportContract
    prompt: PromptAnalysisContract
    verification: VerificationReportContract | None = None
    edited: bool = False
    plan: dict[str, Any] | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class ReviewRequest(BaseModel):
    """Serializable request for a future review endpoint or frontend action."""

    model_config = ConfigDict(frozen=True)

    target: ReviewTarget
    artist: str
    album: str | None = None
    provider: str | None = None
    model: str | None = None
    mode: ReviewMode = "create"


class ReviewResponse(BaseModel):
    """Serializable response for a future review workflow."""

    model_config = ConfigDict(frozen=True)

    document: ReviewDocumentContract
    apply_allowed: bool = Field(serialization_alias="applyAllowed")
    messages: list[str] = Field(default_factory=list)


class ApplyResultContract(BaseModel):
    """Frontend-neutral apply result."""

    model_config = ConfigDict(frozen=True)

    status: str
    artist: str
    album: str
    rating_key: str = Field(serialization_alias="ratingKey")
    backup_created: bool = Field(serialization_alias="backupCreated")
    write_successful: bool = Field(serialization_alias="writeSuccessful")
    verification_passed: bool = Field(serialization_alias="verificationPassed")
    audit_stored: bool = Field(serialization_alias="auditStored")
    backup_path: str | None = Field(default=None, serialization_alias="backupPath")
    audit_path: str | None = Field(default=None, serialization_alias="auditPath")
    message: str


class ConfigurationContract(BaseModel):
    """Sanitized runtime configuration for UI and diagnostics."""

    model_config = ConfigDict(frozen=True)

    plex_configured: bool = Field(serialization_alias="plexConfigured")
    plex_url: str | None = Field(default=None, serialization_alias="plexUrl")
    ai_provider: str = Field(serialization_alias="aiProvider")
    ai_model: str = Field(serialization_alias="aiModel")
    openai_api_key_configured: bool = Field(serialization_alias="openaiApiKeyConfigured")
    discogs_configured: bool = Field(serialization_alias="discogsConfigured")
    lastfm_configured: bool = Field(serialization_alias="lastfmConfigured")
    max_prompt_characters: int = Field(serialization_alias="maxPromptCharacters")


class LibraryEntryContract(BaseModel):
    """Serializable music-library entry for future API responses."""

    model_config = ConfigDict(frozen=True)

    library_id: str = Field(serialization_alias="libraryId")
    title: str
    uuid: str | None = None
    scanner: str | None = None
    agent: str | None = None
    artist_count: int = Field(default=0, ge=0, serialization_alias="artistCount")
    album_count: int = Field(default=0, ge=0, serialization_alias="albumCount")
    track_count: int = Field(default=0, ge=0, serialization_alias="trackCount")
