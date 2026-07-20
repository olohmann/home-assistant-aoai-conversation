"""Test fixtures for the Azure OpenAI Conversation integration."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import httpx
import openai
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aoai_conversation.const import (
    CONF_ENDPOINT,
    DEFAULT_AI_TASK_NAME,
    DEFAULT_CONVERSATION_NAME,
    DEFAULT_STT_NAME,
    DEFAULT_TTS_NAME,
    DOMAIN,
    RECOMMENDED_AI_TASK_OPTIONS,
    RECOMMENDED_CONVERSATION_OPTIONS,
    RECOMMENDED_STT_OPTIONS,
    RECOMMENDED_TTS_OPTIONS,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

TEST_API_KEY = "sk-test-0123456789"
TEST_ENDPOINT = "https://unit-test.services.ai.azure.com/"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading of the custom integration in every test."""
    return


@pytest.fixture(autouse=True)
async def setup_ha_core(hass: HomeAssistant) -> None:
    """Set up the homeassistant core component (registers exposed_entities).

    The ``conversation`` dependency's default agent requires the exposed
    entities store, which is created by the ``homeassistant`` integration.
    """
    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a mock config entry with all four subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Azure OpenAI",
        data={CONF_API_KEY: TEST_API_KEY, CONF_ENDPOINT: TEST_ENDPOINT},
        version=1,
        minor_version=1,
        subentries_data=[
            {
                "subentry_type": "conversation",
                "data": RECOMMENDED_CONVERSATION_OPTIONS,
                "title": DEFAULT_CONVERSATION_NAME,
                "unique_id": None,
            },
            {
                "subentry_type": "ai_task_data",
                "data": RECOMMENDED_AI_TASK_OPTIONS,
                "title": DEFAULT_AI_TASK_NAME,
                "unique_id": None,
            },
            {
                "subentry_type": "stt",
                "data": RECOMMENDED_STT_OPTIONS,
                "title": DEFAULT_STT_NAME,
                "unique_id": None,
            },
            {
                "subentry_type": "tts",
                "data": RECOMMENDED_TTS_OPTIONS,
                "title": DEFAULT_TTS_NAME,
                "unique_id": None,
            },
        ],
    )
    entry.add_to_hass(hass)
    return entry


def build_setup_client() -> MagicMock:
    """Build a client mock suitable for async_setup_entry.

    ``platform_headers`` and ``with_options(...).models.list`` are called
    synchronously inside executor jobs, so they are plain MagicMocks.
    """
    client = MagicMock()
    client.platform_headers = MagicMock(return_value={})
    client.with_options = MagicMock(return_value=client)
    client.models = MagicMock()
    client.models.list = MagicMock(return_value=[])
    return client


@pytest.fixture
def mock_create_client() -> Generator[MagicMock]:
    """Patch create_client (in __init__) so setup succeeds offline."""
    client = build_setup_client()
    with patch(
        "custom_components.aoai_conversation.create_client",
        return_value=client,
    ):
        yield client


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_create_client: MagicMock,
) -> MockConfigEntry:
    """Set up the integration with a mocked client."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry


def make_auth_error() -> openai.AuthenticationError:
    """Return a realistic openai.AuthenticationError instance."""
    request = httpx.Request("GET", f"{TEST_ENDPOINT}openai/v1/models")
    response = httpx.Response(401, request=request)
    return openai.AuthenticationError("invalid key", response=response, body=None)


def make_connection_error() -> openai.APIConnectionError:
    """Return a realistic openai.APIConnectionError instance."""
    request = httpx.Request("GET", f"{TEST_ENDPOINT}openai/v1/models")
    return openai.APIConnectionError(request=request)
