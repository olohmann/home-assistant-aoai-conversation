"""Tests for the config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aoai_conversation.const import CONF_ENDPOINT, DOMAIN
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import (
    TEST_API_KEY,
    TEST_ENDPOINT,
    make_auth_error,
    make_connection_error,
)

USER_INPUT = {CONF_API_KEY: TEST_API_KEY, CONF_ENDPOINT: TEST_ENDPOINT}


def _flow_client() -> MagicMock:
    """Return a client whose models.list is awaitable (config flow uses await)."""
    client = MagicMock()
    client.models = MagicMock()
    client.models.list = AsyncMock(return_value=[])
    return client


async def test_user_flow_creates_entry_with_subentries(hass: HomeAssistant) -> None:
    """A successful user flow creates the entry and its four subentries."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with (
        patch(
            "custom_components.aoai_conversation.config_flow.create_client",
            return_value=_flow_client(),
        ),
        patch(
            "custom_components.aoai_conversation.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Azure OpenAI"
    assert result["data"] == USER_INPUT

    subentry_types = sorted(sub["subentry_type"] for sub in result["subentries"])
    assert subentry_types == ["ai_task_data", "conversation", "stt", "tts"]


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        (make_auth_error(), "invalid_auth"),
        (make_connection_error(), "cannot_connect"),
        (ValueError("boom"), "unknown"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant, side_effect: Exception, expected_error: str
) -> None:
    """Errors during validation are surfaced on the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    client = MagicMock()
    client.models = MagicMock()
    client.models.list = AsyncMock(side_effect=side_effect)

    with patch(
        "custom_components.aoai_conversation.config_flow.create_client",
        return_value=client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}

    # Recover after fixing the error.
    with (
        patch(
            "custom_components.aoai_conversation.config_flow.create_client",
            return_value=_flow_client(),
        ),
        patch(
            "custom_components.aoai_conversation.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_duplicate_aborts(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A second entry with the same api key and endpoint aborts."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_ai_task_subentry_accepts_custom_image_deployment(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The AI Task subentry flow accepts a custom Azure image deployment name."""
    custom_deployment = "my-azure-gpt-image-2"

    result = await hass.config_entries.subentries.async_init(
        (setup_integration.entry_id, "ai_task_data"),
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    # init step: name + chat model (deployment) + advanced (recommended=False).
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Azure Image Task",
            "chat_model": "gpt-4.1-mini",
            "recommended": False,
        },
    )
    assert result["step_id"] == "additional"

    # additional step: accept defaults.
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["step_id"] == "model"

    # model step: provide a custom image deployment name.
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"image_model": custom_deployment}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["image_model"] == custom_deployment
    assert result["data"]["chat_model"] == "gpt-4.1-mini"


async def test_conversation_subentry_sets_model_in_recommended_mode(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The chat model (deployment) is settable without entering advanced mode."""
    result = await hass.config_entries.subentries.async_init(
        (setup_integration.entry_id, "conversation"),
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["step_id"] == "init"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Azure Conversation",
            "chat_model": "my-gpt4o-deployment",
            "recommended": True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["chat_model"] == "my-gpt4o-deployment"


async def test_conversation_subentry_foundry_agent_mode(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """A conversation can target a Foundry agent instead of a model."""
    result = await hass.config_entries.subentries.async_init(
        (setup_integration.entry_id, "conversation"),
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "House Agent",
            "agent_endpoint": ("https://res.services.ai.azure.com/api/projects/proj"),
            "agent_name": "MyHouseAgent",
            "recommended": True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["agent_name"] == "MyHouseAgent"
    assert result["data"]["agent_endpoint"].endswith("/projects/proj")
    assert "chat_model" not in result["data"]


async def test_conversation_subentry_backend_required(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Neither a model nor an agent is an error."""
    result = await hass.config_entries.subentries.async_init(
        (setup_integration.entry_id, "conversation"),
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"name": "Empty", "recommended": True},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "backend_required"}


async def test_conversation_subentry_backend_conflict(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Both a model and an agent is an error."""
    result = await hass.config_entries.subentries.async_init(
        (setup_integration.entry_id, "conversation"),
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Both",
            "chat_model": "gpt-4.1-mini",
            "agent_endpoint": "https://res.services.ai.azure.com/api/projects/proj",
            "agent_name": "MyHouseAgent",
            "recommended": True,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "backend_conflict"}


async def test_conversation_subentry_agent_requires_endpoint(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """An agent without a project endpoint is an error."""
    result = await hass.config_entries.subentries.async_init(
        (setup_integration.entry_id, "conversation"),
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"name": "NoEndpoint", "agent_name": "MyHouseAgent", "recommended": True},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"agent_endpoint": "agent_endpoint_required"}
