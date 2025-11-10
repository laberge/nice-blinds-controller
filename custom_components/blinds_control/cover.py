"""Platform for Blinds Control cover integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from . import DOMAIN
from .nice_protocol import NiceController

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Blinds Control cover platform."""
    entry_runtime = hass.data[DOMAIN][config_entry.entry_id]
    move_time = config_entry.data.get("move_time", 30)

    http_config = {
        "base_url": config_entry.data.get("http_base_url"),
        "username": config_entry.data.get("http_username"),
        "password": config_entry.data.get("http_password"),
        "timeout": config_entry.data.get("http_timeout", 10),
    }

    controller = NiceController(http_config=http_config)
    coordinator = NiceStatusCoordinator(hass, controller)
    await coordinator.async_config_entry_first_refresh()

    entry_runtime["controller"] = controller
    entry_runtime["coordinator"] = coordinator

    # Create cover entities for all devices
    entities = []
    devices = config_entry.data.get("devices", [])

    for device in devices:
        entity = BlindsCover(
            name=device["name"],
            unique_id=f"{config_entry.entry_id}_{device['id']}",
            controller=controller,
            coordinator=coordinator,
            device_id=device["id"],
            move_time=move_time,
            entry_id=config_entry.entry_id,
            device_info=device,
        )
        entities.append(entity)

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
                coordinator=coordinator,
                entry_id=config_entry.entry_id,
            )
            entities.append(group_entity)

    async_add_entities(entities, True)


class NiceStatusCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator for polling Nice controller device states."""

    def __init__(self, hass: HomeAssistant, controller: NiceController) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Nice Blinds Controller status",
            update_interval=timedelta(seconds=10),
        )
        self._controller = controller

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch latest device data from controller."""
        try:
            return await self._controller.get_all_device_status()
        except Exception as err:
            raise UpdateFailed(f"Failed to refresh device status: {err}") from err


class BlindsCover(CoordinatorEntity[dict[str, dict[str, Any]]], CoverEntity):
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
        coordinator: NiceStatusCoordinator,
        device_id: str,
        move_time: int = 30,
        entry_id: str = None,
        device_info: dict = None,
    ) -> None:
        """Initialize the blind."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._controller = controller
        self._device_id = device_id
        self._move_time = move_time
        self._attr_should_poll = False

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

    @property
    def _status(self) -> dict[str, Any] | None:
        """Return cached status for this device."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._device_id)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return True

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover (0 closed, 100 open)."""
        if not (status := self._status):
            return None
        position = status.get("position")
        return position if position is not None else None

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        status = self._status
        if not status:
            return False
        return status.get("status_code") == "02"

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        status = self._status
        if not status:
            return False
        return status.get("status_code") == "03"

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        position = self.current_cover_position
        if position is None:
            return None
        return position == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        _LOGGER.info("Opening blinds: %s", self.name)

        try:
            # Send Nice protocol open command
            await self._controller.send_command(self._device_id, "open")
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error opening blinds %s: %s", self.name, err)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        _LOGGER.info("Closing blinds: %s", self.name)

        try:
            # Send Nice protocol close command
            await self._controller.send_command(self._device_id, "close")
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error closing blinds %s: %s", self.name, err)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        _LOGGER.info("Stopping blinds: %s", self.name)

        try:
            # Send Nice protocol stop command
            await self._controller.send_command(self._device_id, "stop")
        except Exception as err:
            _LOGGER.error("Error stopping blinds %s: %s", self.name, err)
        finally:
            await self.coordinator.async_request_refresh()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = kwargs.get("position", 0)
        _LOGGER.info("Setting blinds %s to position: %s", self.name, position)

        current_pos = self.current_cover_position or 0

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
        except Exception as err:
            _LOGGER.error("Error setting blinds %s position: %s", self.name, err)
        finally:
            await self.coordinator.async_request_refresh()


class BlindsGroupCover(
    CoordinatorEntity[dict[str, dict[str, Any]]], CoverEntity
):
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
        coordinator: NiceStatusCoordinator,
        entry_id: str = None,
    ) -> None:
        """Initialize the blind group using controller's native groups."""
        super().__init__(coordinator)
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
    def available(self) -> bool:
        """Return True if entity is available."""
        return True

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
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error opening group %s: %s", self.name, err)
            raise

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close all covers in the group using controller's native group command."""
        _LOGGER.info("Closing controller group: %s (num: %s)", self.name, self._group_num)
        try:
            await self._controller.send_group_command(self._group_num, "close")
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error closing group %s: %s", self.name, err)
            raise

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop all covers in the group using controller's native group command."""
        _LOGGER.info("Stopping controller group: %s (num: %s)", self.name, self._group_num)
        try:
            await self._controller.send_group_command(self._group_num, "stop")
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error stopping group %s: %s", self.name, err)
            raise
