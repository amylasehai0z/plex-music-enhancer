"""Plex integration package."""

from plex_music_enhancer.plex.audit import (
    AlbumAuditFinding,
    ArtistAuditFinding,
    AuditStatistics,
    LibraryAuditResult,
    MetadataAuditReport,
    PlexAuditError,
    PlexMetadataAuditor,
    SummaryLanguage,
    SummaryPresence,
)
from plex_music_enhancer.plex.capabilities import (
    LibraryCapability,
    ObjectCapabilityAnalysis,
    PlexCapabilityAnalysis,
    PlexCapabilityAnalyzer,
    PlexCapabilityError,
)
from plex_music_enhancer.plex.client import PlexClient, PlexConnectionResult
from plex_music_enhancer.plex.inspector import (
    InspectChild,
    InspectedPlexObject,
    InspectImage,
    InspectTarget,
    PlexInspectError,
    PlexMetadataInspector,
)
from plex_music_enhancer.plex.probe import (
    AlbumWriteVerificationReport,
    PlexProbeError,
    PlexWriteProbe,
    SummaryWriteCapability,
    WriteCapabilityReport,
)
from plex_music_enhancer.plex.scanner import (
    AlbumScanExport,
    AlbumScanItem,
    ArtistScanExport,
    ArtistScanItem,
    MusicLibraryScanExport,
    MusicLibraryStats,
    PlexMusicScanner,
    PlexScannerError,
)

__all__ = [
    "AlbumAuditFinding",
    "AlbumScanExport",
    "AlbumScanItem",
    "AlbumWriteVerificationReport",
    "ArtistAuditFinding",
    "ArtistScanExport",
    "ArtistScanItem",
    "AuditStatistics",
    "InspectChild",
    "InspectImage",
    "InspectTarget",
    "InspectedPlexObject",
    "LibraryAuditResult",
    "LibraryCapability",
    "MetadataAuditReport",
    "MusicLibraryScanExport",
    "MusicLibraryStats",
    "ObjectCapabilityAnalysis",
    "PlexAuditError",
    "PlexCapabilityAnalysis",
    "PlexCapabilityAnalyzer",
    "PlexCapabilityError",
    "PlexClient",
    "PlexConnectionResult",
    "PlexInspectError",
    "PlexMetadataInspector",
    "PlexMetadataAuditor",
    "PlexMusicScanner",
    "PlexProbeError",
    "PlexWriteProbe",
    "PlexScannerError",
    "SummaryWriteCapability",
    "SummaryLanguage",
    "SummaryPresence",
    "WriteCapabilityReport",
]
