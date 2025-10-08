"""Config flow for Blinds Control integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from . import DOMAIN
from .nice_protocol import NiceController

_LOGGER = logging.getLogger(__name__)

_LOGGER.debug("Config flow module loaded")

# HTTP connection details
STEP_HTTP_CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Required("http_base_url"): cv.string,
        vol.Required("http_username", default="admin"): cv.string,
        vol.Required("http_password"): cv.string,
        vol.Optional("http_timeout", default=10): cv.positive_int,
    }
)



class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Blinds Control."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        _LOGGER.debug("Config flow initialized")
        self._http_config: dict[str, Any] = {}
        self._discovered_devices: list[dict[str, str]] = []
        self._selected_devices: list[dict[str, str]] = []
        self._move_time: int = 30
        self._groups: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - HTTP connection configuration."""
        _LOGGER.debug("async_step_user called (user_input: %s)", user_input)
        return await self.async_step_http_connection()

    async def async_step_http_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle HTTP connection configuration."""
        _LOGGER.debug("async_step_http_connection called (user_input: %s)", user_input)
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate URL format
            base_url = user_input.get("http_base_url", "")
            _LOGGER.debug("Validating URL: %s", base_url)
            if not base_url.startswith(("http://", "https://")):
                _LOGGER.debug("URL validation failed - invalid format")
                errors["http_base_url"] = "invalid_url"
            else:
                _LOGGER.debug("URL validation passed, connecting to controller...")
                # Try to connect and discover devices
                self._http_config = {
                    "base_url": base_url,
                    "username": user_input.get("http_username"),
                    "password": user_input.get("http_password"),
                    "timeout": user_input.get("http_timeout", 10),
                }

                try:
                    _LOGGER.debug("Creating NiceController with config: %s", self._http_config)
                    controller = NiceController(http_config=self._http_config)
                    _LOGGER.debug("Discovering devices...")
                    self._discovered_devices = await controller.discover_devices()
                    _LOGGER.info("Discovered %d devices from controller", len(self._discovered_devices))
                    await controller.cleanup()

                    if not self._discovered_devices:
                        _LOGGER.warning("No devices found on controller")
                        errors["base"] = "no_devices_found"
                    else:
                        _LOGGER.debug("Proceeding to device selection")
                        return await self.async_step_select_devices()

                except aiohttp.ClientResponseError as err:
                    _LOGGER.error("HTTP error from controller: %s (status: %s)", err, err.status)
                    if err.status == 401:
                        errors["base"] = "invalid_auth"
                    else:
                        errors["base"] = "cannot_connect"
                except (aiohttp.ClientError, TimeoutError) as err:
                    _LOGGER.error("Failed to connect to controller: %s", err)
                    errors["base"] = "cannot_connect"
                except Exception as err:
                    _LOGGER.error("Unexpected error during setup: %s", err, exc_info=True)
                    errors["base"] = "unknown"

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

            # Store selected devices and move on to groups
            self._selected_devices = devices_data
            self._move_time = move_time
            
            return await self.async_step_configure_groups()

        return self.async_show_form(
            step_id="select_devices",
            data_schema=self._build_device_selection_schema(),
        )
    
    async def async_step_configure_groups(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle group configuration."""
        if user_input is not None:
            create_groups = user_input.get("create_groups", False)
            
            if not create_groups:
                # Skip group creation, finish setup
                return self._create_entry_with_data([])
            
            # Move to group creation step
            self._groups = []
            return await self.async_step_create_group()
        
        return self.async_show_form(
            step_id="configure_groups",
            data_schema=vol.Schema({
                vol.Required("create_groups", default=True): cv.boolean,
            }),
            description_placeholders={
                "device_count": str(len(self._selected_devices))
            }
        )
    
    async def async_step_create_group(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle creating a single group."""
        if user_input is not None:
            group_name = user_input.get("group_name", "").strip()
            group_devices = user_input.get("group_devices", [])
            add_another = user_input.get("add_another", False)
            
            if group_name and group_devices:
                # Add this group
                self._groups.append({
                    "name": group_name,
                    "devices": group_devices,
                })
            
            if add_another:
                # Show form again for another group
                return await self.async_step_create_group()
            else:
                # Done with groups, create entry
                return self._create_entry_with_data(self._groups)
        
        return self.async_show_form(
            step_id="create_group",
            data_schema=self._build_group_creation_schema(),
        )
    
    def _create_entry_with_data(self, groups: list[dict[str, Any]]) -> FlowResult:
        """Create the config entry with all data."""
        entry_data = {
            "http_base_url": self._http_config["base_url"],
            "http_username": self._http_config["username"],
            "http_password": self._http_config["password"],
            "http_timeout": self._http_config["timeout"],
            "move_time": self._move_time,
            "devices": self._selected_devices,
            "groups": groups,
        }

        # Use controller URL as unique ID
        self.async_set_unique_id(f"nice_controller_{self._http_config['base_url']}")
        self._abort_if_unique_id_configured()

        group_text = f", {len(groups)} groups" if groups else ""
        return self.async_create_entry(
            title=f"Nice Controller ({len(self._selected_devices)} devices{group_text})",
            data=entry_data,
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
    
    def _build_group_creation_schema(self) -> vol.Schema:
        """Build group creation schema."""
        device_options = {
            device["id"]: device["name"]
            for device in self._selected_devices
        }

        return vol.Schema(
            {
                vol.Required("group_name"): cv.string,
                vol.Required("group_devices"): cv.multi_select(device_options),
                vol.Required("add_another", default=False): cv.boolean,
            }
        )

