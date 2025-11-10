"""Config flow for Blinds Control integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

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

            # Store selected devices
            self._selected_devices = devices_data
            self._move_time = move_time
            
            # Discover groups from controller
            try:
                controller = NiceController(http_config=self._http_config)
                self._groups = await controller.discover_groups()
                await controller.cleanup()
                _LOGGER.info("Discovered %d groups from controller", len(self._groups))
            except Exception as err:
                _LOGGER.warning("Could not discover groups: %s", err)
                self._groups = []
            
            # Go to review groups step
            return await self.async_step_review_groups()

        return self.async_show_form(
            step_id="select_devices",
            data_schema=self._build_device_selection_schema(),
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
    async def async_step_review_groups(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Review and confirm controller groups."""
        if user_input is not None:
            if user_input.get("use_groups", True):
                # User accepted the groups, create entry
                return self._create_entry_with_data(self._groups)
            else:
                # User rejected groups, create entry without them
                return self._create_entry_with_data([])
        
        # Build description of controller groups
        if self._groups:
            group_descriptions = []
            for group in self._groups:
                group_descriptions.append(
                    f"• {group['name']} (Group #{group['num']})"
                )
            
            groups_text = "\n".join(group_descriptions)
            
            return self.async_show_form(
                step_id="review_groups",
                data_schema=vol.Schema({
                    vol.Required("use_groups", default=True): cv.boolean,
                }),
                description_placeholders={
                    "groups": groups_text,
                    "group_count": str(len(self._groups)),
                },
            )
        else:
            # No groups found on controller, skip to completion
            _LOGGER.info("No groups found on controller")
            return self._create_entry_with_data([])


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Blinds Control."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._groups = list(config_entry.data.get("groups", []))
        self._devices = config_entry.data.get("devices", [])

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return await self.async_step_main_menu()
    
    async def async_step_main_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Main options menu."""
        if user_input is not None:
            action = user_input.get("action")
            
            if action == "refresh":
                return await self.async_step_refresh_devices()
            elif action == "done":
                return self.async_create_entry(title="", data={})
        
        device_count = len(self._devices)
        group_count = len(self._groups)
        
        return self.async_show_form(
            step_id="main_menu",
            data_schema=vol.Schema({
                vol.Required("action"): vol.In({
                    "refresh": f"Refresh Devices & Groups (current: {device_count} devices, {group_count} groups)",
                    "done": "Save and Exit",
                }),
            }),
            description_placeholders={
                "info": "Groups are managed in your Nice controller's web interface. Use 'Refresh' to update after making changes."
            }
        )
    
    async def async_step_refresh_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Refresh devices and groups from controller."""
        if user_input is not None:
            if not user_input.get("confirm_refresh", False):
                return await self.async_step_main_menu()
            
            # Re-discover devices and groups from controller
            http_config = {
                "base_url": self.config_entry.data.get("http_base_url"),
                "username": self.config_entry.data.get("http_username"),
                "password": self.config_entry.data.get("http_password"),
                "timeout": self.config_entry.data.get("http_timeout", 10),
            }
            
            try:
                controller = NiceController(http_config=http_config)
                
                # Discover devices
                new_devices = await controller.discover_devices()
                _LOGGER.info("Refreshed devices: found %d devices", len(new_devices))
                
                # Discover groups
                new_groups = await controller.discover_groups()
                _LOGGER.info("Refreshed groups: found %d groups", len(new_groups))
                
                await controller.cleanup()
                
                # Update config entry
                new_data = {**self.config_entry.data}
                new_data["devices"] = new_devices
                new_data["groups"] = new_groups
                
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=new_data,
                )
                
                # Reload the integration to apply changes
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                
                # Update local state for menu display
                self._devices = new_devices
                self._groups = new_groups
                
                return self.async_create_entry(
                    title="",
                    data={},
                    description="Successfully refreshed devices and groups. Integration has been reloaded."
                )
                
            except Exception as err:
                _LOGGER.error("Error refreshing devices: %s", err)
                return self.async_show_form(
                    step_id="refresh_devices",
                    data_schema=vol.Schema({
                        vol.Required("confirm_refresh", default=False): cv.boolean,
                    }),
                    errors={"base": "refresh_failed"},
                    description_placeholders={
                        "error": str(err)
                    }
                )
        
        return self.async_show_form(
            step_id="refresh_devices",
            data_schema=vol.Schema({
                vol.Required("confirm_refresh", default=True): cv.boolean,
            }),
            description_placeholders={
                "device_count": str(len(self._devices)),
                "group_count": str(len(self._groups)),
            }
        )

