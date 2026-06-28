"""Tests for the NiceController HTTP protocol layer."""
import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.blinds_control.nice_protocol import NiceController

from .conftest import BASE_URL


def make_controller(http_config):
    return NiceController(http_config)


async def test_discover_devices_parses_and_converts(http_config, device_list_xml):
    controller = make_controller(http_config)
    with aioresponses() as m:
        m.get(f"{BASE_URL}/cgi/devlst.xml", status=200, body=device_list_xml)
        devices = await controller.discover_devices()
    await controller.cleanup()

    by_id = {d["id"]: d for d in devices}
    # Only installed devices; adr hex -> decimal, ept kept as uppercase hex.
    assert set(by_id) == {"1,01", "1,0F", "10,05"}
    assert by_id["1,01"]["name"] == "MBA 3"
    assert by_id["1,01"]["adr"] == "1"
    assert by_id["1,01"]["ept"] == "01"
    assert by_id["10,05"]["adr"] == "10"  # adr "0A" -> 10


async def test_get_all_device_status(http_config, device_list_xml):
    controller = make_controller(http_config)
    with aioresponses() as m:
        m.get(f"{BASE_URL}/cgi/devlst.xml", status=200, body=device_list_xml)
        status = await controller.get_all_device_status()
    await controller.cleanup()

    assert status["1,01"]["position"] == 0
    assert status["1,01"]["status_code"] == "05"
    assert status["1,0F"]["position"] == 100
    assert status["10,05"]["position"] is None  # pos="255" means unknown
    assert "1,20" not in status  # not installed


async def test_get_device_status_single(http_config, device_list_xml):
    controller = make_controller(http_config)
    with aioresponses() as m:
        m.get(f"{BASE_URL}/cgi/devlst.xml", status=200, body=device_list_xml)
        status = await controller.get_device_status("1,0F")
    await controller.cleanup()
    assert status["position"] == 100


@pytest.mark.parametrize(
    ("command", "code"),
    [("open", "03"), ("close", "04"), ("stop", "02")],
)
async def test_send_command_builds_url(http_config, command, code):
    controller = make_controller(http_config)
    url = f"{BASE_URL}/cgi/devcmd.xml?adr=1&ept=0F&cmd={code}"
    with aioresponses() as m:
        m.get(url, status=200, body="<r/>")
        await controller.send_command("1,0F", command)
        m.assert_called_once_with(url, auth=aiohttp.BasicAuth("user", "pass"))
    await controller.cleanup()


async def test_send_command_invalid_device_id_makes_no_request(http_config):
    controller = make_controller(http_config)
    with aioresponses() as m:
        await controller.send_command("not-valid", "open")
        assert len(m.requests) == 0  # returned before any HTTP call
    await controller.cleanup()


async def test_send_command_unknown_command_makes_no_request(http_config):
    controller = make_controller(http_config)
    with aioresponses() as m:
        await controller.send_command("1,0F", "wiggle")
        assert len(m.requests) == 0
    await controller.cleanup()


async def test_send_command_raises_on_http_error(http_config):
    controller = make_controller(http_config)
    with aioresponses() as m:
        m.get(f"{BASE_URL}/cgi/devcmd.xml?adr=1&ept=01&cmd=04", status=500)
        with pytest.raises(aiohttp.ClientError):
            await controller.send_command("1,01", "close")
    await controller.cleanup()


async def test_discover_groups_skips_disabled(http_config, group_list_xml):
    controller = make_controller(http_config)
    with aioresponses() as m:
        m.get(f"{BASE_URL}/cgi/grplst.xml", status=200, body=group_list_xml)
        groups = await controller.discover_groups()
    await controller.cleanup()
    assert [g["num"] for g in groups] == ["1", "3"]
    assert groups[0]["name"] == "Office"


@pytest.mark.parametrize(
    ("command", "dat"),
    [("open", "03000000"), ("close", "04000000"), ("stop", "02000000")],
)
async def test_send_group_command(http_config, command, dat):
    controller = make_controller(http_config)
    url = f"{BASE_URL}/cgi/grpcmd.xml?req=R&num=1&dat={dat}"
    with aioresponses() as m:
        m.get(url, status=200, body="<grpcmd><result>0</result></grpcmd>")
        await controller.send_group_command("1", command)
        m.assert_called_once()
    await controller.cleanup()


async def test_test_connection_ok(http_config):
    controller = make_controller(http_config)
    with aioresponses() as m:
        m.get(BASE_URL, status=200)
        assert await controller.test_connection() is True
    await controller.cleanup()


async def test_test_connection_failure_returns_false(http_config):
    controller = make_controller(http_config)
    with aioresponses() as m:
        m.get(BASE_URL, exception=aiohttp.ClientError("boom"))
        assert await controller.test_connection() is False
    await controller.cleanup()


async def test_cleanup_closes_session(http_config):
    controller = make_controller(http_config)
    await controller._ensure_initialized()
    assert controller._http_session is not None
    await controller.cleanup()
    assert controller._http_session is None
    assert controller._initialized is False


def test_auth_none_without_credentials():
    controller = NiceController({"base_url": BASE_URL})
    assert controller._auth() is None


def test_url_strips_trailing_slash():
    controller = NiceController({"base_url": "http://x/"})
    assert controller._url("cgi/devlst.xml") == "http://x/cgi/devlst.xml"
