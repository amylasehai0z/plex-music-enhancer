"""Configuration REST endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends

from plex_music_enhancer.api.models import ConfigurationResponse
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
    payload: Annotated[dict[str, Any] | None, Body()] = None,
) -> ConfigurationResponse:
    """Return current configuration and echo requested updates for future persistence."""
    response = service.configuration()
    configuration = dict(response.configuration)
    configuration["requestedUpdate"] = payload or {}
    configuration["message"] = "Runtime configuration persistence is not implemented yet."
    return ConfigurationResponse(meta=response.meta, configuration=configuration)
