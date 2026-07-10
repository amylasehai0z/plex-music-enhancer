"""Versioned internal API models for future FastAPI integration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

API_VERSION = "v1"

ReviewTarget = Literal["album", "artist"]
ReviewMode = Literal["create", "translate", "improve"]


class APIModel(BaseModel):
    """Base model for stable internal API payloads."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)


class ResponseMeta(APIModel):
    """Common response metadata for future API clients."""

    api_version: str = Field(default=API_VERSION, serialization_alias="apiVersion")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        serialization_alias="generatedAt",
    )


class TokenUsage(APIModel):
    """AI token usage reported by a provider."""

    prompt_tokens: int | None = Field(default=None, serialization_alias="promptTokens")
    completion_tokens: int | None = Field(default=None, serialization_alias="completionTokens")
    total_tokens: int | None = Field(default=None, serialization_alias="totalTokens")

    def model_post_init(self, __context: object) -> None:
        """Populate total tokens when both parts are available."""
        if (
            self.total_tokens is None
            and self.prompt_tokens is not None
            and self.completion_tokens is not None
        ):
            object.__setattr__(
                self,
                "total_tokens",
                self.prompt_tokens + self.completion_tokens,
            )


class PromptAnalysis(APIModel):
    """Prompt diagnostics included in preview and review documents."""

    name: str
    version: str
    characters: int = Field(ge=0)
    estimated_tokens: int = Field(ge=0, serialization_alias="estimatedTokens")
    budget: int | None = None
    trimmed: bool = False
    budget_diagnostics: dict[str, Any] = Field(
        default_factory=dict,
        serialization_alias="budgetDiagnostics",
    )
    decisions: dict[str, list[str]] = Field(default_factory=dict)
    quality: dict[str, Any] = Field(default_factory=dict)
    efficiency: int | None = None
    utilization: dict[str, Any] = Field(default_factory=dict)
    evidence_ranking: dict[str, int] = Field(
        default_factory=dict,
        serialization_alias="evidenceRanking",
    )
    evidence_coverage: dict[str, Any] = Field(
        default_factory=dict,
        serialization_alias="evidenceCoverage",
    )
    editorial_coverage: dict[str, Any] = Field(
        default_factory=dict,
        serialization_alias="editorialCoverage",
    )
    editorial_balance: dict[str, Any] = Field(
        default_factory=dict,
        serialization_alias="editorialBalance",
    )
    missed_opportunities: list[str] = Field(
        default_factory=list,
        serialization_alias="missedOpportunities",
    )


class QualityAnalysis(APIModel):
    """Unified review quality analysis."""

    status: str
    critical_validation: str = Field(serialization_alias="criticalValidation")
    editorial_validation: str = Field(serialization_alias="editorialValidation")
    publishable: bool
    word_count: int = Field(ge=0, serialization_alias="wordCount")
    checks: dict[str, bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    overall_score: int | None = Field(default=None, serialization_alias="overallScore")
    overall_level: str | None = Field(default=None, serialization_alias="overallLevel")


class EditorialAnalysis(APIModel):
    """Editorial QA details for generated text."""

    score: int | None = None
    level: str | None = None
    recommendations: list[str] = Field(default_factory=list)
    missing_topics: list[str] = Field(default_factory=list, serialization_alias="missingTopics")
    style_metrics: dict[str, Any] = Field(default_factory=dict, serialization_alias="styleMetrics")
    editorial_metrics: dict[str, Any] = Field(
        default_factory=dict,
        serialization_alias="editorialMetrics",
    )


class VerificationAnalysis(APIModel):
    """Fact verification summary for generated text."""

    verified_facts: int = Field(default=0, ge=0, serialization_alias="verifiedFacts")
    probable_facts: int = Field(default=0, ge=0, serialization_alias="probableFacts")
    weak_facts: int = Field(default=0, ge=0, serialization_alias="weakFacts")
    conflicting_facts: int = Field(default=0, ge=0, serialization_alias="conflictingFacts")
    unknown_facts: int = Field(default=0, ge=0, serialization_alias="unknownFacts")
    coverage_score: int = Field(default=100, ge=0, le=100, serialization_alias="coverageScore")
    conflicts: list[str] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list, serialization_alias="missingFacts")


