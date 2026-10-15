"""Tests for model-specific Responses API request parameters."""

import dataclasses
import json
from typing import Any
from unittest.mock import MagicMock

import httpx
import openai
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aoai_conversation.entity import OpenAIBaseLLMEntity
from homeassistant.components import conversation
from homeassistant.core import HomeAssistant


@pytest.mark.parametrize(
    ("model", "effort", "expected_effort", "sampling"),
    [
        ("gpt-6-luna", None, None, False),
        ("gpt-6-luna-2026-09-22", None, None, False),
        ("gpt-6-luna", "none", None, False),
        ("gpt-6-astra", None, None, True),
        ("gpt-4o", None, None, True),
        ("gpt-4.1-mini", None, None, True),
        ("my-chat-deployment", None, None, True),
        ("gpt-5", None, "low", False),
        ("gpt-5.1", "none", "none", True),
        ("gpt-5.2", "none", "none", True),
        ("gpt-5.2", "high", "high", False),
        ("gpt-5.6", "none", "none", True),
        ("gpt-5.6", "low", "low", False),
        ("gpt-5-pro", "none", "high", False),
        ("o3", None, "low", False),
        ("o4-mini", None, "low", False),
        ("o3", "none", "none", False),
    ],
)
@pytest.mark.parametrize(
    "sampling_options",
    [{}, {"top_p": 0.4, "temperature": 0.2}],
    ids=["defaults", "stored-sampling"],
)
async def test_model_request_parameters(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    model: str,
    effort: str | None,
    expected_effort: str | None,
    sampling: bool,
    sampling_options: dict[str, float],
) -> None:
    """Assert the serialized request omits unsupported optional parameters."""
    requests: list[dict[str, Any]] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/openai/v1/responses"
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream"},
            text="data: [DONE]\n\n",
        )

    subentry = next(
        sub
        for sub in mock_config_entry.subentries.values()
        if sub.subentry_type == "conversation"
    )
    options: dict[str, Any] = {"chat_model": model, **sampling_options}
    if effort is not None:
        options["reasoning_effort"] = effort
    subentry = dataclasses.replace(subentry, data=options)

    chat_log = MagicMock(spec=conversation.ChatLog)
    chat_log.conversation_id = "test-conversation"
    chat_log.content = [conversation.UserContent(content="Hello")]
    chat_log.llm_api = None
    chat_log.unresponded_tool_results = False
    chat_log.async_add_delta_content_stream.side_effect = (
        lambda _entity_id, stream: stream
    )

    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handle_request)) as http_client,
        openai.AsyncOpenAI(
            api_key="test-key",
            base_url="https://unit-test.services.ai.azure.com/openai/v1/",
            http_client=http_client,
        ) as client,
    ):
        mock_config_entry.runtime_data = client
        entity = OpenAIBaseLLMEntity(mock_config_entry, subentry)
        entity.hass = hass
        entity.entity_id = "conversation.test"
        await entity._async_handle_chat_log(chat_log)

    assert len(requests) == 1
    body = requests[0]
    assert body["model"] == model
    assert body["stream"] is True
    assert body["input"] == [{"role": "user", "content": "Hello", "type": "message"}]
    if sampling:
        assert body["top_p"] == sampling_options.get("top_p", 1.0)
        assert body["temperature"] == sampling_options.get("temperature", 1.0)
    else:
        assert "top_p" not in body
        assert "temperature" not in body
    if expected_effort is None:
        assert "reasoning" not in body
        assert "include" not in body
    else:
        assert body["reasoning"] == {"effort": expected_effort, "summary": "auto"}
        assert body["include"] == ["reasoning.encrypted_content"]
    if model.startswith("gpt-5"):
        assert body["text"] == {"verbosity": "medium"}
    else:
        assert "text" not in body
