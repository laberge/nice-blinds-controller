"""Tests for the cover entities and status coordinator."""
from unittest.mock import AsyncMock

from awesomeversion import AwesomeVersion
from homeassistant.const import __version__ as HA_VERSION
import pytest

from custom_components.blinds_control.cover import (
    BlindsCover,
    BlindsGroupCover,
    NiceStatusCoordinator,
)


def make_coordinator(hass, controller=None, data=None, success=True):
    controller = controller or AsyncMock()
    controller.get_all_device_status.return_value = data or {}
    coordinator = NiceStatusCoordinator(hass, controller)
    coordinator.data = data or {}
    coordinator.last_update_success = success
    return coordinator, controller


def make_cover(coordinator, controller, device_id="1,01"):
    return BlindsCover(
        name="MBA 3",
        unique_id="uid",
        controller=controller,
        coordinator=coordinator,
        device_id=device_id,
        move_time=30,
        entry_id="entry",
        device_info={"module": "Era Mat MA", "adr": "1"},
    )


async def test_cover_position_and_states(hass):
    data = {
        "1,01": {"status_code": "05", "position": 0},
        "1,0F": {"status_code": "04", "position": 100},
        "10,05": {"status_code": "02", "position": None},
    }
    coordinator, controller = make_coordinator(hass, data=data)

    closed = make_cover(coordinator, controller, "1,01")
    assert closed.current_cover_position == 0
    assert closed.is_closed is True

    opening = make_cover(coordinator, controller, "10,05")
    assert opening.is_opening is True
    assert opening.is_closing is False
    assert opening.is_closed is None  # position unknown

    open_full = make_cover(coordinator, controller, "1,0F")
    assert open_full.is_closed is False


async def test_cover_available_reflects_coordinator(hass):
    data = {"1,01": {"status_code": "05", "position": 0}}
    coordinator, controller = make_coordinator(hass, data=data)
    cover = make_cover(coordinator, controller, "1,01")
    assert cover.available is True

    coordinator.last_update_success = False
    assert cover.available is False


async def test_cover_unavailable_when_device_missing(hass):
    coordinator, controller = make_coordinator(hass, data={"9,09": {}})
    cover = make_cover(coordinator, controller, "1,01")
    assert cover.available is False


@pytest.mark.parametrize("command", ["open", "close", "stop"])
async def test_cover_commands(hass, command):
    data = {"1,01": {"status_code": "05", "position": 0}}
    coordinator, controller = make_coordinator(hass, data=data)
    cover = make_cover(coordinator, controller, "1,01")

    await getattr(cover, f"async_{command}_cover")()
    controller.send_command.assert_awaited_with("1,01", command)


async def test_set_position_moves_then_stops(hass, monkeypatch):
    data = {"1,01": {"status_code": "05", "position": 0}}
    coordinator, controller = make_coordinator(hass, data=data)
    cover = make_cover(coordinator, controller, "1,01")

    sleeps = []

    async def fake_sleep(duration):
        sleeps.append(duration)

    monkeypatch.setattr(
        "custom_components.blinds_control.cover.asyncio.sleep", fake_sleep
    )

    await cover.async_set_cover_position(position=50)

    # From 0 -> 50 with move_time 30s => 15s of travel, then open then stop.
    assert sleeps == [pytest.approx(15.0)]
    commands = [call.args for call in controller.send_command.await_args_list]
    assert ("1,01", "open") in commands
    assert ("1,01", "stop") in commands


async def test_group_cover_commands(hass):
    coordinator, controller = make_coordinator(hass)
    group = BlindsGroupCover(
        name="Office",
        unique_id="uid-grp",
        group_num="1",
        controller=controller,
        coordinator=coordinator,
        entry_id="entry",
    )
    assert group.current_cover_position is None
    assert group.available is True

    await group.async_open_cover()
    controller.send_group_command.assert_awaited_with("1", "open")
    await group.async_close_cover()
    controller.send_group_command.assert_awaited_with("1", "close")
    await group.async_stop_cover()
    controller.send_group_command.assert_awaited_with("1", "stop")


@pytest.mark.skipif(
    AwesomeVersion(HA_VERSION) < AwesomeVersion("2026.9.0"),
    reason="DeviceInfo.via_device_id needs HA 2026.9+; the Python 3.13 test env caps HA at 2026.2",
)
async def test_setup_adds_every_entity_linked_to_controller(hass, caplog):
    """Every configured device and group must be added (HA 2026.9+ rejects via_device)."""
    from unittest.mock import patch

    from homeassistant.helpers import device_registry as dr
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.blinds_control import DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "http_base_url": "http://controller.test",
            "http_username": "user",
            "http_password": "pass",
            "devices": [
                {"id": "1,01", "name": "MBA 3", "module": "Era Mat MA (1,1)", "adr": "1", "ept": "01"},
                {"id": "1,02", "name": "MBA 1", "module": "Era Mat MA (1,2)", "adr": "1", "ept": "02"},
            ],
            "groups": [{"num": "1", "name": "Office"}],
        },
    )
    entry.add_to_hass(hass)
    status = {
        "1,01": {"status_code": "05", "position": 0},
        "1,02": {"status_code": "04", "position": 100},
    }
    with patch(
        "custom_components.blinds_control.cover.NiceController.get_all_device_status",
        return_value=status,
    ), patch("custom_components.blinds_control.cover.NiceController.cleanup"):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        states = {s.entity_id: s.state for s in hass.states.async_all("cover")}
        assert states == {
            "cover.mba_3": "closed",
            "cover.mba_1": "open",
            "cover.office_group_office": "unknown",
        }

        registry = dr.async_get(hass)
        devices = dr.async_entries_for_config_entry(registry, entry.entry_id)
        (controller,) = [d for d in devices if (DOMAIN, entry.entry_id) in d.identifiers]
        children = [d for d in devices if d.id != controller.id]
        assert len(children) == 3
        assert all(d.via_device_id == controller.id for d in children)
        assert "via_device" not in caplog.text

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
