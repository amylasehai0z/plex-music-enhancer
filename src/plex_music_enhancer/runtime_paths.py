"""Runtime filesystem locations for persistent application data."""

from __future__ import annotations

from os import environ
from pathlib import Path


def runtime_config_dir() -> Path:
    """Return the persistent configuration directory."""
    raw_path = environ.get("PLEX_ENHANCER_CONFIG", "/config")
    path = Path(raw_path).expanduser()
    if path.suffix == ".env" or (path.exists() and path.is_file()):
        return path.parent
    return path


def runtime_exports_dir() -> Path:
    """Return the persistent export directory used for backups and audits."""
    raw_path = environ.get("PLEX_ENHANCER_EXPORTS")
    if raw_path:
        return Path(raw_path).expanduser()
    return runtime_config_dir() / "exports"


def runtime_backups_dir() -> Path:
    """Return the persistent apply-backup directory."""
    return runtime_exports_dir() / "backups"


def runtime_audit_dir() -> Path:
    """Return the persistent apply-audit directory."""
    return runtime_exports_dir() / "audit"


__all__ = [
    "runtime_audit_dir",
    "runtime_backups_dir",
    "runtime_config_dir",
    "runtime_exports_dir",
]
