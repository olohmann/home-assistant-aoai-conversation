"""Tests for the Azure AI Speech REST helpers (speech.py)."""

import httpx
import pytest

from custom_components.aoai_conversation.speech import (
    async_list_voices,
    async_recognize,
    async_synthesize,
    build_ssml,
    speech_url,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

BASE = "https://lohmannio.cognitiveservices.azure.com/"


@pytest.mark.parametrize(
    ("base", "kind", "expected"),
    [
        # Custom-subdomain host (the common Azure AI Foundry case) -> service prefix.
        (
            BASE,
            "tts",
            "https://lohmannio.cognitiveservices.azure.com/tts/cognitiveservices/v1",
        ),
        (
            BASE,
            "voices",
            "https://lohmannio.cognitiveservices.azure.com/tts/cognitiveservices/voices/list",
        ),
        (
            BASE,
            "stt",
            "https://lohmannio.cognitiveservices.azure.com/stt/speech/recognition/conversation/cognitiveservices/v1",
        ),
        # Regional hosts encode the service -> no prefix.
        (
            "https://westeurope.tts.speech.microsoft.com/",
            "tts",
            "https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1",
        ),
        (
            "https://westeurope.stt.speech.microsoft.com/",
            "stt",
            "https://westeurope.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1",
        ),
    ],
)
def test_speech_url(base: str, kind: str, expected: str) -> None:
    """URLs are built with the correct host-aware suffixes."""
    assert speech_url(base, kind) == expected
    assert speech_url(base.rstrip("/"), kind) == expected


def test_build_ssml_basic() -> None:
    """A minimal SSML document contains the voice and escaped text."""
    ssml = build_ssml("Hallo & <Welt>", "de-DE-KatjaNeural", "de-DE")
    assert "<voice name='de-DE-KatjaNeural'>" in ssml
    assert "xml:lang='de-DE'" in ssml
    assert "Hallo &amp; &lt;Welt&gt;" in ssml
    assert "<prosody" not in ssml
    assert "express-as" not in ssml


def test_build_ssml_prosody_and_style() -> None:
    """Rate/pitch/style wrap the text in the right SSML elements."""
    ssml = build_ssml(
        "Hi",
        "de-DE-KatjaNeural",
        "de-DE",
        rate="+10%",
        pitch="-2st",
        style="cheerful",
    )
    assert 'rate="+10%"' in ssml
    assert 'pitch="-2st"' in ssml
    assert 'style="cheerful"' in ssml
    assert "mstts:express-as" in ssml


def _mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_async_synthesize_success(hass: HomeAssistant) -> None:
    """Synthesis returns the raw audio bytes and sends SSML headers."""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = request.content
        return httpx.Response(200, content=b"AUDIO")

    audio = await async_synthesize(
        _mock_client(handler),
        BASE,
        "key",
        "<speak/>",
        "audio-24khz-48kbitrate-mono-mp3",
    )

    assert audio == b"AUDIO"
    assert captured["url"].endswith("/cognitiveservices/v1")
    assert captured["headers"]["Ocp-Apim-Subscription-Key"] == "key"
    assert captured["headers"]["Content-Type"] == "application/ssml+xml"
    assert (
        captured["headers"]["X-Microsoft-OutputFormat"]
        == "audio-24khz-48kbitrate-mono-mp3"
    )


async def test_async_synthesize_error(hass: HomeAssistant) -> None:
    """An HTTP error is surfaced as a HomeAssistantError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="denied")

    with pytest.raises(HomeAssistantError):
        await async_synthesize(_mock_client(handler), BASE, "key", "<speak/>", "fmt")


async def test_async_list_voices(hass: HomeAssistant) -> None:
    """Voice listing returns the parsed JSON list."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {"ShortName": "de-DE-KatjaNeural", "LocalName": "Katja"},
                {"ShortName": "en-US-JennyNeural", "LocalName": "Jenny"},
            ],
        )

    voices = await async_list_voices(_mock_client(handler), BASE, "key")

    assert [v["ShortName"] for v in voices] == [
        "de-DE-KatjaNeural",
        "en-US-JennyNeural",
    ]


async def test_async_recognize_success(hass: HomeAssistant) -> None:
    """Recognition returns DisplayText for a successful status."""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200, json={"RecognitionStatus": "Success", "DisplayText": "Licht an"}
        )

    text = await async_recognize(_mock_client(handler), BASE, "key", b"WAV", "de-DE")

    assert text == "Licht an"
    assert "language=de-DE" in captured["url"]
    assert "/speech/recognition/conversation/cognitiveservices/v1" in captured["url"]


async def test_async_recognize_no_match(hass: HomeAssistant) -> None:
    """A non-success status yields None."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"RecognitionStatus": "NoMatch"})

    text = await async_recognize(_mock_client(handler), BASE, "key", b"WAV", "de-DE")

    assert text is None
