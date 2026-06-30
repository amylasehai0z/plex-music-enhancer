"""Plex client tests."""

from __future__ import annotations

import pytest_httpx
from pydantic import AnyHttpUrl, SecretStr, TypeAdapter

from plex_music_enhancer.plex import PlexClient


def test_check_connection_success(httpx_mock: pytest_httpx.HTTPXMock) -> None:
    httpx_mock.add_response(
        url="http://localhost:32400/",
        text='<MediaContainer friendlyName="Test Plex" />',
    )
    url = TypeAdapter(AnyHttpUrl).validate_python("http://localhost:32400")

    result = PlexClient(url, SecretStr("token"), timeout_seconds=5).check_connection()

    assert result.ok is True
    assert result.status_code == 200
    assert result.server_name == "Test Plex"


def test_check_connection_unauthorized(httpx_mock: pytest_httpx.HTTPXMock) -> None:
    httpx_mock.add_response(url="http://localhost:32400/", status_code=401)
    url = TypeAdapter(AnyHttpUrl).validate_python("http://localhost:32400")

    result = PlexClient(url, SecretStr("bad-token"), timeout_seconds=5).check_connection()

    assert result.ok is False
    assert result.status_code == 401
    assert result.message == "Authentication failed. Check the Plex token."
