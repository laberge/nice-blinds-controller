"""Nice HTTP controller for blind motors."""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Nice protocol command codes; group commands pad the code to four bytes.
CMD_CODES = {"stop": "02", "open": "03", "close": "04"}
GROUP_CMD_DATA = {cmd: f"{code}000000" for cmd, code in CMD_CODES.items()}

# Status codes reported in the devlst.xml `sta` attribute.
STATUS_OPENING = "02"
STATUS_CLOSING = "03"
STATUS_OPEN = "04"
STATUS_CLOSED = "05"

# The `pos` attribute value meaning "position unknown".
POSITION_UNKNOWN = "255"

# Position a device ends at for each command.
TARGET_POSITION = {"open": 100, "close": 0}

# Group membership is a little-endian bitmask in the grpitm.xml `dat`
# attribute; an endpoint's bit index is its number plus this offset.
GROUP_MASK_BIT_OFFSET = 32

# Markers that indicate the controller answered with its login page.
_HTML_MARKERS = ("<!doctype html", "<html", "login", "password")


def unresponsive_members(
    command: str,
    members: list[str],
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> list[str]:
    """Return the group members that show no reaction to a group command.

    A group command is one broadcast on the motor bus, so a motor that misses
    it never moves and nothing reports the miss. `before` and `after` are
    status maps taken before the command and a few seconds after it.
    """
    missed = []
    for device_id in members:
        now = after.get(device_id)
        if now is None:
            continue
        if command == "stop":
            if now["status_code"] in (STATUS_OPENING, STATUS_CLOSING):
                missed.append(device_id)
            continue
        was = before.get(device_id)
        if was is None or now["position"] == TARGET_POSITION[command]:
            continue
        if (was["status_code"], was["position"]) == (now["status_code"], now["position"]):
            missed.append(device_id)
    return missed


class NiceController:
    """HTTP client for a Nice controller (IT4WiFi, MyNice, etc.)."""

    def __init__(self, http_config: dict[str, Any]) -> None:
        """Initialize with a config dict of base_url, username, password, timeout."""
        self.http_config = http_config
        self._http_session: aiohttp.ClientSession | None = None

    async def _ensure_initialized(self) -> None:
        """Create the shared HTTP session on first use."""
        if self._http_session is None:
            timeout = aiohttp.ClientTimeout(total=self.http_config.get("timeout", 10))
            self._http_session = aiohttp.ClientSession(timeout=timeout)

    def _auth_headers(self) -> dict[str, str] | None:
        """Build basic auth from config, or None if no credentials."""
        username = self.http_config.get("username")
        password = self.http_config.get("password")
        if username and password:
            return {"Authorization": aiohttp.encode_basic_auth(username, password)}
        return None

    def _url(self, path: str) -> str:
        """Build a full controller URL from a path/query."""
        base_url = self.http_config.get("base_url", "")
        return f"{base_url.rstrip('/')}/{path}"

    async def _fetch_xml(self, path: str) -> ET.Element:
        """GET a controller endpoint and return the parsed XML root.

        Raises ClientResponseError on HTTP errors and when the controller
        answers with its HTML login page (misconfigured credentials).
        """
        await self._ensure_initialized()

        async with self._http_session.get(self._url(path), headers=self._auth_headers()) as response:
            response.raise_for_status()
            text = await response.text()

            lowered = text.lower()
            if any(marker in lowered for marker in _HTML_MARKERS):
                _LOGGER.error("Received HTML/login page instead of XML. Check credentials.")
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=401,
                    message="Authentication failed - received HTML instead of XML",
                )

        try:
            return ET.fromstring(text)
        except ET.ParseError as err:
            _LOGGER.error("Failed to parse XML from %s: %s", path, err)
            raise

    @staticmethod
    def _parse_device_id(device_elem: ET.Element) -> str | None:
        """Return the "adr,ept" command ID for a device element.

        The controller reports adr/ept as hex, but device commands expect
        a decimal adr and an uppercase-hex ept.
        """
        try:
            adr_dec = int(device_elem.get("adr", "0"), 16)
        except ValueError:
            _LOGGER.debug("Skipping device with invalid adr: %s", device_elem.get("adr"))
            return None
        return f"{adr_dec},{device_elem.get('ept', '0').upper()}"

    async def send_command(self, device_id: str, command: str) -> None:
        """Send an open/close/stop command to a device ("adr,ept" ID)."""
        cmd = CMD_CODES.get(command)
        if cmd is None:
            _LOGGER.error("Unknown command: %s", command)
            return

        try:
            adr, ept = device_id.split(",")
        except ValueError:
            _LOGGER.error("Invalid device_id format. Expected 'adr,ept', got: %s", device_id)
            return

        await self._ensure_initialized()
        url = self._url(f"cgi/devcmd.xml?adr={adr}&ept={ept}&cmd={cmd}")
        _LOGGER.debug("Sending command '%s' to device %s", command, device_id)
        async with self._http_session.get(url, headers=self._auth_headers()) as response:
            response.raise_for_status()

    async def send_group_command(self, group_num: str, command: str) -> None:
        """Send an open/close/stop command to a controller group."""
        dat = GROUP_CMD_DATA.get(command)
        if dat is None:
            _LOGGER.error("Unknown command: %s", command)
            return

        await self._ensure_initialized()
        url = self._url(f"cgi/grpcmd.xml?req=R&num={group_num}&dat={dat}")
        _LOGGER.debug("Sending command '%s' to group %s", command, group_num)
        async with self._http_session.get(url, headers=self._auth_headers()) as response:
            response.raise_for_status()
            text = await response.text()

        try:
            result = ET.fromstring(text).findtext(".//result", "0")
        except ET.ParseError:
            _LOGGER.warning("Could not parse group command response")
            return
        if result != "0":
            _LOGGER.warning("Group command '%s' returned result: %s", command, result)

    async def get_group_members(self, group_num: str) -> list[str]:
        """Return the "adr,ept" IDs of the devices in a controller group."""
        root = await self._fetch_xml(f"cgi/grpitm.xml?num={group_num}")

        members = []
        for row in root.findall(".//command"):
            try:
                adr_dec = int(row.get("adr", "0"), 16)
                mask = int.from_bytes(bytes.fromhex(row.get("dat", "")), "little")
            except ValueError:
                _LOGGER.debug("Skipping unreadable row in group %s", group_num)
                continue
            members.extend(
                f"{adr_dec},{bit - GROUP_MASK_BIT_OFFSET:02X}"
                for bit in range(GROUP_MASK_BIT_OFFSET, mask.bit_length())
                if mask >> bit & 1
            )
        return members

    async def resend_to_unresponsive(
        self, group_num: str, command: str, before: dict[str, dict[str, Any]]
    ) -> list[str]:
        """Send `command` directly to group members that ignored a group command.

        Call a few seconds after send_group_command, with the status map from
        before it. Returns the device IDs the command was re-sent to.
        """
        members = await self.get_group_members(group_num)
        after = await self.get_all_device_status()
        missed = unresponsive_members(command, members, before, after)
        for device_id in missed:
            await self.send_command(device_id, command)
        return missed

    async def test_connection(self) -> bool:
        """Return True if the controller base URL is reachable."""
        await self._ensure_initialized()

        base_url = self.http_config.get("base_url", "")
        try:
            async with self._http_session.get(base_url, headers=self._auth_headers()) as response:
                return response.status < 500
        except Exception as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False

    async def get_device_status(self, device_id: str) -> dict[str, Any] | None:
        """Get current status of a single device ("adr,ept" ID)."""
        statuses = await self.get_all_device_status()
        return statuses.get(device_id)

    async def get_all_device_status(self) -> dict[str, dict[str, Any]]:
        """Get status for all installed devices, keyed by "adr,ept" ID."""
        root = await self._fetch_xml("cgi/devlst.xml")

        status_map: dict[str, dict[str, Any]] = {}
        for device_elem in root.findall(".//device"):
            if device_elem.get("installed", "0") != "1":
                continue
            device_id = self._parse_device_id(device_elem)
            if device_id is None:
                continue

            pos_raw = device_elem.get("pos", POSITION_UNKNOWN)
            try:
                position = None if pos_raw == POSITION_UNKNOWN else int(pos_raw)
            except ValueError:
                position = None

            status_map[device_id] = {
                "status_code": device_elem.get("sta", "00").upper(),
                "position": position,
                "raw_position": pos_raw,
                "input": device_elem.get("inp", "0"),
            }

        return status_map

    async def discover_devices(self) -> list[dict[str, str]]:
        """Discover installed devices.

        Returns:
            List of device dicts with 'id', 'name', 'module', 'adr', 'ept'.
        """
        root = await self._fetch_xml("cgi/devlst.xml")

        devices = []
        for device_elem in root.findall(".//device"):
            if device_elem.get("installed", "0") != "1":
                continue
            device_id = self._parse_device_id(device_elem)
            if device_id is None:
                continue

            adr_dec, ept = device_id.split(",")
            product_name = device_elem.get("productName", "Unknown")
            devices.append(
                {
                    "id": device_id,
                    "name": device_elem.get("desc") or product_name,
                    "module": f"{product_name} ({adr_dec},{int(ept, 16)})",
                    "adr": adr_dec,
                    "ept": ept,
                }
            )

        _LOGGER.debug("Discovered %d installed devices", len(devices))
        return devices

    async def discover_groups(self) -> list[dict[str, Any]]:
        """Discover enabled controller groups.

        Returns:
            List of group dicts with 'num', 'name', 'enabled'.
        """
        root = await self._fetch_xml("cgi/grplst.xml")

        groups = []
        for group_elem in root.findall(".//group"):
            if group_elem.get("enabled", "0") != "1":
                continue
            num = group_elem.get("num", "0")
            groups.append(
                {
                    "num": num,
                    "name": group_elem.get("desc") or f"Group {num}",
                    "enabled": "1",
                }
            )

        _LOGGER.debug("Discovered %d enabled groups", len(groups))
        return groups

    async def cleanup(self) -> None:
        """Close the shared HTTP session."""
        if self._http_session is not None:
            await self._http_session.close()
            self._http_session = None
