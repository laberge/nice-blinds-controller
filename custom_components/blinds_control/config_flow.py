"""Config flow for Blinds Control integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

PROTOCOL_TYPES = ["rf433", "bidi_bus"]

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("name", default="Smart Blinds"): cv.string,
        vol.Required("protocol_type", default="rf433"): vol.In(PROTOCOL_TYPES),
        vol.Optional("device_id"): cv.string,
        vol.Optional("gpio_pin", default=17): cv.positive_int,
        vol.Optional("move_time", default=30): cv.positive_int,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Blinds Control."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the input
            name = user_input.get("name", "Smart Blinds")
            protocol_type = user_input.get("protocol_type", "rf433")

            # Create a unique ID for this device
            await self.async_set_unique_id(f"blinds_{name.lower().replace(' ', '_')}")
            self._abort_if_unique_id_configured()

            # Validate GPIO pin for RF433 protocol
            if protocol_type == "rf433":
                gpio_pin = user_input.get("gpio_pin", 17)
                if not 1 <= gpio_pin <= 27:
                    errors["gpio_pin"] = "invalid_gpio_pin"

            if not errors:
                _LOGGER.info(
                    "Setting up Nice blinds: %s with protocol: %s",
                    name,
                    protocol_type,
                )
                return self.async_create_entry(title=name, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
