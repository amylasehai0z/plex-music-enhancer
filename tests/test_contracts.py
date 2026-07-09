"""Shared contract and web-preparation tests."""

from __future__ import annotations

from pydantic import SecretStr

from plex_music_enhancer.config import AISettings, DiscogsSettings, LastFMSettings, Settings
from plex_music_enhancer.contracts import (
    ConfigurationContract,
    PromptAnalysisContract,
    ReviewDocumentContract,
    ReviewRequest,
)
from plex_music_enhancer.services import ConfigurationService


def test_review_contracts_are_frontend_serializable() -> None:
    """Review contracts should expose stable API-friendly aliases."""
    prompt = PromptAnalysisContract(
        prompt_name="artist_biography",
        prompt_version="1.0",
        characters=1200,
        estimated_tokens=300,
        budget=20000,
        trimmed=False,
    )
    document = ReviewDocumentContract(
        target="artist",
        artist="ABBA",
        current_summary="Aktuelle Biografie.",
        proposed_summary="Neue Biografie.",
        diff="--- current\n+++ generated",
        quality={
            "status": "PASS",
            "publishable": True,
            "critical_validation": "PASS",
            "editorial_validation": "PASS",
            "word_count": 140,
        },
        prompt=prompt,
    )

    exported = document.model_dump(by_alias=True)

    assert exported["currentSummary"] == "Aktuelle Biografie."
    assert exported["proposedSummary"] == "Neue Biografie."
    assert exported["prompt"]["promptName"] == "artist_biography"
    assert exported["prompt"]["estimatedTokens"] == 300


def test_review_request_supports_album_and_artist_targets() -> None:
    """Review requests should represent future API inputs without CLI types."""
    album_request = ReviewRequest(target="album", artist="Jennifer Rush", album="Credo")
    artist_request = ReviewRequest(target="artist", artist="ABBA")

    assert album_request.target == "album"
    assert album_request.album == "Credo"
    assert artist_request.target == "artist"
    assert artist_request.album is None


def test_configuration_service_returns_sanitized_contract() -> None:
    """ConfigurationService should expose settings without leaking secrets."""
    settings = Settings(
        _env_file=None,
        plex_url="http://localhost:32400",
        plex_token=SecretStr("plex-token"),
        ai=AISettings(
            provider="openai",
            model="gpt-5.5",
            api_key=SecretStr("openai-key"),
            max_prompt_characters=12000,
        ),
        discogs=DiscogsSettings(token=SecretStr("discogs-token")),
        lastfm=LastFMSettings(api_key=SecretStr("lastfm-key")),
    )
    service = ConfigurationService(settings_factory=lambda: settings)

    snapshot = service.snapshot()
    exported = snapshot.model_dump(by_alias=True)

    assert isinstance(snapshot, ConfigurationContract)
    assert exported["plexConfigured"] is True
    assert exported["plexUrl"] == "http://localhost:32400/"
    assert exported["aiProvider"] == "openai"
    assert exported["aiModel"] == "gpt-5.5"
    assert exported["openaiApiKeyConfigured"] is True
    assert exported["discogsConfigured"] is True
    assert exported["lastfmConfigured"] is True
    assert "openai-key" not in str(exported)
