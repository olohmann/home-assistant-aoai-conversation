"""The Azure OpenAI Conversation integration."""

from __future__ import annotations

import openai
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_PROMPT, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv, selector
from homeassistant.helpers.typing import ConfigType

from .client import create_client
from .const import (
    CONF_ENDPOINT,
    CONF_FILENAMES,
    DOMAIN,
    LOGGER,
)

SERVICE_GENERATE_IMAGE = "generate_image"
SERVICE_GENERATE_CONTENT = "generate_content"

PLATFORMS = (Platform.AI_TASK, Platform.CONVERSATION, Platform.STT, Platform.TTS)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type OpenAIConfigEntry = ConfigEntry[openai.AsyncClient]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Azure OpenAI Conversation."""

    async def render_image(call: ServiceCall) -> ServiceResponse:
        """Handle the removed 'generate_image' action."""
        LOGGER.error(
            "The '%s.%s' action is no longer supported by the Azure OpenAI "
            "Conversation integration. Generate images with the "
            "'ai_task.generate_image' action using an AI Task entity backed by "
            "an Azure image deployment (for example 'gpt-image-2'). See the "
            "integration documentation for migration details.",
            DOMAIN,
            SERVICE_GENERATE_IMAGE,
        )
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="generate_image_removed",
        )

    async def send_prompt(call: ServiceCall) -> ServiceResponse:
        """Handle the removed 'generate_content' action."""
        LOGGER.error(
            "The '%s.%s' action is no longer supported by the Azure OpenAI "
            "Conversation integration. Generate content with the "
            "'ai_task.generate_data' action using an AI Task entity instead. "
            "See the integration documentation for migration details.",
            DOMAIN,
            SERVICE_GENERATE_CONTENT,
        )
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="generate_content_removed",
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_CONTENT,
        send_prompt,
        schema=vol.Schema(
            {
                vol.Required("config_entry"): selector.ConfigEntrySelector(
                    {
                        "integration": DOMAIN,
                    }
                ),
                vol.Required(CONF_PROMPT): cv.string,
                vol.Optional(CONF_FILENAMES, default=[]): vol.All(
                    cv.ensure_list, [cv.string]
                ),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_IMAGE,
        render_image,
        schema=vol.Schema(
            {
                vol.Required("config_entry"): selector.ConfigEntrySelector(
                    {
                        "integration": DOMAIN,
                    }
                ),
                vol.Required(CONF_PROMPT): cv.string,
                vol.Optional("size", default="1024x1024"): vol.In(
                    ("1024x1024", "1024x1792", "1792x1024")
                ),
                vol.Optional("quality", default="standard"): vol.In(("standard", "hd")),
                vol.Optional("style", default="vivid"): vol.In(("vivid", "natural")),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: OpenAIConfigEntry) -> bool:
    """Set up Azure OpenAI Conversation from a config entry."""
    client = create_client(hass, entry.data[CONF_API_KEY], entry.data[CONF_ENDPOINT])

    # Cache current platform data which gets added to each request
    # (caching done by library)
    _ = await hass.async_add_executor_job(client.platform_headers)

    try:
        await hass.async_add_executor_job(client.with_options(timeout=10.0).models.list)
    except openai.AuthenticationError as err:
        raise ConfigEntryAuthFailed(err) from err
    except openai.OpenAIError as err:
        raise ConfigEntryNotReady(err) from err

    entry.runtime_data = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: OpenAIConfigEntry) -> bool:
    """Unload Azure OpenAI."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_update_options(hass: HomeAssistant, entry: OpenAIConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)
