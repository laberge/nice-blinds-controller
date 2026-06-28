"""Tests for the config and options flows."""
import aiohttp
from aioresponses import aioresponses
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.blinds_control import DOMAIN

from .conftest import BASE_URL


async def _start_connection(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )


async def test_full_flow_creates_entry(hass, device_list_xml, group_list_xml):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/cgi/devlst.xml", status=200, body=device_list_xml)
        m.get(f"{BASE_URL}/cgi/grplst.xml", status=200, body=group_list_xml)

        result = await _start_connection(hass)
        assert result["step_id"] == "http_connection"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "http_base_url": BASE_URL,
                "http_username": "user",
                "http_password": "pass",
                "http_timeout": 10,
            },
        )
        assert result["step_id"] == "select_devices"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"devices": ["1,01", "1,0F"], "move_time": 25},
        )
        assert result["step_id"] == "review_groups"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"use_groups": True}
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    data = result["data"]
    assert data["move_time"] == 25
    assert {d["id"] for d in data["devices"]} == {"1,01", "1,0F"}
    assert [g["num"] for g in data["groups"]] == ["1", "3"]


async def test_reject_groups_creates_entry_without_them(
    hass, device_list_xml, group_list_xml
):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/cgi/devlst.xml", status=200, body=device_list_xml)
        m.get(f"{BASE_URL}/cgi/grplst.xml", status=200, body=group_list_xml)

        result = await _start_connection(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "http_base_url": BASE_URL,
                "http_username": "user",
                "http_password": "pass",
                "http_timeout": 10,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"devices": ["1,01"], "move_time": 30}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"use_groups": False}
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["groups"] == []


async def test_invalid_url(hass):
    result = await _start_connection(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "http_base_url": "192.168.1.1",  # no scheme
            "http_username": "user",
            "http_password": "pass",
            "http_timeout": 10,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"http_base_url": "invalid_url"}


async def test_invalid_auth(hass):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/cgi/devlst.xml", status=401)
        result = await _start_connection(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "http_base_url": BASE_URL,
                "http_username": "user",
                "http_password": "bad",
                "http_timeout": 10,
            },
        )
    assert result["errors"] == {"base": "invalid_auth"}


async def test_cannot_connect(hass):
    with aioresponses() as m:
        m.get(
            f"{BASE_URL}/cgi/devlst.xml",
            exception=aiohttp.ClientConnectionError("no route"),
        )
        result = await _start_connection(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "http_base_url": BASE_URL,
                "http_username": "user",
                "http_password": "pass",
                "http_timeout": 10,
            },
        )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_no_devices_found(hass, empty_device_list_xml):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/cgi/devlst.xml", status=200, body=empty_device_list_xml)
        result = await _start_connection(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "http_base_url": BASE_URL,
                "http_username": "user",
                "http_password": "pass",
                "http_timeout": 10,
            },
        )
    assert result["errors"] == {"base": "no_devices_found"}


async def test_options_refresh_updates_entry(hass, device_list_xml, group_list_xml):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Nice Controller",
        unique_id="nice_controller_test",
        data={
            "http_base_url": BASE_URL,
            "http_username": "user",
            "http_password": "pass",
            "http_timeout": 10,
            "move_time": 30,
            "devices": [{"id": "1,01", "name": "MBA 3", "module": "m", "adr": "1", "ept": "01"}],
            "groups": [],
        },
    )
    entry.add_to_hass(hass)

    with aioresponses() as m:
        # Needed by the refresh itself and by the reload's coordinator refresh.
        m.get(f"{BASE_URL}/cgi/devlst.xml", status=200, body=device_list_xml, repeat=True)
        m.get(f"{BASE_URL}/cgi/grplst.xml", status=200, body=group_list_xml, repeat=True)

        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["step_id"] == "main_menu"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"action": "refresh"}
        )
        assert result["step_id"] == "refresh_devices"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"confirm_refresh": True}
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert {d["id"] for d in entry.data["devices"]} == {"1,01", "1,0F", "10,05"}
    assert [g["num"] for g in entry.data["groups"]] == ["1", "3"]
