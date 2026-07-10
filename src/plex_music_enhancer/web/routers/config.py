"""Configuration REST endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends

from plex_music_enhancer.api.models import (
    ConfigurationResponse,
    ConfigurationUpdateRequest,
    PlexConnectionTestRequest,
    PlexConnectionTestResponse,
)
from plex_music_enhancer.api.services.configuration import ConfigurationAPIService
from plex_music_enhancer.web.dependencies import get_configuration_api_service

router = APIRouter()


@router.get("", response_model=ConfigurationResponse)
async def get_config(
    service: Annotated[ConfigurationAPIService, Depends(get_configuration_api_service)],
) -> ConfigurationResponse:
    """Return sanitized runtime configuration."""
    return service.configuration()


@router.put("", response_model=ConfigurationResponse)
async def update_config(
    service: Annotated[ConfigurationAPIService, Depends(get_configuration_api_service)],
    payload: Annotated[ConfigurationUpdateRequest | None, Body()] = None,
) -> ConfigurationResponse:
    """Persist validated runtime configuration and return a sanitized snapshot."""
    return service.update(payload or ConfigurationUpdateRequest())


@router.post("/test-plex", response_model=PlexConnectionTestResponse)
async def test_plex_connection(
    service: Annotated[ConfigurationAPIService, Depends(get_configuration_api_service)],
    payload: Annotated[PlexConnectionTestRequest | None, Body()] = None,
) -> PlexConnectionTestResponse:
    """Test Plex connectivity without persisting credentials."""
    return service.test_plex_connection(payload or PlexConnectionTestRequest())
