"""Tests for setting up and unloading the config entry."""

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import build_setup_client, make_auth_error, make_connection_error


async def test_setup_and_unload(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """A config entry sets up and unloads cleanly."""
    entry = setup_integration
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not None

    # One entity per subentry platform.
    entity_registry = er.async_get(hass)
    domains = {e.domain for e in entity_registry.entities.values()}
    assert {"conversation", "ai_task", "stt", "tts"} <= domains
    assert hass.states.get("conversation.azure_openai_conversation") is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def _setup_with_client_error(
    hass: HomeAssistant, entry: MockConfigEntry, error: Exception
) -> None:
    """Set up the entry with a client whose models.list raises ``error``."""
    client = build_setup_client()
    client.models.list.side_effect = error
    with patch(
        "custom_components.aoai_conversation.create_client",
        return_value=client,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_setup_auth_error_triggers_reauth(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """An authentication error puts the entry into the auth-error state."""
    await _setup_with_client_error(hass, mock_config_entry, make_auth_error())
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_connection_error_retries(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A connection error puts the entry into the retry state."""
    await _setup_with_client_error(hass, mock_config_entry, make_connection_error())
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
