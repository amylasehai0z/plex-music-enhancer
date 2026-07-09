"""Fact verification for collected album metadata."""

from plex_music_enhancer.verification.models import (
    FactCollection,
    VerificationState,
    VerifiedFact,
)

__all__ = [
    "FactCollection",
    "FactVerifier",
    "VerificationState",
    "VerifiedFact",
    "confidence_for_sources",
]


def __getattr__(name: str) -> object:
    """Lazily expose verifier objects without creating import cycles."""
    if name == "FactVerifier":
        from plex_music_enhancer.verification.verifier import FactVerifier

        return FactVerifier
    if name == "confidence_for_sources":
        from plex_music_enhancer.verification.verifier import confidence_for_sources

        return confidence_for_sources
    raise AttributeError(name)