class ProviderInfo(APIModel):
    """Provider metadata for future diagnostics endpoints."""

    name: str
    configured: bool
    available: bool | None = None
    model: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class DebugMeta(APIModel):
    """Structured debug metadata shared by CLI and future REST clients."""

    provider: str
    model: str
    generation_time_seconds: float = Field(ge=0, serialization_alias="generationTimeSeconds")
    token_usage: TokenUsage = Field(default_factory=TokenUsage, serialization_alias="tokenUsage")
    source_count: int = Field(default=0, ge=0, serialization_alias="sourceCount")
    raw: dict[str, Any] = Field(default_factory=dict)


class ReviewDocument(APIModel):
    """Central API exchange document for preview, review, JSON, and future REST."""

    api_version: str = Field(default=API_VERSION, serialization_alias="apiVersion")
    target: ReviewTarget
    mode: ReviewMode = "create"
    artist: str
    album: str | None = None
    rating_key: str | None = Field(default=None, serialization_alias="ratingKey")
    current_summary: str = Field(serialization_alias="currentSummary")
    generated_summary: str = Field(serialization_alias="generatedSummary")
    proposed_summary: str = Field(serialization_alias="proposedSummary")
    unified_diff: str = Field(serialization_alias="unifiedDiff")
    qa: QualityAnalysis
    editorial: EditorialAnalysis
    verification: VerificationAnalysis
    prompt: PromptAnalysis
    debug: DebugMeta
    provider: str
    model: str
    edited: bool = False
    plan: dict[str, Any] | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class PreviewRequest(APIModel):
    """Request model for a future preview operation."""

    target: ReviewTarget
    artist: str
    album: str | None = None
    provider: str | None = None
    model: str | None = None
    mode: ReviewMode = "create"


class PreviewResponse(APIModel):
    """Response model for a future preview operation."""

    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    document: ReviewDocument


class AlbumReviewRequest(APIModel):
    """Request model for album review creation."""

    artist: str
    album: str
    provider: str | None = None
    model: str | None = None
    mode: ReviewMode = "create"


class ArtistReviewRequest(APIModel):
    """Request model for artist review creation."""

    artist: str
    provider: str | None = None
    model: str | None = None


class AlbumReviewResponse(APIModel):
    """Response model for album review creation."""

    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    document: ReviewDocument
    apply_allowed: bool = Field(serialization_alias="applyAllowed")
    messages: list[str] = Field(default_factory=list)


class ArtistReviewResponse(APIModel):
    """Response model for artist review creation."""

    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    document: ReviewDocument
    apply_allowed: bool = Field(serialization_alias="applyAllowed")
    messages: list[str] = Field(default_factory=list)


class ApplyRequest(APIModel):
    """Request model for a future apply operation."""

    target: ReviewTarget
    artist: str
    album: str | None = None
    provider: str | None = None
    model: str | None = None
    mode: ReviewMode = "create"
    force: bool = False


class ApplyResponse(APIModel):
    """Response model for a future apply operation."""

    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    status: str
    artist: str
    album: str
    rating_key: str = Field(serialization_alias="ratingKey")
    backup_created: bool = Field(serialization_alias="backupCreated")
    write_successful: bool = Field(serialization_alias="writeSuccessful")
    verification_passed: bool = Field(serialization_alias="verificationPassed")
    audit_stored: bool = Field(serialization_alias="auditStored")
    message: str
    review: ReviewDocument


class LibraryArtist(APIModel):
    """Artist entry for future library API responses."""

    rating_key: str = Field(serialization_alias="ratingKey")
    title: str
    library: str | None = None
    album_count: int = Field(default=0, ge=0, serialization_alias="albumCount")
    track_count: int = Field(default=0, ge=0, serialization_alias="trackCount")
    summary_present: bool = Field(default=False, serialization_alias="summaryPresent")
    planned_action: str | None = Field(default=None, serialization_alias="plannedAction")


class LibraryArtistDetail(APIModel):
    """Artist detail assembled from the persisted Plex sync snapshot."""

    rating_key: str = Field(serialization_alias="ratingKey")
    title: str
    library: str | None = None
    album_count: int = Field(default=0, ge=0, serialization_alias="albumCount")
    track_count: int = Field(default=0, ge=0, serialization_alias="trackCount")
    albums: list[LibraryAlbum] = Field(default_factory=list)
    tracks: list[str] = Field(default_factory=list)
    reviews: list[StoredAlbumReview] = Field(default_factory=list)


