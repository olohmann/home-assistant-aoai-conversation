"""Azure OpenAI client helpers.

This module isolates the only real difference from the upstream OpenAI
integration: constructing an ``openai.AsyncOpenAI`` client that targets an
Azure OpenAI / Azure AI Foundry resource via its v1 (preview) API surface,
which exposes the Responses API used throughout this integration.
"""

from __future__ import annotations

import openai

from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client

from .const import AZURE_API_VERSION


def normalize_azure_endpoint(endpoint: str) -> str:
    """Return a base URL pointing at the Azure OpenAI v1 API surface.

    Accepts the resource endpoint in any of these shapes and normalizes to
    ``https://<resource>.services.ai.azure.com/openai/v1/``:

    * ``https://<resource>.services.ai.azure.com``
    * ``https://<resource>.services.ai.azure.com/``
    * ``https://<resource>.services.ai.azure.com/openai/v1``
    * a full ``.../openai/v1/`` URL (returned unchanged)
    """
    base = endpoint.strip().rstrip("/")
    if base.endswith("/openai/v1"):
        return f"{base}/"
    return f"{base}/openai/v1/"


def create_client(
    hass: HomeAssistant, api_key: str, endpoint: str
) -> openai.AsyncOpenAI:
    """Create an ``AsyncOpenAI`` client configured for Azure OpenAI."""
    return openai.AsyncOpenAI(
        base_url=normalize_azure_endpoint(endpoint),
        api_key=api_key,
        default_query={"api-version": AZURE_API_VERSION},
        http_client=get_async_client(hass),
    )
