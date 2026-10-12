"""Tests for the standalone `blinds` CLI (no Home Assistant involved)."""
import base64
import os
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from unittest.mock import MagicMock

import aiohttp
import pytest
from aioresponses import aioresponses
from aioresponses.core import normalize_url

from custom_components.blinds_control.nice_protocol import NiceController

from .conftest import BASE_URL

CLI_PATH = Path(__file__).resolve().parent.parent / "blinds"
DEVLST = f"{BASE_URL}/cgi/devlst.xml"
GRPLST = f"{BASE_URL}/cgi/grplst.xml"
USER, PASS = "user", "pass"


def _load_cli():
    loader = SourceFileLoader("blinds_cli", str(CLI_PATH))
    module = module_from_spec(spec_from_loader("blinds_cli", loader))
    loader.exec_module(module)
    return module


@pytest.fixture
def cli(tmp_path, monkeypatch):
    """The CLI module with retries instant and diagnostics logged to tmp."""
    module = _load_cli()
    monkeypatch.setattr(module, "RETRY_BACKOFF", 0)
    monkeypatch.setattr(module, "DIAG_LOG", str(tmp_path / "blinds-cli.log"))
    return module


def no_route_error():
    return aiohttp.ClientConnectorError(MagicMock(), OSError(65, "No route to host"))


def requested_urls(m):
    return [str(url) for (_method, url) in m.requests]


def was_requested(m, url):
    return str(normalize_url(url)) in requested_urls(m)


# --- auth -----------------------------------------------------------------------

def test_auth_headers(cli):
    expected = "Basic " + base64.b64encode(b"user:pass").decode()
    assert cli._auth_headers("user", "pass") == {"Authorization": expected}
    assert cli._auth_headers("user", "") is None
    assert cli._auth_headers("", "pass") is None


async def test_requests_send_basic_auth(cli, device_list_xml):
    with aioresponses() as m:
        m.get(DEVLST, status=200, body=device_list_xml)
        await cli.get_devices(BASE_URL, USER, PASS)
        (call,) = next(iter(m.requests.values()))
    assert call.kwargs["headers"] == cli._auth_headers(USER, PASS)


# --- parsing --------------------------------------------------------------------

async def test_get_devices_ids_and_names(cli, device_list_xml):
    with aioresponses() as m:
        m.get(DEVLST, status=200, body=device_list_xml)
        devices = await cli.get_devices(BASE_URL + "/", USER, PASS)

    # Keyed by lowercase name; adr hex -> decimal, ept uppercase hex; not-installed skipped.
    assert devices == {"mba 3": "1,01", "office 3": "1,0F", "sunroom 1": "10,05"}


async def test_cli_device_ids_match_integration(cli, http_config, device_list_xml):
    """The CLI duplicates the integration's ID logic; they must never drift."""
    controller = NiceController(http_config)
    with aioresponses() as m:
        m.get(DEVLST, status=200, body=device_list_xml)
        m.get(DEVLST, status=200, body=device_list_xml)
        cli_ids = set((await cli.get_devices(BASE_URL, USER, PASS)).values())
        integration_ids = {d["id"] for d in await controller.discover_devices()}
    await controller.cleanup()
    assert cli_ids == integration_ids


async def test_get_device_status(cli, device_list_xml):
    with aioresponses() as m:
        m.get(DEVLST, status=200, body=device_list_xml)
        devices = await cli.get_device_status(BASE_URL, USER, PASS)

    by_name = {d["name"]: d for d in devices}
    assert set(by_name) == {"MBA 3", "Office 3", "Sunroom 1"}
    assert by_name["MBA 3"]["status"] == "Closed (low limit)"
    assert by_name["MBA 3"]["position"] == "0%"
    assert by_name["Office 3"]["status"] == "Open (high limit)"
    assert by_name["Office 3"]["id"] == "1,0F"
    assert by_name["Sunroom 1"]["status"] == "Opening"
    assert by_name["Sunroom 1"]["position"] == "Unknown"  # pos="255"


