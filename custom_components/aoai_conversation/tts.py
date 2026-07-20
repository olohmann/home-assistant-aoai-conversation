"""Text to speech support via Azure AI Speech."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import TYPE_CHECKING, Any, override

from propcache.api import cached_property

from homeassistant.components.tts import (
    ATTR_PREFERRED_FORMAT,
    ATTR_VOICE,
    TextToSpeechEntity,
    TtsAudioType,
    Voice,
)
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    CONF_TTS_API_KEY,
    CONF_TTS_ENDPOINT,
    CONF_TTS_OUTPUT_FORMAT,
    CONF_TTS_PITCH,
    CONF_TTS_RATE,
    CONF_TTS_STYLE,
    CONF_TTS_VOICE,
    DEFAULT_STT_LANGUAGE,
    DEFAULT_TTS_OUTPUT_FORMAT,
    DEFAULT_TTS_VOICE,
    DOMAIN,
    TTS_OUTPUT_FORMATS,
)
from .speech import async_list_voices, async_synthesize, build_ssml

if TYPE_CHECKING:
    from . import OpenAIConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: OpenAIConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up TTS entities."""
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "tts":
            continue

        async_add_entities(
            [AzureSpeechTTSEntity(config_entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class AzureSpeechTTSEntity(TextToSpeechEntity, Entity):
    """Azure AI Speech text-to-speech entity."""

    _attr_supported_options = [ATTR_VOICE, ATTR_PREFERRED_FORMAT]
    # Azure Speech detects/renders the language from the selected voice; expose a
    # broad common set so Home Assistant accepts the entity for any language.
    _attr_supported_languages = [
        "ar-SA",
        "bg-BG",
        "ca-ES",
        "cs-CZ",
        "da-DK",
        "de-DE",
        "de-AT",
        "de-CH",
        "el-GR",
        "en-US",
        "en-GB",
        "en-AU",
        "en-CA",
        "en-IN",
        "es-ES",
        "es-MX",
        "et-EE",
        "fi-FI",
        "fr-FR",
        "fr-CA",
        "he-IL",
        "hi-IN",
        "hr-HR",
        "hu-HU",
        "id-ID",
        "it-IT",
        "ja-JP",
        "ko-KR",
        "lt-LT",
        "lv-LV",
        "ms-MY",
        "nb-NO",
        "nl-NL",
        "pl-PL",
        "pt-BR",
        "pt-PT",
        "ro-RO",
        "ru-RU",
        "sk-SK",
        "sl-SI",
        "sv-SE",
        "th-TH",
        "tr-TR",
        "uk-UA",
        "vi-VN",
        "zh-CN",
        "zh-HK",
        "zh-TW",
    ]
    _attr_default_language = "de-DE"
    _attr_has_entity_name = False

    def __init__(self, entry: OpenAIConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the entity."""
        self.entry = entry
        self.subentry = subentry
        self._attr_unique_id = subentry.subentry_id
        self._attr_name = subentry.title
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=subentry.title,
            manufacturer="Azure AI Speech",
            entry_type=dr.DeviceEntryType.SERVICE,
        )
        self._voices: list[Voice] | None = None

    async def async_get_voices(self) -> list[Voice] | None:
        """Fetch and cache the neural voices for the configured endpoint."""
        if self._voices is not None:
            return self._voices

        endpoint = self.subentry.data.get(CONF_TTS_ENDPOINT)
        api_key = self.subentry.data.get(CONF_TTS_API_KEY)
        if not endpoint or not api_key:
            return None

        try:
            raw = await async_list_voices(
                get_async_client(self.hass), endpoint, api_key
            )
        except HomeAssistantError as err:
            _LOGGER.debug("Could not list Azure Speech voices: %s", err)
            return None

        self._voices = [
            Voice(voice["ShortName"], voice.get("LocalName") or voice["ShortName"])
            for voice in raw
            if voice.get("ShortName")
        ]
        return self._voices

    @callback
    @override
    def async_get_supported_voices(self, language: str) -> list[Voice] | None:
        """Return a list of supported voices for a language."""
        if self._voices is None:
            return None
        prefix = language.split("-")[0].lower()
        return [
            voice for voice in self._voices if voice.voice_id.lower().startswith(prefix)
        ] or self._voices

    @cached_property
    @override
    def default_options(self) -> Mapping[str, Any]:
        """Return a mapping with the default options."""
        return {
            ATTR_VOICE: self.subentry.data.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE),
            ATTR_PREFERRED_FORMAT: "mp3",
        }

    @override
    async def async_internal_added_to_hass(self) -> None:
        """Warm the voice cache once the entity is added."""
        await super().async_internal_added_to_hass()
        await self.async_get_voices()

    @override
    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any]
    ) -> TtsAudioType:
        """Load TTS audio from Azure Speech."""
        endpoint = self.subentry.data.get(CONF_TTS_ENDPOINT)
        api_key = self.subentry.data.get(CONF_TTS_API_KEY)
        if not endpoint or not api_key:
            raise HomeAssistantError(
                "Azure Speech TTS is not configured: set the endpoint URI and "
                "API key for this entity"
            )

        data = {**self.subentry.data, **options}
        voice = options.get(ATTR_VOICE) or data.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE)
        output_format = data.get(CONF_TTS_OUTPUT_FORMAT, DEFAULT_TTS_OUTPUT_FORMAT)
        extension, _content_type = TTS_OUTPUT_FORMATS.get(
            output_format, TTS_OUTPUT_FORMATS[DEFAULT_TTS_OUTPUT_FORMAT]
        )

        ssml = build_ssml(
            message,
            voice,
            language or self._attr_default_language or DEFAULT_STT_LANGUAGE,
            rate=data.get(CONF_TTS_RATE),
            pitch=data.get(CONF_TTS_PITCH),
            style=data.get(CONF_TTS_STYLE),
        )

        audio = await async_synthesize(
            get_async_client(self.hass), endpoint, api_key, ssml, output_format
        )
        return extension, audio
