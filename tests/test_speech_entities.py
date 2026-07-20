"""Tests for the Azure Speech STT and TTS entities and their subentry flows."""

import dataclasses
from unittest.mock import patch

import httpx
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aoai_conversation.tts import AzureSpeechTTSEntity
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError

STT_ENDPOINT = "https://lohmannio.cognitiveservices.azure.com/"
TTS_ENDPOINT = "https://lohmannio.cognitiveservices.azure.com/"


def _mock_transport(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_stt_subentry_flow(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The STT subentry flow stores endpoint, key and language."""
    result = await hass.config_entries.subentries.async_init(
        (setup_integration.entry_id, "stt"),
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Speech STT",
            "stt_endpoint": STT_ENDPOINT,
            "stt_api_key": "sttkey",
            "stt_language": "de-DE",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["stt_endpoint"] == STT_ENDPOINT
    assert result["data"]["stt_api_key"] == "sttkey"
    assert result["data"]["stt_language"] == "de-DE"


async def test_tts_subentry_flow_custom_voice(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The TTS subentry flow stores endpoint, key and a custom neural voice."""
    result = await hass.config_entries.subentries.async_init(
        (setup_integration.entry_id, "tts"),
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Speech TTS",
            "tts_endpoint": TTS_ENDPOINT,
            "tts_api_key": "ttskey",
            "tts_voice": "de-DE-ConradNeural",
            "tts_output_format": "audio-24khz-48kbitrate-mono-mp3",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["tts_voice"] == "de-DE-ConradNeural"
    assert result["data"]["tts_endpoint"] == TTS_ENDPOINT


def _tts_entity(setup_integration: MockConfigEntry) -> AzureSpeechTTSEntity:
    subentry = next(
        sub
        for sub in setup_integration.subentries.values()
        if sub.subentry_type == "tts"
    )
    # Inject connection settings the recommended defaults don't carry.
    data = dict(subentry.data)
    data.update(
        {
            "tts_endpoint": TTS_ENDPOINT,
            "tts_api_key": "ttskey",
            "tts_voice": "de-DE-KatjaNeural",
        }
    )
    subentry = dataclasses.replace(subentry, data=data)
    return AzureSpeechTTSEntity(setup_integration, subentry)


async def test_tts_get_audio(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """TTS builds SSML, calls Azure Speech and returns (ext, bytes)."""
    entity = _tts_entity(setup_integration)
    entity.hass = hass

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(200, content=b"MP3DATA")

    with patch(
        "custom_components.aoai_conversation.speech.get_async_client",
        return_value=_mock_transport(handler),
    ):
        ext, audio = await entity.async_get_tts_audio(
            "Hallo Welt", "de-DE", {"voice": "de-DE-KatjaNeural"}
        )

    assert ext == "mp3"
    assert audio == b"MP3DATA"
    assert "de-DE-KatjaNeural" in captured["body"]
    assert "Hallo Welt" in captured["body"]


async def test_tts_get_audio_missing_endpoint_raises(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """TTS with no endpoint configured raises a clear error."""
    subentry = next(
        sub
        for sub in setup_integration.subentries.values()
        if sub.subentry_type == "tts"
    )
    entity = AzureSpeechTTSEntity(setup_integration, subentry)
    entity.hass = hass

    with pytest.raises(HomeAssistantError):
        await entity.async_get_tts_audio("Hallo", "de-DE", {})
