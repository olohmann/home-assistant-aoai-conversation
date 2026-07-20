"""Tests for the Azure client helpers."""

import pytest

from custom_components.aoai_conversation.client import (
    create_client,
    normalize_azure_endpoint,
)
from custom_components.aoai_conversation.const import AZURE_API_VERSION
from homeassistant.core import HomeAssistant


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "https://res.services.ai.azure.com",
            "https://res.services.ai.azure.com/openai/v1/",
        ),
        (
            "https://res.services.ai.azure.com/",
            "https://res.services.ai.azure.com/openai/v1/",
        ),
        (
            "  https://res.services.ai.azure.com/  ",
            "https://res.services.ai.azure.com/openai/v1/",
        ),
        (
            "https://res.services.ai.azure.com/openai/v1",
            "https://res.services.ai.azure.com/openai/v1/",
        ),
        (
            "https://res.services.ai.azure.com/openai/v1/",
            "https://res.services.ai.azure.com/openai/v1/",
        ),
    ],
)
def test_normalize_azure_endpoint(raw: str, expected: str) -> None:
    """The endpoint is normalized to the v1 API surface."""
    assert normalize_azure_endpoint(raw) == expected


async def test_create_client_configuration(hass: HomeAssistant) -> None:
    """The client is configured with the Azure base URL and api-version."""
    client = create_client(hass, "sk-key", "https://res.services.ai.azure.com")

    assert str(client.base_url) == "https://res.services.ai.azure.com/openai/v1/"
    assert client.api_key == "sk-key"
    # The api-version is pinned as a default query parameter.
    assert dict(client._custom_query) == {"api-version": AZURE_API_VERSION}