async def test_get_device_status_filters_by_name(cli, device_list_xml):
    with aioresponses() as m:
        m.get(DEVLST, status=200, body=device_list_xml)
        devices = await cli.get_device_status(BASE_URL, USER, PASS, "  OFFICE 3 ")
    assert [d["id"] for d in devices] == ["1,0F"]


async def test_get_controller_groups_skips_disabled(cli, group_list_xml):
    with aioresponses() as m:
        m.get(GRPLST, status=200, body=group_list_xml)
        groups = await cli.get_controller_groups(BASE_URL, USER, PASS)
    assert groups == {
        "office": {"num": "1", "name": "Office"},
        "sunroom": {"num": "3", "name": "Sunroom"},
    }


# --- device commands ------------------------------------------------------------

@pytest.mark.parametrize("command, code", [("stop", "02"), ("open", "03"), ("close", "04")])
async def test_send_command_codes(cli, command, code):
    url = f"{BASE_URL}/cgi/devcmd.xml?adr=1&ept=0F&cmd={code}"
    with aioresponses() as m:
        m.get(url, status=200, body="<ok/>")
        assert await cli.send_command(BASE_URL, USER, PASS, "1,0F", command) is True
        assert requested_urls(m) == [str(normalize_url(url))]


async def test_main_async_resolves_name_and_sends(cli, device_list_xml, capsys):
    cmd_url = f"{BASE_URL}/cgi/devcmd.xml?adr=10&ept=05&cmd=04"
    with aioresponses() as m:
        m.get(DEVLST, status=200, body=device_list_xml)
        m.get(cmd_url, status=200, body="<ok/>")
        assert await cli.main_async("close", "sunroom 1", BASE_URL, USER, PASS) is True
        assert was_requested(m, cmd_url)
    assert "CLOSE: Sunroom 1" in capsys.readouterr().out


async def test_main_async_unknown_device(cli, device_list_xml, capsys):
    with aioresponses() as m:
        m.get(DEVLST, status=200, body=device_list_xml)
        assert await cli.main_async("open", "Garage", BASE_URL, USER, PASS) is False
        assert not any("devcmd" in u for u in requested_urls(m))
    out = capsys.readouterr().out
    assert "Device 'Garage' not found" in out
    assert "Office 3" in out


async def test_main_async_auth_failure(cli, capsys):
    with aioresponses() as m:
        m.get(DEVLST, status=401)
        assert await cli.main_async("open", "Office 3", BASE_URL, USER, PASS) is False
    assert "Authentication failed" in capsys.readouterr().out


# --- group commands -------------------------------------------------------------

@pytest.mark.parametrize("command, dat", [("stop", "02000000"), ("open", "03000000"), ("close", "04000000")])
async def test_send_group_command(cli, group_list_xml, command, dat):
    url = f"{BASE_URL}/cgi/grpcmd.xml?req=R&num=3&dat={dat}"
    with aioresponses() as m:
        m.get(GRPLST, status=200, body=group_list_xml)
        m.get(url, status=200, body="<nice><result>0</result></nice>")
        assert await cli.send_group_command("SUNROOM", command, BASE_URL, USER, PASS) is True
        assert was_requested(m, url)


async def test_send_group_command_controller_rejects(cli, group_list_xml):
    with aioresponses() as m:
        m.get(GRPLST, status=200, body=group_list_xml)
        m.get(f"{BASE_URL}/cgi/grpcmd.xml?req=R&num=1&dat=03000000", status=200,
              body="<nice><result>1</result></nice>")
        assert await cli.send_group_command("Office", "open", BASE_URL, USER, PASS) is False


async def test_send_group_command_unknown_or_disabled_group(cli, group_list_xml, capsys):
    with aioresponses() as m:
        m.get(GRPLST, status=200, body=group_list_xml)
        assert await cli.send_group_command("Disabled", "open", BASE_URL, USER, PASS) is False
        assert not any("grpcmd" in u for u in requested_urls(m))
    assert "Group 'Disabled' not found" in capsys.readouterr().out


