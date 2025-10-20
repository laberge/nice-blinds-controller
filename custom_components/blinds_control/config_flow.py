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
    
    def _auto_generate_groups(self, devices: list[dict[str, str]]) -> list[dict[str, Any]]:
        """Auto-generate groups based on device name patterns."""
        import re
        from collections import defaultdict
        
        # Group devices by common prefix patterns
        # Pattern: "Office 1", "Office 2" -> group "Office"
        # Pattern: "Sunroom 1", "Sunroom 2" -> group "Sunroom"
        # Pattern: "MBA 1", "MBA 3" -> group "MBA"
        
        groups_dict = defaultdict(list)
        
        for device in devices:
            name = device["name"]
            device_id = device["id"]
            
            # Try to match pattern: "Name Number" or "Abbreviation Number"
            match = re.match(r'^([A-Za-z\s]+?)\s+(\d+)$', name.strip())
            if match:
                group_prefix = match.group(1).strip()
                groups_dict[group_prefix].append(device_id)
            else:
                # Check for abbreviated pattern like "MBA 1"
                match = re.match(r'^([A-Z]{2,4})\s+(\d+)$', name.strip())
                if match:
                    group_prefix = match.group(1)
                    groups_dict[group_prefix].append(device_id)
        
        # Create group objects (only for groups with 2+ devices)
        groups = []
        for group_name, device_ids in groups_dict.items():
            if len(device_ids) >= 2:
                groups.append({
                    "name": f"{group_name} Blinds",
                    "devices": device_ids,
                })
        
        # Add an "All Blinds" group if there are 3+ total devices
        if len(devices) >= 3:
            groups.append({
                "name": "All Blinds",
                "devices": [device["id"] for device in devices],
            })
        
        _LOGGER.info("Auto-generated %d groups from %d devices", len(groups), len(devices))
        return groups
    
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
        self._current_group_index = None

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

    async def async_step_manage_groups(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage groups - list, add, edit, delete."""
        if user_input is not None:
            action = user_input.get("action")
            
            if action == "add":
                return await self.async_step_add_group()
            elif action == "edit":
                return await self.async_step_select_group_to_edit()
            elif action == "delete":
                return await self.async_step_select_group_to_delete()
            elif action == "done":
                return await self._update_options()
        
        # Build options based on existing groups
        group_count = len(self._groups)
        group_list = "\n".join([f"• {g['name']} ({len(g['devices'])} devices)" for g in self._groups]) if self._groups else "No groups configured"
        
        return self.async_show_form(
            step_id="manage_groups",
            data_schema=vol.Schema({
                vol.Required("action"): vol.In({
                    "add": f"Add new group (current: {group_count})",
                    "edit": "Edit existing group" if self._groups else "Edit existing group (none)",
                    "delete": "Delete a group" if self._groups else "Delete a group (none)",
                    "done": "Save and finish",
                }),
            }),
            description_placeholders={
                "groups": group_list,
            },
        )

    async def async_step_add_group(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new group."""
        if user_input is not None:
            group_name = user_input.get("group_name", "").strip()
            group_devices = user_input.get("group_devices", [])
            
            if group_name and group_devices:
                self._groups.append({
                    "name": group_name,
                    "devices": group_devices,
                })
            
            return await self.async_step_manage_groups()
        
        device_options = {
            device["id"]: device["name"]
            for device in self._devices
        }

        return self.async_show_form(
            step_id="add_group",
            data_schema=vol.Schema({
                vol.Required("group_name"): cv.string,
                vol.Required("group_devices"): cv.multi_select(device_options),
            }),
        )

    async def async_step_select_group_to_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which group to edit."""
        if user_input is not None:
            self._current_group_index = int(user_input.get("group_index"))
            return await self.async_step_edit_group()
        
        if not self._groups:
            return await self.async_step_manage_groups()
        
        group_options = {
            str(i): f"{group['name']} ({len(group['devices'])} devices)"
            for i, group in enumerate(self._groups)
        }

        return self.async_show_form(
            step_id="select_group_to_edit",
            data_schema=vol.Schema({
                vol.Required("group_index"): vol.In(group_options),
            }),
        )

    async def async_step_edit_group(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit a group."""
        if user_input is not None:
            group_name = user_input.get("group_name", "").strip()
            group_devices = user_input.get("group_devices", [])
            
            if group_name and group_devices:
                self._groups[self._current_group_index] = {
                    "name": group_name,
                    "devices": group_devices,
                }
            
            return await self.async_step_manage_groups()
        
        current_group = self._groups[self._current_group_index]
        device_options = {
            device["id"]: device["name"]
            for device in self._devices
        }

        return self.async_show_form(
            step_id="edit_group",
            data_schema=vol.Schema({
                vol.Required("group_name", default=current_group["name"]): cv.string,
                vol.Required("group_devices", default=current_group["devices"]): cv.multi_select(device_options),
            }),
        )

    async def async_step_select_group_to_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which group to delete."""
        if user_input is not None:
            group_index = int(user_input.get("group_index"))
            deleted_name = self._groups[group_index]["name"]
            del self._groups[group_index]
            _LOGGER.info("Deleted group: %s", deleted_name)
            return await self.async_step_manage_groups()
        
        if not self._groups:
            return await self.async_step_manage_groups()
        
        group_options = {
            str(i): f"{group['name']} ({len(group['devices'])} devices)"
            for i, group in enumerate(self._groups)
        }

        return self.async_show_form(
            step_id="select_group_to_delete",
            data_schema=vol.Schema({
                vol.Required("group_index"): vol.In(group_options),
            }),
        )

    async def _update_options(self) -> FlowResult:
        """Update config entry with new group configuration."""
        # Update the config entry data with new groups
        new_data = {**self.config_entry.data}
        new_data["groups"] = self._groups
        
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data=new_data,
        )
        
        # Reload the integration to apply changes
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        
        return self.async_create_entry(title="", data={})

