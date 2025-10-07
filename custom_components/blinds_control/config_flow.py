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
from .nice_protocol import NiceController

_LOGGER = logging.getLogger(__name__)

PROTOCOL_TYPES = ["rf433", "bidi_bus", "http"]

# Step 1: Choose protocol type
STEP_PROTOCOL_SCHEMA = vol.Schema(
    {
        vol.Required("protocol_type", default="http"): vol.In(PROTOCOL_TYPES),
    }
)

# Step 2a: HTTP connection details
STEP_HTTP_CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Required("http_base_url"): cv.string,
        vol.Required("http_username", default="admin"): cv.string,
        vol.Required("http_password"): cv.string,
        vol.Optional("http_timeout", default=10): cv.positive_int,
    }
)

# Step 2b: RF433 settings
STEP_RF433_SCHEMA = vol.Schema(
    {
        vol.Required("name", default="Smart Blinds"): cv.string,
        vol.Optional("device_id"): cv.string,
        vol.Optional("gpio_pin", default=17): cv.positive_int,
        vol.Optional("move_time", default=30): cv.positive_int,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Blinds Control."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._protocol_type: str | None = None
        self._http_config: dict[str, Any] = {}
        self._discovered_devices: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - choose protocol."""
        if user_input is not None:
            self._protocol_type = user_input["protocol_type"]

            if self._protocol_type == "http":
                return await self.async_step_http_connection()
            elif self._protocol_type == "rf433":
                return await self.async_step_rf433()
            else:
                # BiDi-Bus or other protocols
                return self.async_abort(reason="protocol_not_implemented")

        return self.async_show_form(
            step_id="user", data_schema=STEP_PROTOCOL_SCHEMA
        )

    async def async_step_http_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle HTTP connection configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate URL format
            base_url = user_input.get("http_base_url", "")
            if not base_url.startswith(("http://", "https://")):
                errors["http_base_url"] = "invalid_url"
            else:
                # Try to connect and discover devices
                self._http_config = {
                    "base_url": base_url,
                    "username": user_input.get("http_username"),
                    "password": user_input.get("http_password"),
                    "timeout": user_input.get("http_timeout", 10),
                }

                try:
                    controller = NiceController(
                        protocol_type="http", http_config=self._http_config
                    )
                    self._discovered_devices = await controller.discover_devices()
                    await controller.cleanup()

                    if not self._discovered_devices:
                        errors["base"] = "no_devices_found"
                    else:
                        return await self.async_step_select_devices()

                except Exception as err:
                    _LOGGER.error("Failed to connect to controller: %s", err)
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="http_connection",
            data_schema=STEP_HTTP_CONNECTION_SCHEMA,
            errors=errors,
        )

    async def async_step_select_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device selection."""
        if user_input is not None:
            selected_devices = user_input.get("devices", [])
            move_time = user_input.get("move_time", 30)

            if not selected_devices:
                return self.async_show_form(
                    step_id="select_devices",
                    data_schema=self._build_device_selection_schema(),
                    errors={"devices": "select_at_least_one"},
                )

            # Get device details for selected devices
            devices_data = []
            for device_id in selected_devices:
                device = next(
                    (d for d in self._discovered_devices if d["id"] == device_id), None
                )
                if device:
                    devices_data.append(device)

            # Create single entry with all selected devices
            entry_data = {
                "protocol_type": "http",
                "http_base_url": self._http_config["base_url"],
                "http_username": self._http_config["username"],
                "http_password": self._http_config["password"],
                "http_timeout": self._http_config["timeout"],
                "move_time": move_time,
                "devices": devices_data,  # Store all devices in one entry
            }

            # Use controller URL as unique ID
            await self.async_set_unique_id(f"nice_controller_{self._http_config['base_url']}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Nice Controller ({len(selected_devices)} devices)",
                data=entry_data,
            )

        return self.async_show_form(
            step_id="select_devices",
            data_schema=self._build_device_selection_schema(),
        )

    def _build_device_selection_schema(self) -> vol.Schema:
        """Build device selection schema."""
        device_options = {
            device["id"]: f"{device['name']} ({device['module']})"
            for device in self._discovered_devices
        }

        return vol.Schema(
            {
                vol.Required("devices"): cv.multi_select(device_options),
                vol.Optional("move_time", default=30): cv.positive_int,
            }
        )

    async def async_step_rf433(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle RF433 configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get("name", "Smart Blinds")
            gpio_pin = user_input.get("gpio_pin", 17)

            if not 1 <= gpio_pin <= 27:
                errors["gpio_pin"] = "invalid_gpio_pin"

            if not errors:
                await self.async_set_unique_id(f"blinds_{name.lower().replace(' ', '_')}")
                self._abort_if_unique_id_configured()

                entry_data = {
                    "protocol_type": "rf433",
                    "name": name,
                    "device_id": user_input.get("device_id"),
                    "gpio_pin": gpio_pin,
                    "move_time": user_input.get("move_time", 30),
                }

                return self.async_create_entry(title=name, data=entry_data)

        return self.async_show_form(
            step_id="rf433", data_schema=STEP_RF433_SCHEMA, errors=errors
        )
