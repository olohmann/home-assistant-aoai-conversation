"""Azure AI Speech REST client helpers.

STT and TTS in this integration are hard-wired to **Azure AI Speech** (not the
OpenAI audio endpoints). The Speech endpoint differs per install (custom
subdomain, e.g. ``https://<name>.cognitiveservices.azure.com/``, or a regional
host), so the base endpoint URI and API key are configured per entity.

All calls are plain REST over an ``httpx.AsyncClient`` -- no binary Speech SDK is
required. Authentication uses the ``Ocp-Apim-Subscription-Key`` header.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
from xml.sax.saxutils import escape

import httpx

from homeassistant.exceptions import HomeAssistantError

from .const import LOGGER

# REST path suffixes. Regional hosts (``<region>.tts|stt.speech.microsoft.com``)
# encode the service in the hostname and use bare suffixes; custom-domain /
# private-endpoint hosts (``<name>.cognitiveservices.azure.com``) share one host
# and therefore require a ``tts/`` or ``stt/`` service prefix.
_SUFFIX_TTS = "cognitiveservices/v1"
_SUFFIX_VOICES = "cognitiveservices/voices/list"
_SUFFIX_STT = "speech/recognition/conversation/cognitiveservices/v1"

# Speech recognition succeeds only for this status.
_STT_SUCCESS = "Success"


def speech_url(base: str, kind: str) -> str:
    """Return the full Speech REST URL for ``kind`` from a base endpoint.

    ``kind`` is one of ``"tts"``, ``"voices"`` or ``"stt"``. Works for both a
    regional host (``https://<region>.tts.speech.microsoft.com/``) and a
    custom-subdomain host (``https://<name>.cognitiveservices.azure.com/``); the
    latter needs a ``tts/`` / ``stt/`` service prefix, which is added
    automatically.
    """
    root = base.strip().rstrip("/")
    host = urlparse(root).netloc.lower()
    regional_tts = host.endswith(".tts.speech.microsoft.com")
    regional_stt = host.endswith(".stt.speech.microsoft.com")

    if kind == "tts":
        prefix = "" if regional_tts else "tts/"
        return f"{root}/{prefix}{_SUFFIX_TTS}"
    if kind == "voices":
        prefix = "" if regional_tts else "tts/"
        return f"{root}/{prefix}{_SUFFIX_VOICES}"
    if kind == "stt":
        prefix = "" if regional_stt else "stt/"
        return f"{root}/{prefix}{_SUFFIX_STT}"
    raise ValueError(f"Unknown Speech URL kind: {kind}")


def build_ssml(
    message: str,
    voice: str,
    language: str,
    *,
    rate: str | None = None,
    pitch: str | None = None,
    style: str | None = None,
) -> str:
    """Build an SSML document for a single-voice synthesis request."""
    inner = escape(message)

    if style:
        # mstts express-as requires the mstts namespace, declared on <speak>.
        inner = (
            f'<mstts:express-as style="{escape(style, {chr(34): "&quot;"})}">'
            f"{inner}</mstts:express-as>"
        )

    if rate is not None or pitch is not None:
        attrs = ""
        if rate is not None:
            attrs += f' rate="{escape(rate, {chr(34): "&quot;"})}"'
        if pitch is not None:
            attrs += f' pitch="{escape(pitch, {chr(34): "&quot;"})}"'
        inner = f"<prosody{attrs}>{inner}</prosody>"

    return (
        "<speak version='1.0' "
        "xmlns='http://www.w3.org/2001/10/synthesis' "
        "xmlns:mstts='https://www.w3.org/2001/mstts' "
        f"xml:lang='{escape(language)}'>"
        f"<voice name='{escape(voice)}'>{inner}</voice>"
        "</speak>"
    )


async def async_synthesize(
    client: httpx.AsyncClient,
    base: str,
    api_key: str,
    ssml: str,
    output_format: str,
) -> bytes:
    """Synthesize speech from SSML and return the raw audio bytes."""
    try:
        response = await client.post(
            speech_url(base, "tts"),
            headers={
                "Ocp-Apim-Subscription-Key": api_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": output_format,
                "User-Agent": "home-assistant-aoai-conversation",
            },
            content=ssml.encode("utf-8"),
            timeout=30.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as err:
        raise HomeAssistantError(
            f"Azure Speech TTS request failed ({err.response.status_code}): "
            f"{err.response.text}"
        ) from err
    except httpx.HTTPError as err:
        raise HomeAssistantError(f"Azure Speech TTS request failed: {err}") from err

    return response.content


async def async_list_voices(
    client: httpx.AsyncClient, base: str, api_key: str
) -> list[dict[str, Any]]:
    """Return the list of available neural voices for the endpoint."""
    try:
        response = await client.get(
            speech_url(base, "voices"),
            headers={
                "Ocp-Apim-Subscription-Key": api_key,
                "User-Agent": "home-assistant-aoai-conversation",
            },
            timeout=30.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as err:
        raise HomeAssistantError(
            f"Azure Speech voice list failed ({err.response.status_code}): "
            f"{err.response.text}"
        ) from err
    except httpx.HTTPError as err:
        raise HomeAssistantError(f"Azure Speech voice list failed: {err}") from err

    data = response.json()
    if not isinstance(data, list):
        raise HomeAssistantError("Unexpected Azure Speech voice list response")
    return data


async def async_recognize(
    client: httpx.AsyncClient,
    base: str,
    api_key: str,
    wav_audio: bytes,
    language: str,
) -> str | None:
    """Recognize a short WAV clip and return the transcript, or ``None``.

    Uses the short-audio, one-shot recognition endpoint (suitable for the brief
    voice commands issued through Home Assistant Assist).
    """
    try:
        response = await client.post(
            speech_url(base, "stt"),
            params={"language": language, "format": "detailed"},
            headers={
                "Ocp-Apim-Subscription-Key": api_key,
                "Content-Type": ("audio/wav; codecs=audio/pcm; samplerate=16000"),
                "Accept": "application/json",
                "User-Agent": "home-assistant-aoai-conversation",
            },
            content=wav_audio,
            timeout=30.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as err:
        raise HomeAssistantError(
            f"Azure Speech STT request failed ({err.response.status_code}): "
            f"{err.response.text}"
        ) from err
    except httpx.HTTPError as err:
        raise HomeAssistantError(f"Azure Speech STT request failed: {err}") from err

    result = response.json()
    status = result.get("RecognitionStatus")
    if status != _STT_SUCCESS:
        LOGGER.debug("Azure Speech STT non-success status: %s", status)
        return None
    return result.get("DisplayText")
