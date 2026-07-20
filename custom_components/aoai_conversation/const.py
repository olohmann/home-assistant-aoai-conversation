"""Constants for the Azure OpenAI Conversation integration."""

import logging
from typing import Any

from homeassistant.const import CONF_LLM_HASS_API, CONF_PROMPT
from homeassistant.helpers import llm

DOMAIN = "aoai_conversation"
LOGGER: logging.Logger = logging.getLogger(__package__)

DEFAULT_CONVERSATION_NAME = "Azure OpenAI Conversation"
DEFAULT_AI_TASK_NAME = "Azure OpenAI AI Task"
DEFAULT_STT_NAME = "Azure Speech STT"
DEFAULT_TTS_NAME = "Azure Speech TTS"
DEFAULT_NAME = "Azure OpenAI Conversation"

# Azure-specific connection settings.
CONF_ENDPOINT = "endpoint"
# The v1 preview surface exposes the Responses API used by this integration.
AZURE_API_VERSION = "preview"

CONF_CHAT_MODEL = "chat_model"
CONF_IMAGE_MODEL = "image_model"
CONF_CODE_INTERPRETER = "code_interpreter"
CONF_FILENAMES = "filenames"
CONF_MAX_TOKENS = "max_tokens"
CONF_PRO_MODE = "pro_mode"
CONF_REASONING_EFFORT = "reasoning_effort"
CONF_REASONING_SUMMARY = "reasoning_summary"
CONF_RECOMMENDED = "recommended"
CONF_STORE_RESPONSES = "store_responses"
CONF_SERVICE_TIER = "service_tier"
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"
CONF_VERBOSITY = "verbosity"

# Azure AI Speech (STT / TTS) connection + options. STT and TTS are hard-wired to
# Azure Speech; each entity carries its own endpoint URI and API key because the
# Speech endpoint differs per install (custom subdomain or regional host).
CONF_STT_ENDPOINT = "stt_endpoint"
CONF_STT_API_KEY = "stt_api_key"
CONF_STT_LANGUAGE = "stt_language"
CONF_TTS_ENDPOINT = "tts_endpoint"
CONF_TTS_API_KEY = "tts_api_key"
CONF_TTS_VOICE = "tts_voice"
CONF_TTS_OUTPUT_FORMAT = "tts_output_format"
CONF_TTS_RATE = "tts_rate"
CONF_TTS_PITCH = "tts_pitch"
CONF_TTS_STYLE = "tts_style"
CONF_WEB_SEARCH = "web_search"
CONF_WEB_SEARCH_USER_LOCATION = "user_location"
CONF_WEB_SEARCH_CONTEXT_SIZE = "search_context_size"
CONF_WEB_SEARCH_CITY = "city"
CONF_WEB_SEARCH_REGION = "region"
CONF_WEB_SEARCH_COUNTRY = "country"
CONF_WEB_SEARCH_TIMEZONE = "timezone"
CONF_WEB_SEARCH_INLINE_CITATIONS = "inline_citations"
RECOMMENDED_CODE_INTERPRETER = False
RECOMMENDED_CHAT_MODEL = "gpt-4o-mini"
RECOMMENDED_IMAGE_MODEL = "gpt-image-2"
RECOMMENDED_MAX_TOKENS = 3000
RECOMMENDED_PRO_MODE = False
RECOMMENDED_REASONING_EFFORT = "low"
RECOMMENDED_STORE_RESPONSES = False
RECOMMENDED_REASONING_SUMMARY = "auto"
RECOMMENDED_SERVICE_TIER = "auto"
RECOMMENDED_TEMPERATURE = 1.0
RECOMMENDED_TOP_P = 1.0
RECOMMENDED_VERBOSITY = "medium"

