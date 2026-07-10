"""FastAPI REST layer tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from plex_music_enhancer.api.errors import ReviewAPIError
from plex_music_enhancer.api.models import (
    API_VERSION,
    AlbumReviewContent,
    AlbumReviewGenerationResponse,
    AlbumReviewListItem,
    AlbumReviewOverviewResponse,
    AlbumReviewResponse,
    ApplyResponse,
    ArtistReviewResponse,
    DebugMeta,
    PlexSyncStatusResponse,
    PromptAnalysis,
    QualityAnalysis,
    ReviewDocument,
    StoredAlbumReview,
    TokenUsage,
    VerificationAnalysis,
)
from plex_music_enhancer.api.services.configuration import ConfigurationAPIService
from plex_music_enhancer.config import Settings
from plex_music_enhancer.contracts import ConfigurationContract
from plex_music_enhancer.plex.sync import (
    PlexSyncSnapshot,
    SyncedAlbum,
    SyncedArtist,
    SyncedLibrary,
    SyncedTrack,
)
from plex_music_enhancer.review.debug import PROMPT_DEBUG_DUMP_PATH, REVIEW_DEBUG_LOG_PATH
from plex_music_enhancer.services import ConfigurationService
from plex_music_enhancer.services.configuration import PersistentConfigurationStore
from plex_music_enhancer.web.app import create_app
from plex_music_enhancer.web.dependencies import (
    get_album_review_service,
    get_apply_api_service,
    get_configuration_api_service,
    get_plex_sync_service,
    get_review_api_service,
)

pytestmark = pytest.mark.filterwarnings(
    "ignore:Using `httpx` with `starlette.testclient` is deprecated"
)


def test_health_and_version_endpoints() -> None:
    """System endpoints should expose health and version information."""
    client = TestClient(create_app())

    health = client.get("/api/v1/system/health")
    version = client.get("/api/v1/system/version")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert version.status_code == 200
    assert version.json()["apiVersion"] == API_VERSION


def test_config_endpoint_uses_dependency_injection() -> None:
    """Config endpoint should use injectable services."""
    app = create_app()
    app.dependency_overrides[get_configuration_api_service] = lambda: _FakeConfigurationService()
    client = TestClient(app)

    response = client.get("/api/v1/config")

    assert response.status_code == 200
    assert response.json()["configuration"]["aiProvider"] == "openai"


def test_config_update_validates_and_persists_runtime_configuration(tmp_path) -> None:
    """Config updates should validate, persist and return only sanitized values."""
    app = create_app()
    store = PersistentConfigurationStore(tmp_path / ".env")
    settings = Settings(_env_file=None)
    app.dependency_overrides[get_configuration_api_service] = lambda: ConfigurationAPIService(
        ConfigurationService(settings_factory=lambda: settings, store=store)
    )
    client = TestClient(app)

    response = client.put(
        "/api/v1/config",
        json={
            "plexUrl": "http://plex:32400",
            "plexToken": "plex-token",
            "aiProvider": "openai",
            "aiModel": "gpt-5.5",
            "openaiApiKey": "openai-secret",
            "discogsToken": "discogs-secret",
            "lastfmApiKey": "lastfm-secret",
        },
    )

    assert response.status_code == 200
    payload = response.json()["configuration"]
    assert payload["plexConfigured"] is True
    assert payload["plexTokenConfigured"] is True
    assert payload["openaiApiKeyConfigured"] is True
    assert payload["discogsConfigured"] is True
    assert payload["lastfmConfigured"] is True
    assert "openai-secret" not in str(response.json())
    assert "plex-token" not in str(response.json())

    persisted = store.path.read_text(encoding="utf-8")
    assert "PLEX_ENHANCER_PLEX_URL=" in persisted
    assert "PLEX_ENHANCER_AI__API_KEY=" in persisted

    restarted = Settings(_env_file=store.path)
    assert str(restarted.plex_url) == "http://plex:32400/"
    assert restarted.plex_token is not None
    assert restarted.ai.provider == "openai"
    assert restarted.ai.api_key is not None


def test_config_update_rejects_invalid_values(tmp_path) -> None:
    """Invalid configuration updates should return a clear validation error."""
    app = create_app()
    store = PersistentConfigurationStore(tmp_path / ".env")
    settings = Settings(_env_file=None)
    app.dependency_overrides[get_configuration_api_service] = lambda: ConfigurationAPIService(
        ConfigurationService(settings_factory=lambda: settings, store=store)
    )
    client = TestClient(app)

    response = client.put("/api/v1/config", json={"plexUrl": "not-a-url"})

    assert response.status_code == 400
    assert response.json()["code"] == "configuration_error"
    assert not store.path.exists()


def test_review_artist_endpoint() -> None:
    """Artist review endpoint should return the shared API ReviewDocument."""
    app = create_app()
    app.dependency_overrides[get_review_api_service] = lambda: _FakeReviewService()
    client = TestClient(app)

    response = client.post("/api/v1/review/artist", json={"artist": "ABBA"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["document"]["target"] == "artist"
    assert payload["document"]["artist"] == "ABBA"
    assert payload["applyAllowed"] is True


def test_review_album_endpoint() -> None:
    """Album review endpoint should return album review payloads."""
    app = create_app()
    app.dependency_overrides[get_review_api_service] = lambda: _FakeReviewService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/review/album",
        json={"artist": "Jennifer Rush", "album": "Credo"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document"]["target"] == "album"
    assert payload["document"]["album"] == "Credo"


def test_preview_endpoint() -> None:
    """Preview endpoint should return a versioned preview response."""
    app = create_app()
    app.dependency_overrides[get_review_api_service] = lambda: _FakeReviewService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/preview",
        json={"target": "album", "artist": "Jennifer Rush", "album": "Credo"},
    )

    assert response.status_code == 200
    assert response.json()["document"]["prompt"]["evidenceRanking"] == {"Wikipedia": 98}


def test_apply_endpoint() -> None:
    """Apply endpoint should use injectable apply service."""
    app = create_app()
    app.dependency_overrides[get_apply_api_service] = lambda: _FakeApplyService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/apply",
        json={"target": "album", "artist": "Jennifer Rush", "album": "Credo"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SUCCESS"
    assert payload["verificationPassed"] is True


def test_plex_sync_endpoints_use_injected_service() -> None:
    """Plex sync endpoints should start and report sync status."""
    app = create_app()
    app.dependency_overrides[get_plex_sync_service] = lambda: _FakePlexSyncService()
    client = TestClient(app)

    started = client.post("/api/v1/plex/sync")
    status = client.get("/api/v1/plex/sync/status")

    assert started.status_code == 200
    assert started.json()["running"] is True
    assert started.json()["progress"] == 45
    assert status.status_code == 200
    assert status.json()["artists"] == 120
    assert status.json()["tracks"] == 5200


def test_album_review_endpoints_use_injected_service() -> None:
    """Structured album review endpoints should use injectable services."""
    app = create_app()
    app.dependency_overrides[get_album_review_service] = lambda: _FakeAlbumReviewService()
    client = TestClient(app)

    overview = client.get("/api/v1/reviews")
    started = client.post("/api/v1/reviews/generate/200")
    review = client.get("/api/v1/reviews/200")

    assert overview.status_code == 200
    assert overview.json()["albums"][0]["reviewStatus"] == "present"
    assert overview.json()["generatedReviews"] == 1
    assert started.status_code == 200
    assert started.json() == {"status": "started", "albumId": "200"}
    assert review.status_code == 200
    assert review.json()["content"]["rating"] == 88


def test_artist_endpoints_use_plex_sync_snapshot() -> None:
    """Artist endpoints should expose synchronized Plex artist aggregates."""
    app = create_app()
    app.dependency_overrides[get_plex_sync_service] = lambda: _FakePlexSyncService()
    app.dependency_overrides[get_album_review_service] = lambda: _FakeAlbumReviewService()
    client = TestClient(app)

    artists = client.get("/api/v1/artists")
    detail = client.get("/api/v1/artists/100")

    assert artists.status_code == 200
    assert artists.json() == [
        {
            "ratingKey": "100",
            "title": "Nina Simone",
            "library": "Music",
            "albumCount": 2,
            "trackCount": 3,
            "summaryPresent": False,
            "plannedAction": None,
        }
    ]
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["title"] == "Nina Simone"
    assert payload["albumCount"] == 2
    assert payload["trackCount"] == 3
    assert [album["title"] for album in payload["albums"]] == ["Pastel Blues", "Wild Is the Wind"]
    assert payload["tracks"] == ["Be My Husband", "Sinnerman", "Wild Is the Wind"]
    assert payload["reviews"][0]["content"]["rating"] == 88


def test_error_handler_maps_api_errors() -> None:
    """API errors should map to configured HTTP status codes."""
    app = create_app()
    app.dependency_overrides[get_review_api_service] = lambda: _FailingReviewService()
    client = TestClient(app)

    response = client.post("/api/v1/review/artist", json={"artist": "ABBA"})

    assert response.status_code == 422
    assert response.json()["code"] == "review_error"


def test_validation_errors_use_http_400() -> None:
    """Request validation should use the configured 400 response."""
    app = create_app()
    app.dependency_overrides[get_review_api_service] = lambda: _FakeReviewService()
    client = TestClient(app)

    response = client.post("/api/v1/review/album", json={"artist": "ABBA"})

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_openapi_is_generated() -> None:
    """FastAPI should generate OpenAPI for the versioned REST API."""
    client = TestClient(create_app())

    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/system/health" in response.json()["paths"]
    assert "/api/v1/review/artist" in response.json()["paths"]


def test_frontend_is_served_when_built() -> None:
    """FastAPI should serve the built SPA from the same process."""
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Plex Music Enhancer" in response.text


def test_frontend_logo_is_served_when_built() -> None:
    """FastAPI should serve Vite public logo assets from the same process."""
    client = TestClient(create_app())

    response = client.get("/logo/plex-music-enhancer-logo.svg")

    assert response.status_code == 200
    assert "svg" in response.text


def test_log_endpoints_use_existing_debug_files() -> None:
    """Log endpoints should expose the same debug files used by the CLI."""
    REVIEW_DEBUG_LOG_PATH.write_text("review log", encoding="utf-8")
    PROMPT_DEBUG_DUMP_PATH.write_text("prompt log", encoding="utf-8")
    client = TestClient(create_app())

    review_response = client.get("/api/v1/logs/review")
    prompt_response = client.get("/api/v1/logs/prompt")

    assert review_response.status_code == 200
    assert review_response.json()["content"] == "review log"
    assert prompt_response.status_code == 200
    assert prompt_response.json()["content"] == "prompt log"


def test_debug_endpoints_expose_developer_analysis() -> None:
    """Debug endpoints should expose backend developer-mode analysis."""
    client = TestClient(create_app())

    prompt_response = client.get("/api/v1/debug/prompt")
    explain_response = client.get("/api/v1/debug/explain")
    doctor_response = client.get("/api/v1/debug/doctor")

    assert prompt_response.status_code == 200
    assert "stats" in prompt_response.json()
    assert explain_response.status_code == 200
    assert "recommendations" in explain_response.json()
    assert doctor_response.status_code == 200
    assert "checks" in doctor_response.json()


class _FakeConfigurationService:
    """Fake configuration API service."""

    def configuration(self):
        """Return fake configuration."""
        from plex_music_enhancer.api.models import ConfigurationResponse

        return ConfigurationResponse(
            configuration=ConfigurationContract(
                plex_configured=True,
                plex_url="http://localhost:32400",
                ai_provider="openai",
                ai_model="gpt-5.5",
                openai_api_key_configured=True,
                discogs_configured=False,
                lastfm_configured=False,
                max_prompt_characters=20000,
            ).model_dump(by_alias=True)
        )


class _FakeReviewService:
    """Fake review API service."""

    def review(self, request):
        """Return fake review response."""
        document = _api_review_document(target=getattr(request, "target", None) or "album")
        if request.__class__.__name__.startswith("Artist"):
            document = _api_review_document(target="artist", album=None, artist=request.artist)
            return ArtistReviewResponse(document=document, apply_allowed=True)
        return AlbumReviewResponse(document=document, apply_allowed=True)


class _FailingReviewService:
    """Fake failing review service."""

    def review(self, request):
        """Raise an API error."""
        raise ReviewAPIError("Review failed.")


class _FakeApplyService:
    """Fake apply API service."""

    def apply(self, request):
        """Return fake apply response."""
        return ApplyResponse(
            status="SUCCESS",
            artist=request.artist,
            album=request.album or "artist",
            rating_key="42",
            backup_created=True,
            write_successful=True,
            verification_passed=True,
            audit_stored=True,
            message="ok",
            review=_api_review_document(
                target=request.target, artist=request.artist, album=request.album
            ),
        )


class _FakePlexSyncService:
    """Fake Plex sync API service."""

    def start(self) -> PlexSyncStatusResponse:
        """Return fake running status."""
        return PlexSyncStatusResponse(
            running=True,
            progress=45,
            libraries=1,
            artists=120,
            albums=450,
            tracks=5200,
        )

    def status(self) -> PlexSyncStatusResponse:
        """Return fake persisted status."""
        return PlexSyncStatusResponse(
            running=False,
            progress=100,
            libraries=1,
            artists=120,
            albums=450,
            tracks=5200,
        )

    def snapshot(self) -> PlexSyncSnapshot:
        """Return a fake persisted sync snapshot."""
        return PlexSyncSnapshot(
            synced_at=datetime(2026, 1, 1, tzinfo=UTC),
            libraries=[
                SyncedLibrary(
                    library_id="1",
                    title="Music",
                    uuid="library-uuid",
                    scanner="Plex Music",
                    agent="Plex Music",
                )
            ],
            artists=[
                SyncedArtist(
                    rating_key="100",
                    title="Nina Simone",
                    guid="plex://artist/100",
                    library_id="1",
                    library_title="Music",
                )
            ],
            albums=[
                SyncedAlbum(
                    rating_key="200",
                    title="Pastel Blues",
                    parent_artist="Nina Simone",
                    guid="plex://album/200",
                    year=1965,
                    library_id="1",
                    library_title="Music",
                ),
                SyncedAlbum(
                    rating_key="201",
                    title="Wild Is the Wind",
                    parent_artist="Nina Simone",
                    guid="plex://album/201",
                    year=1966,
                    library_id="1",
                    library_title="Music",
                ),
            ],
            tracks=[
                SyncedTrack(
                    rating_key="300",
                    title="Be My Husband",
                    parent_artist="Nina Simone",
                    parent_album="Pastel Blues",
                    guid="plex://track/300",
                    duration=200000,
                    index=1,
                    library_id="1",
                    library_title="Music",
                ),
                SyncedTrack(
                    rating_key="301",
                    title="Sinnerman",
                    parent_artist="Nina Simone",
                    parent_album="Pastel Blues",
                    guid="plex://track/301",
                    duration=600000,
                    index=2,
                    library_id="1",
                    library_title="Music",
                ),
                SyncedTrack(
                    rating_key="302",
                    title="Wild Is the Wind",
                    parent_artist="Nina Simone",
                    parent_album="Wild Is the Wind",
                    guid="plex://track/302",
                    duration=420000,
                    index=1,
                    library_id="1",
                    library_title="Music",
                ),
            ],
        )


class _FakeAlbumReviewService:
    """Fake structured album review service."""

    def start_generation(self, album_id: str) -> AlbumReviewGenerationResponse:
        """Return fake generation start response."""
        return AlbumReviewGenerationResponse(status="started", album_id=album_id)

    def get_review(self, album_id: str) -> StoredAlbumReview:
        """Return a fake stored review."""
        return _stored_album_review(album_id=album_id)

    def reviews(self) -> dict[str, StoredAlbumReview]:
        """Return fake stored reviews."""
        return {"200": _stored_album_review(album_id="200")}

    def overview(self) -> AlbumReviewOverviewResponse:
        """Return a fake review overview."""
        review = _stored_album_review(album_id="200")
        return AlbumReviewOverviewResponse(
            generated_reviews=1,
            average_rating=88,
            albums=[
                AlbumReviewListItem(
                    album_id="200",
                    artist="Nina Simone",
                    album="Pastel Blues",
                    year=1965,
                    track_count=2,
                    review_status="present",
                    rating=88,
                    summary=review.content.summary,
                    review=review,
                )
            ],
        )


def _api_review_document(
    *,
    target: str = "album",
    artist: str = "Jennifer Rush",
    album: str | None = "Credo",
) -> ReviewDocument:
    """Return a fake API ReviewDocument."""
    return ReviewDocument(
        target=target,
        artist=artist,
        album=album,
        rating_key="42",
        current_summary="Alt.",
        generated_summary="Neu.",
        proposed_summary="Neu.",
        unified_diff="--- old\n+++ new",
        qa=QualityAnalysis(
            status="PASS",
            critical_validation="PASS",
            editorial_validation="PASS",
            publishable=True,
            word_count=120,
        ),
        editorial={},
        verification=VerificationAnalysis(),
        prompt=PromptAnalysis(
            name="artist_biography" if target == "artist" else "album_summary",
            version="1.0",
            characters=100,
            estimated_tokens=25,
            budget=20000,
            evidence_ranking={"Wikipedia": 98},
        ),
        debug=DebugMeta(
            provider="openai",
            model="gpt-5.5",
            generation_time_seconds=0.2,
            token_usage=TokenUsage(prompt_tokens=10, completion_tokens=20),
        ),
        provider="openai",
        model="gpt-5.5",
        context={"generatedAt": datetime(2026, 1, 1, tzinfo=UTC).isoformat()},
    )


def _stored_album_review(*, album_id: str) -> StoredAlbumReview:
    """Return a fake structured stored album review."""
    return StoredAlbumReview(
        album_id=album_id,
        artist="Nina Simone",
        album="Pastel Blues",
        year=1965,
        tracks=["1. Be My Husband", "2. Nobody Knows You When You're Down and Out"],
        content=AlbumReviewContent(
            summary="Eine fokussierte Kritik.",
            rating=88,
            genres=["Blues", "Jazz"],
            strengths=["Ausdrucksstarke Stimme"],
            weaknesses=["Kurze Laufzeit"],
            recommended_for="Hörer klassischer Vokalalben.",
            final_verdict="Ein prägnantes, starkes Album.",
        ),
        provider="dummy",
        model="dummy-v1",
        prompt_name="album_review",
        prompt_version="1.0",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