# --- transient-connection retry -------------------------------------------------

async def test_retry_recovers_from_transient_no_route(cli, device_list_xml):
    with aioresponses() as m:
        m.get(DEVLST, exception=no_route_error())
        m.get(DEVLST, exception=no_route_error())
        m.get(DEVLST, status=200, body=device_list_xml)
        devices = await cli.get_devices(BASE_URL, USER, PASS)
    assert devices["office 3"] == "1,0F"

    log = Path(cli.DIAG_LOG).read_text()
    assert "get_devices attempt 1/3 failed" in log
    assert "get_devices attempt 2/3 failed" in log
    assert "get_devices recovered on attempt 3" in log


async def test_retry_gives_up_after_three_attempts(cli):
    with aioresponses() as m:
        for _ in range(4):
            m.get(DEVLST, exception=no_route_error())
        with pytest.raises(aiohttp.ClientConnectorError):
            await cli.get_devices(BASE_URL, USER, PASS)
        assert len(requested_urls(m)) == 1  # one URL key...
        assert len(next(iter(m.requests.values()))) == 3  # ...hit exactly 3 times
    assert "attempt 3/3 failed" in Path(cli.DIAG_LOG).read_text()


async def test_http_errors_are_not_retried(cli):
    with aioresponses() as m:
        m.get(DEVLST, status=500)
        m.get(DEVLST, status=200, body="<devlst/>")
        with pytest.raises(aiohttp.ClientResponseError):
            await cli.get_devices(BASE_URL, USER, PASS)
        assert len(next(iter(m.requests.values()))) == 1
    assert not Path(cli.DIAG_LOG).exists()


async def test_group_command_retries_both_requests(cli, group_list_xml):
    grpcmd = f"{BASE_URL}/cgi/grpcmd.xml?req=R&num=1&dat=02000000"
    with aioresponses() as m:
        m.get(GRPLST, exception=no_route_error())
        m.get(GRPLST, status=200, body=group_list_xml)
        m.get(grpcmd, exception=no_route_error())
        m.get(grpcmd, status=200, body="<nice><result>0</result></nice>")
        assert await cli.send_group_command("office", "stop", BASE_URL, USER, PASS) is True


async def test_unreachable_controller_reports_cleanly(cli, capsys):
    with aioresponses() as m:
        for _ in range(3):
            m.get(DEVLST, exception=no_route_error())
        assert await cli.main_async("open", "Office 3", BASE_URL, USER, PASS) is False
    assert "Cannot connect to controller" in capsys.readouterr().out


# --- argv handling (subprocess, never reaches the network) ----------------------

def run_cli(*args, **env):
    full_env = {**os.environ, "BLINDS_URL": "", "BLINDS_PASS": "", **env}
    return subprocess.run([sys.executable, str(CLI_PATH), *args],
                          capture_output=True, text=True, env=full_env, timeout=30)


def test_cli_no_args_prints_usage():
    result = run_cli()
    assert result.returncode == 1
    assert "Usage:" in result.stdout


def test_cli_requires_url_and_password():
    assert "Controller URL not configured" in run_cli("list").stdout
    assert "Password not configured" in run_cli("list", BLINDS_URL=BASE_URL).stdout


def test_cli_rejects_invalid_commands():
    env = {"BLINDS_URL": BASE_URL, "BLINDS_PASS": "x"}
    bad = run_cli("toggle", "Office 3", **env)
    assert bad.returncode == 1 and "Invalid command 'toggle'" in bad.stdout
    bad_group = run_cli("toggle-group", "Office", **env)
    assert bad_group.returncode == 1 and "Invalid group command" in bad_group.stdout
    missing = run_cli("open-group", **env)
    assert missing.returncode == 1 and "Group name required" in missing.stdout
