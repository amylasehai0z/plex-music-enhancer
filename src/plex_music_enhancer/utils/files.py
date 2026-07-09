"""Filesystem helpers."""

from __future__ import annotations

from contextlib import suppress
from os import replace, unlink
from pathlib import Path
from tempfile import NamedTemporaryFile


def write_text_atomic(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Atomically write text to a file in the same directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            "w",
            encoding=encoding,
            dir=path.parent,
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)

        replace(temporary_path, path)
    except Exception:
        if temporary_path is not None:
            with suppress(FileNotFoundError):
                unlink(temporary_path)
        raise
