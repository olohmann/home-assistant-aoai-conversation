"""Azure OpenAI client helpers.

This module isolates the only real difference from the upstream OpenAI
integration: constructing an ``openai.AsyncOpenAI`` client that targets an
Azure OpenAI / Azure AI Foundry resource via its v1 (preview) API surface,
which exposes the Responses API used throughout this integration.
"""

from __future__ import annotations

import httpx
import openai

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.httpx_client import get_async_client

from .const import LOGGER


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
    """Create an ``AsyncOpenAI`` client configured for Azure OpenAI.

    The base URL targets the versionless ``/openai/v1/`` surface, which does not
    accept an ``api-version`` query parameter (the service rejects it), so none
    is sent.
    """
    return openai.AsyncOpenAI(
        base_url=normalize_azure_endpoint(endpoint),
        api_key=api_key,
        http_client=get_async_client(hass),
    )


def _conversations_url(endpoint: str, conversation_id: str | None = None) -> str:
    """Return the conversations REST URL for a project endpoint."""
    base = f"{normalize_azure_endpoint(endpoint)}conversations"
    return f"{base}/{conversation_id}" if conversation_id else base


async def async_create_conversation(
    hass: HomeAssistant, endpoint: str, api_key: str
) -> str:
    """Create a server-side conversation (thread) and return its id.

    Used for Foundry hosted-agent mode so the agent keeps context across turns.
    Uses a plain REST call (the pinned openai SDK has no conversations resource).
    """
    client = get_async_client(hass)
    try:
        response = await client.post(
            _conversations_url(endpoint),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={},
            timeout=30.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as err:
        raise HomeAssistantError(
            f"Azure conversation create failed ({err.response.status_code}): "
            f"{err.response.text}"
        ) from err
    except httpx.HTTPError as err:
        raise HomeAssistantError(f"Azure conversation create failed: {err}") from err

    data = response.json()
    conversation_id = data.get("id")
    if not conversation_id:
        raise HomeAssistantError("Azure conversation create returned no id")
    return str(conversation_id)


async def async_delete_conversation(
    hass: HomeAssistant, endpoint: str, api_key: str, conversation_id: str
) -> None:
    """Best-effort delete of a server-side conversation (thread)."""
    client = get_async_client(hass)
    try:
        response = await client.delete(
            _conversations_url(endpoint, conversation_id),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as err:
        # Non-fatal: the thread will expire under Foundry retention anyway.
        LOGGER.debug("Could not delete Azure conversation %s: %s", conversation_id, err)
