"""Tests for the (removed) deprecated services."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aoai_conversation.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError


@pytest.mark.parametrize(
    ("service", "service_data"),
    [
        ("generate_content", {"prompt": "Hello"}),
        ("generate_image", {"prompt": "A cat"}),
    ],
)
async def test_deprecated_services_raise(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    service: str,
    service_data: dict,
) -> None:
    """The removed generate_* actions raise a ServiceValidationError."""
    assert hass.services.has_service(DOMAIN, service)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            service,
            {"config_entry": setup_integration.entry_id, **service_data},
            blocking=True,
            return_response=True,
        )
