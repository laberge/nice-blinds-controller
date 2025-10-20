"""Platform for Blinds Control cover integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
    CoverDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from . import DOMAIN
from .nice_protocol import NiceController

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Blinds Control cover platform."""
    move_time = config_entry.data.get("move_time", 30)

    # Build HTTP config
    http_config = {
        "base_url": config_entry.data.get("http_base_url"),
        "username": config_entry.data.get("http_username"),
        "password": config_entry.data.get("http_password"),
        "timeout": config_entry.data.get("http_timeout", 10),
    }

    # Initialize Nice HTTP controller
    controller = NiceController(http_config=http_config)

    # Create cover entities for all devices
    entities = []
    devices = config_entry.data.get("devices", [])
    device_entities = {}  # Store entities by device ID for group references

    for device in devices:
        entity = BlindsCover(
            name=device["name"],
            unique_id=f"{config_entry.entry_id}_{device['id']}",
            controller=controller,
            device_id=device["id"],
            move_time=move_time,
            entry_id=config_entry.entry_id,
            device_info=device,
        )
        entities.append(entity)
        device_entities[device["id"]] = entity

    # Create group entities if configured (controller native groups)
    groups = config_entry.data.get("groups", [])
    for group in groups:
        group_name = group.get("name", "")
        group_num = group.get("num", "")
        
        if group_num:
            group_entity = BlindsGroupCover(
                name=group_name,
                unique_id=f"{config_entry.entry_id}_group_{group_num}",
                group_num=group_num,
                controller=controller,
                entry_id=config_entry.entry_id,
            )
            entities.append(group_entity)

    async_add_entities(entities, True)


class BlindsCover(CoverEntity):
    """Representation of a Blinds Control cover."""

    _attr_device_class = CoverDeviceClass.BLIND
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(
        self,
        name: str,
        unique_id: str,
        controller: NiceController,
        device_id: str,
        move_time: int = 30,
        entry_id: str = None,
        device_info: dict = None,
    ) -> None:
        """Initialize the blind."""
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._controller = controller
        self._device_id = device_id
        self._position = None  # Will be fetched from controller
        self._is_opening = False
        self._is_closing = False
        self._move_time = move_time  # Estimated time to fully open/close in seconds
        self._attr_should_poll = True  # Enable polling to get real position
        
        # Create device info
        if device_info:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{entry_id}_{device_id}")},
                name=name,
                manufacturer="Nice S.p.A.",
                model=device_info.get("module", "Nice Blind Motor"),
                sw_version=device_info.get("adr", "1"),
                via_device=(DOMAIN, entry_id),
            )
        
    async def async_update(self) -> None:
        """Fetch new state data for this cover."""
        try:
            # Get current status from controller
            status = await self._controller.get_device_status(self._device_id)
            if status:
                # Update position from controller
                pos = status.get('pos', '255')
                if pos != '255':  # 255 means unknown position
                    self._position = int(pos)
                
                # Update moving state
                sta = status.get('sta', '00')
                self._is_opening = (sta == '02')
                self._is_closing = (sta == '03')
        except Exception as err:
            _LOGGER.error("Error updating blind %s status: %s", self.name, err)

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover (0 closed, 100 open)."""
        return self._position

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        return self._is_opening

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        return self._is_closing

    @property
    def is_closed(self) -> bool:
        """Return if the cover is closed."""
        return self._position == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        _LOGGER.info("Opening blinds: %s", self.name)
        self._is_opening = True
        self._is_closing = False
        self.async_write_ha_state()

        try:
            # Send Nice protocol open command
            await self._controller.send_command(self._device_id, "open")
            # Position will be updated by polling in async_update
        except Exception as err:
            _LOGGER.error("Error opening blinds %s: %s", self.name, err)
            self._is_opening = False
            self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        _LOGGER.info("Closing blinds: %s", self.name)
        self._is_closing = True
        self._is_opening = False
        self.async_write_ha_state()

        try:
            # Send Nice protocol close command
            await self._controller.send_command(self._device_id, "close")
            # Position will be updated by polling in async_update
        except Exception as err:
            _LOGGER.error("Error closing blinds %s: %s", self.name, err)
            self._is_closing = False
            self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        _LOGGER.info("Stopping blinds: %s", self.name)

        try:
            # Send Nice protocol stop command
            await self._controller.send_command(self._device_id, "stop")
        except Exception as err:
            _LOGGER.error("Error stopping blinds %s: %s", self.name, err)
        finally:
            self._is_opening = False
            self._is_closing = False
            self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = kwargs.get("position", 0)
        _LOGGER.info("Setting blinds %s to position: %s", self.name, position)

        current_pos = self._position if self._position is not None else 0
        
        if position > current_pos:
            self._is_opening = True
            self._is_closing = False
        else:
            self._is_closing = True
            self._is_opening = False

        self.async_write_ha_state()

        try:
            # Calculate movement time based on position difference
            move_duration = abs(position - current_pos) / 100.0 * self._move_time

            # Send appropriate command
            if position > current_pos:
                await self._controller.send_command(self._device_id, "open")
            elif position < current_pos:
                await self._controller.send_command(self._device_id, "close")

            # Wait for partial movement
            await asyncio.sleep(move_duration)

            # Stop at desired position
            await self._controller.send_command(self._device_id, "stop")
            
            # Position will be updated by polling in async_update
        except Exception as err:
            _LOGGER.error("Error setting blinds %s position: %s", self.name, err)
        finally:
            self._is_opening = False
            self._is_closing = False
            self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity removal and clean up controller resources."""
        try:
            await self._controller.cleanup()
        except Exception as err:
            _LOGGER.error("Error during controller cleanup for %s: %s", self.name, err)


