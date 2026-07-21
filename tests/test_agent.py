"""Tests for Foundry agent routing in the conversation entity."""

import dataclasses
from unittest.mock import MagicMock, patch

import openai
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aoai_conversation.conversation import OpenAIConversationEntity
from custom_components.aoai_conversation.entity import _error_message
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError


def _conversation_subentry(entry: MockConfigEntry):
    return next(
        sub for sub in entry.subentries.values() if sub.subentry_type == "conversation"
    )


def test_get_client_model_mode_uses_runtime_data(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """In model mode the shared resource client (runtime_data) is used."""
    subentry = _conversation_subentry(setup_integration)
    subentry = dataclasses.replace(subentry, data={"chat_model": "gpt-4.1-mini"})
    entity = OpenAIConversationEntity(setup_integration, subentry)
    entity.hass = hass

    assert entity._get_client() is setup_integration.runtime_data


def test_get_client_agent_mode_builds_project_client(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """In agent mode a dedicated client for the project endpoint is built + cached."""
    endpoint = "https://res.services.ai.azure.com/api/projects/proj"
    subentry = _conversation_subentry(setup_integration)
    subentry = dataclasses.replace(
        subentry,
        data={"agent_name": "MyHouseAgent", "agent_endpoint": endpoint},
    )
    entity = OpenAIConversationEntity(setup_integration, subentry)
    entity.hass = hass

    sentinel = MagicMock(name="agent_client")
    with patch(
        "custom_components.aoai_conversation.entity.create_client",
        return_value=sentinel,
    ) as mock_create:
        client = entity._get_client()
        # Cached on second call (create_client not called again).
        client_again = entity._get_client()

    assert client is sentinel
    assert client_again is sentinel
    assert client is not setup_integration.runtime_data
    mock_create.assert_called_once()
    # create_client(hass, api_key, endpoint)
    assert mock_create.call_args.args[2] == endpoint


def test_error_message_prefers_body_error_message() -> None:
    """The nested body.error.message is preferred when present."""

    err = openai.OpenAIError("fallback")
    err.body = {"error": {"message": "no device named 'Schrank'"}}
    assert _error_message(err) == "no device named 'Schrank'"


def test_error_message_falls_back_to_message_then_str() -> None:
    """Without a structured body, fall back to .message then str(err)."""

    with_message = openai.OpenAIError("boom")
    with_message.message = "the real reason"
    assert _error_message(with_message) == "the real reason"

    plain = openai.OpenAIError("just a string")
    assert _error_message(plain) == "just a string"


async def test_agent_conversation_thread_created_and_reused(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """A Foundry conversation thread is created once and reused per HA session."""
    endpoint = "https://res.services.ai.azure.com/api/projects/proj"
    subentry = _conversation_subentry(setup_integration)
    subentry = dataclasses.replace(
        subentry, data={"agent_name": "MyAgent", "agent_endpoint": endpoint}
    )
    entity = OpenAIConversationEntity(setup_integration, subentry)
    entity.hass = hass

    with patch(
        "custom_components.aoai_conversation.entity.async_create_conversation",
        return_value="conv_xyz",
    ) as mock_create:
        first = await entity._async_get_agent_conversation("ha-conv-1")
        second = await entity._async_get_agent_conversation("ha-conv-1")
        other = await entity._async_get_agent_conversation("ha-conv-2")

    assert first == "conv_xyz"
    assert second == "conv_xyz"
    assert other == "conv_xyz"
    # Created once for ha-conv-1 (reused), once for ha-conv-2.
    assert mock_create.call_count == 2


async def test_agent_conversation_create_failure_returns_none(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """If thread creation fails, fall back to None (stateless history)."""

    endpoint = "https://res.services.ai.azure.com/api/projects/proj"
    subentry = _conversation_subentry(setup_integration)
    subentry = dataclasses.replace(
        subentry, data={"agent_name": "MyAgent", "agent_endpoint": endpoint}
    )
    entity = OpenAIConversationEntity(setup_integration, subentry)
    entity.hass = hass

    with patch(
        "custom_components.aoai_conversation.entity.async_create_conversation",
        side_effect=HomeAssistantError("boom"),
    ):
        result = await entity._async_get_agent_conversation("ha-conv-1")

    assert result is None