class LibraryAlbum(APIModel):
    """Album entry for future library API responses."""

    rating_key: str = Field(serialization_alias="ratingKey")
    title: str
    artist: str
    artist_id: str | None = Field(default=None, serialization_alias="artistId")
    library: str | None = None
    year: int | None = None
    track_count: int = Field(default=0, ge=0, serialization_alias="trackCount")
    genres: list[str] = Field(default_factory=list)
    cover_url: str | None = Field(default=None, serialization_alias="coverUrl")
    review_status: str = Field(default="missing", serialization_alias="reviewStatus")
    summary_present: bool = Field(default=False, serialization_alias="summaryPresent")
    planned_action: str | None = Field(default=None, serialization_alias="plannedAction")


class LibraryAlbumDetail(LibraryAlbum):
    """Album detail assembled from the persisted Plex sync snapshot."""

    tracks: list[str] = Field(default_factory=list)
    review: StoredAlbumReview | None = None


class StatisticsResponse(APIModel):
    """Aggregated statistics for future dashboard endpoints."""

    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    libraries: int = Field(default=0, ge=0)
    artists: int = Field(default=0, ge=0)
    albums: int = Field(default=0, ge=0)
    tracks: int = Field(default=0, ge=0)
    reviews: int = Field(default=0, ge=0)
    average_rating: float | None = Field(default=None, serialization_alias="averageRating")
    cache_entries: int = Field(default=0, ge=0, serialization_alias="cacheEntries")


class PlexSyncStatusResponse(APIModel):
    """Current Plex library synchronization status."""

    running: bool = False
    progress: int = Field(default=0, ge=0, le=100)
    libraries: int = Field(default=0, ge=0)
    artists: int = Field(default=0, ge=0)
    albums: int = Field(default=0, ge=0)
    tracks: int = Field(default=0, ge=0)
    last_sync: datetime | None = Field(default=None, serialization_alias="lastSync")
    error: str | None = None


class AlbumReviewContent(APIModel):
    """Structured AI review content persisted for one album."""

    summary: str
    rating: int = Field(ge=0, le=100)
    genres: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommended_for: str = Field(alias="recommendedFor")
    final_verdict: str = Field(alias="finalVerdict")


class StoredAlbumReview(APIModel):
    """Persisted AI album review."""

    album_id: str = Field(alias="albumId")
    artist: str
    album: str
    year: int | None = None
    tracks: list[str] = Field(default_factory=list)
    content: AlbumReviewContent
    provider: str
    model: str
    prompt_name: str = Field(alias="promptName")
    prompt_version: str = Field(alias="promptVersion")
    created_at: datetime = Field(alias="createdAt")


class AlbumReviewGenerationResponse(APIModel):
    """Response returned when album review generation starts."""

    status: str
    album_id: str = Field(alias="albumId")


class AlbumReviewListItem(APIModel):
    """Album item with review generation status."""

    album_id: str = Field(alias="albumId")
    artist: str
    album: str
    year: int | None = None
    track_count: int = Field(default=0, ge=0, alias="trackCount")
    review_status: str = Field(alias="reviewStatus")
    running: bool = False
    error: str | None = None
    rating: int | None = Field(default=None, ge=0, le=100)
    summary: str | None = None
    review: StoredAlbumReview | None = None


class AlbumReviewOverviewResponse(APIModel):
    """Overview of synchronized albums and their stored review status."""

    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    albums: list[AlbumReviewListItem] = Field(default_factory=list)
    generated_reviews: int = Field(default=0, ge=0, alias="generatedReviews")
    average_rating: float | None = Field(default=None, alias="averageRating")


class ConfigurationResponse(APIModel):
    """Configuration response wrapper for future API clients."""

    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    configuration: dict[str, Any]


class ConfigurationUpdateRequest(APIModel):
    """Request model for persistent runtime configuration updates."""

    plex_url: str | None = Field(default=None, alias="plexUrl")
    plex_token: str | None = Field(default=None, alias="plexToken")
    ai_provider: str | None = Field(default=None, alias="aiProvider")
    ai_model: str | None = Field(default=None, alias="aiModel")
    openai_api_key: str | None = Field(default=None, alias="openaiApiKey")
    discogs_token: str | None = Field(default=None, alias="discogsToken")
    lastfm_api_key: str | None = Field(default=None, alias="lastfmApiKey")


class PlexConnectionTestRequest(APIModel):
    """Request model for testing Plex connectivity without persisting secrets."""

    plex_url: str | None = Field(default=None, alias="plexUrl")
    plex_token: str | None = Field(default=None, alias="plexToken")


class PlexConnectionTestResponse(APIModel):
    """Sanitized Plex connectivity test response."""

    ok: bool
    status_code: int | None = Field(default=None, serialization_alias="statusCode")
    server_name: str | None = Field(default=None, serialization_alias="serverName")
    message: str
