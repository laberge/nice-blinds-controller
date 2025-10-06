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

from . import DOMAIN
from .nice_protocol import NiceController

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Blinds Control cover platform."""
    name = config_entry.data.get("name", "Smart Blinds")
    device_id = config_entry.data.get("device_id")
    protocol_type = config_entry.data.get("protocol_type", "rf433")
    gpio_pin = config_entry.data.get("gpio_pin", 17)
    move_time = config_entry.data.get("move_time", 30)

    # Build HTTP config if protocol is HTTP
    http_config = None
    if protocol_type == "http":
        http_config = {
            "base_url": config_entry.data.get("http_base_url"),
            "open_endpoint": config_entry.data.get("http_open_endpoint", "/open"),
            "close_endpoint": config_entry.data.get("http_close_endpoint", "/close"),
            "stop_endpoint": config_entry.data.get("http_stop_endpoint", "/stop"),
            "username": config_entry.data.get("http_username"),
            "password": config_entry.data.get("http_password"),
            "timeout": config_entry.data.get("http_timeout", 10),
        }

    # Initialize Nice controller
    controller = NiceController(
        protocol_type=protocol_type, gpio_pin=gpio_pin, http_config=http_config
    )

    async_add_entities(
        [BlindsCover(name, config_entry.entry_id, controller, device_id, move_time)],
        True,
    )


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
        device_id: str | None,
        move_time: int = 30,
    ) -> None:
        """Initialize the blind."""
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._controller = controller
        self._device_id = device_id
        self._position = 0
        self._is_opening = False
        self._is_closing = False
        self._move_time = move_time  # Estimated time to fully open/close in seconds

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

            # Simulate movement time
            await asyncio.sleep(self._move_time)

            self._position = 100
        except Exception as err:
            _LOGGER.error("Error opening blinds %s: %s", self.name, err)
        finally:
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

            # Simulate movement time
            await asyncio.sleep(self._move_time)

            self._position = 0
        except Exception as err:
            _LOGGER.error("Error closing blinds %s: %s", self.name, err)
        finally:
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

        if position > self._position:
            self._is_opening = True
            self._is_closing = False
        else:
            self._is_closing = True
            self._is_opening = False

        self.async_write_ha_state()

        try:
            # Calculate movement time based on position difference
            current_pos = self._position
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

            self._position = position
        except Exception as err:
            _LOGGER.error("Error setting blinds %s position: %s", self.name, err)
        finally:
            self._is_opening = False
            self._is_closing = False
            self.async_write_ha_state()