class BlindsGroupCover(CoverEntity):
    """Representation of a Nice controller group."""

    _attr_device_class = CoverDeviceClass.BLIND
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
    )

    def __init__(
        self,
        name: str,
        unique_id: str,
        group_num: str,
        controller: NiceController,
        entry_id: str = None,
    ) -> None:
        """Initialize the blind group using controller's native groups."""
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._group_num = group_num
        self._controller = controller
        self._attr_should_poll = False  # Groups don't have position feedback
        
        # Create device info for the group
        if entry_id:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{entry_id}_group_{group_num}")},
                name=f"{name} (Group)",
                manufacturer="Nice S.p.A.",
                model="Controller Group",
                via_device=(DOMAIN, entry_id),
            )

    @property
    def current_cover_position(self) -> int | None:
        """Return position - groups don't track position."""
        return None

    @property
    def is_opening(self) -> bool:
        """Return if group is opening."""
        return False

    @property
    def is_closing(self) -> bool:
        """Return if group is closing."""
        return False

    @property
    def is_closed(self) -> bool | None:
        """Return None - groups don't track state."""
        return None

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open all covers in the group using controller's native group command."""
        _LOGGER.info("Opening controller group: %s (num: %s)", self.name, self._group_num)
        try:
            await self._controller.send_group_command(self._group_num, "open")
        except Exception as err:
            _LOGGER.error("Error opening group %s: %s", self.name, err)
            raise

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close all covers in the group using controller's native group command."""
        _LOGGER.info("Closing controller group: %s (num: %s)", self.name, self._group_num)
        try:
            await self._controller.send_group_command(self._group_num, "close")
        except Exception as err:
            _LOGGER.error("Error closing group %s: %s", self.name, err)
            raise

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop all covers in the group using controller's native group command."""
        _LOGGER.info("Stopping controller group: %s (num: %s)", self.name, self._group_num)
        try:
            await self._controller.send_group_command(self._group_num, "stop")
        except Exception as err:
            _LOGGER.error("Error stopping group %s: %s", self.name, err)
            raise