# Azure AI Speech defaults.
DEFAULT_STT_LANGUAGE = "en-US"
DEFAULT_TTS_VOICE = "de-DE-KatjaNeural"
DEFAULT_TTS_OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"
# X-Microsoft-OutputFormat -> (file extension, HA-facing content type).
TTS_OUTPUT_FORMATS: dict[str, tuple[str, str]] = {
    "audio-16khz-32kbitrate-mono-mp3": ("mp3", "audio/mpeg"),
    "audio-24khz-48kbitrate-mono-mp3": ("mp3", "audio/mpeg"),
    "audio-24khz-96kbitrate-mono-mp3": ("mp3", "audio/mpeg"),
    "audio-48khz-96kbitrate-mono-mp3": ("mp3", "audio/mpeg"),
    "audio-48khz-192kbitrate-mono-mp3": ("mp3", "audio/mpeg"),
    "ogg-24khz-16bit-mono-opus": ("ogg", "audio/ogg"),
    "ogg-48khz-16bit-mono-opus": ("ogg", "audio/ogg"),
    "riff-16khz-16bit-mono-pcm": ("wav", "audio/wav"),
    "riff-24khz-16bit-mono-pcm": ("wav", "audio/wav"),
    "riff-48khz-16bit-mono-pcm": ("wav", "audio/wav"),
}
RECOMMENDED_WEB_SEARCH = False
RECOMMENDED_WEB_SEARCH_CONTEXT_SIZE = "medium"
RECOMMENDED_WEB_SEARCH_USER_LOCATION = False
RECOMMENDED_WEB_SEARCH_INLINE_CITATIONS = False

UNSUPPORTED_MODELS: list[str] = [
    "o1-mini",
    "o1-mini-2024-09-12",
    "o1-preview",
    "o1-preview-2024-09-12",
    "gpt-4o-realtime-preview",
    "gpt-4o-realtime-preview-2024-12-17",
    "gpt-4o-realtime-preview-2024-10-01",
    "gpt-4o-mini-realtime-preview",
    "gpt-4o-mini-realtime-preview-2024-12-17",
]

UNSUPPORTED_WEB_SEARCH_MODELS: list[str] = [
    "gpt-3.5",
    "gpt-4-turbo",
    "gpt-4.1-nano",
    "o1",
    "o3-mini",
]

UNSUPPORTED_IMAGE_MODELS: list[str] = [
    "gpt-5-mini",
    "o3-mini",
    "o4",
    "o1",
    "gpt-3.5",
    "gpt-4-turbo",
]

UNSUPPORTED_CODE_INTERPRETER_MODELS: list[str] = [
    "gpt-5-pro",
    "gpt-5.2-pro",
    "gpt-5-codex",
    "gpt-5.1-codex",
    "gpt-5.2-codex",
]

UNSUPPORTED_EXTENDED_CACHE_RETENTION_MODELS: list[str] = [
    "o1",
    "o3",
    "o4",
    "gpt-3.5",
    "gpt-4-turbo",
    "gpt-4o",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-5-mini",
    "gpt-5-nano",
]

RECOMMENDED_CONVERSATION_OPTIONS = {
    CONF_RECOMMENDED: True,
    CONF_LLM_HASS_API: [llm.LLM_API_ASSIST],
    CONF_PROMPT: llm.DEFAULT_INSTRUCTIONS_PROMPT,
}
RECOMMENDED_AI_TASK_OPTIONS = {
    CONF_RECOMMENDED: True,
}
RECOMMENDED_STT_OPTIONS: dict[str, Any] = {
    CONF_STT_LANGUAGE: DEFAULT_STT_LANGUAGE,
}
RECOMMENDED_TTS_OPTIONS: dict[str, Any] = {
    CONF_TTS_VOICE: DEFAULT_TTS_VOICE,
    CONF_TTS_OUTPUT_FORMAT: DEFAULT_TTS_OUTPUT_FORMAT,
}

UNSUPPORTED_FLEX_SERVICE_TIERS_MODELS: list[str] = [
    "gpt-5.3",
    "gpt-5.2-chat",
    "gpt-5.1-chat",
    "gpt-5-chat",
    "gpt-5.2-codex",
    "gpt-5.1-codex",
    "gpt-5-codex",
    "gpt-5.2-pro",
    "gpt-5-pro",
    "gpt-4",
    "o1",
    "o3-pro",
    "o3-deep-research",
    "o4-mini-deep-research",
    "o3-mini",
    "codex-mini",
]
UNSUPPORTED_PRIORITY_SERVICE_TIERS_MODELS: list[str] = [
    "gpt-5-nano",
    "gpt-5.3-chat",
    "gpt-5.2-chat",
    "gpt-5.1-chat",
    "gpt-5.1-codex-mini",
    "gpt-5-chat",
    "gpt-5.2-pro",
    "gpt-5-pro",
    "o1",
    "o3-pro",
    "o3-deep-research",
    "o4-mini-deep-research",
    "o3-mini",
    "codex-mini",
]
