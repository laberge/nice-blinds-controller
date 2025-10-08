"""Nice HTTP controller for blind motors."""
from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)


class NiceController:
    """HTTP controller for Nice blind motors."""

    def __init__(self, http_config: dict[str, Any]) -> None:
        """Initialize the Nice HTTP controller.

        Args:
            http_config: HTTP configuration dict with base_url, username, password, timeout
        """
        self.http_config = http_config
        self._initialized = False
        self._http_session = None

        _LOGGER.info(
            "Nice HTTP controller initialized with base URL: %s",
            http_config.get("base_url"),
        )

    async def _initialize_http(self) -> None:
        """Initialize HTTP session for API communication."""
        try:
            timeout = aiohttp.ClientTimeout(total=self.http_config.get("timeout", 10))
            self._http_session = aiohttp.ClientSession(timeout=timeout)
            self._initialized = True
            _LOGGER.info("HTTP session initialized with base URL: %s", self.http_config.get("base_url"))
        except Exception as err:
            _LOGGER.error("Failed to initialize HTTP session: %s", err)
            raise

    async def _ensure_initialized(self) -> None:
        """Ensure the controller is initialized."""
        if not self._initialized:
            await self._initialize_http()

    async def send_command(self, device_id: str, command: str) -> None:
        """Send a command to the Nice motor via HTTP.

        Args:
            device_id: Device identifier in format "adr,ept" (e.g., "1,0F")
            command: Command to send (open, close, stop)
        """
        await self._ensure_initialized()

        _LOGGER.info("Sending command: %s to device: %s", command, device_id)

        if not self._http_session:
            _LOGGER.error("HTTP session not initialized")
            return

        if not device_id:
            _LOGGER.error("Device ID is required for HTTP commands")
            return

        try:
            # Device ID format: "adr,ept" (e.g., "1,0F")
            parts = device_id.split(",")
            if len(parts) != 2:
                _LOGGER.error("Invalid device_id format. Expected 'adr,ept', got: %s", device_id)
                return

            adr = parts[0]
            ept = parts[1]

            # Map commands to Nice protocol command codes
            cmd_codes = {
                "stop": "02",
                "open": "03",
                "close": "04",
            }

            cmd = cmd_codes.get(command)
            if not cmd:
                _LOGGER.error("Unknown command: %s", command)
                return

            # Build URL: /cgi/devcmd.xml?adr=1&ept=0F&cmd=03
            base_url = self.http_config.get("base_url", "")
            url = f"{base_url.rstrip('/')}/cgi/devcmd.xml?adr={adr}&ept={ept}&cmd={cmd}"

            # Prepare authentication
            auth = None
            username = self.http_config.get("username")
            password = self.http_config.get("password")
            if username and password:
                auth = aiohttp.BasicAuth(username, password)

            _LOGGER.debug("Sending HTTP request to: %s", url)
            async with self._http_session.get(url, auth=auth) as response:
                response.raise_for_status()
                _LOGGER.info(
                    "HTTP command '%s' sent successfully to device %s (status: %s)",
                    command, device_id, response.status
                )

        except aiohttp.ClientError as err:
            _LOGGER.error("HTTP request failed for command '%s': %s", command, err)
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error sending HTTP command '%s': %s", command, err)
            raise

    async def discover_devices(self) -> list[dict[str, str]]:
        """Discover devices from Nice HTTP controller.

        Returns:
            List of device dicts with 'id', 'name', 'module', 'adr', 'ept'
        """
        if not self._http_session:
            await self._ensure_initialized()

        base_url = self.http_config.get("base_url", "")
        url = f"{base_url.rstrip('/')}/dev_list.htm"

        auth = None
        username = self.http_config.get("username")
        password = self.http_config.get("password")
        _LOGGER.info("HTTP config: base_url=%s, username=%s, password=%s",
                     self.http_config.get("base_url"),
                     username,
                     "***" if password else None)
        if username and password:
            auth = aiohttp.BasicAuth(username, password)
            _LOGGER.info("BasicAuth configured for user: %s", username)
        else:
            _LOGGER.warning("No authentication configured! username=%s, password=%s", username, "***" if password else None)

        try:
            _LOGGER.info("Fetching device list from: %s (with auth: %s)", url, auth is not None)
            async with self._http_session.get(url, auth=auth) as response:
                _LOGGER.info("HTTP Response status: %s", response.status)
                response.raise_for_status()
                html = await response.text()
                _LOGGER.info("HTML response length: %d bytes", len(html))
                _LOGGER.debug("First 500 chars of HTML: %s", html[:500])

                # Parse HTML to extract device information
                soup = BeautifulSoup(html, "html.parser")
                devices = []

                # Find all table rows with device data
                rows_found = 0
                for row in soup.find_all("tr"):
                    cells = row.find_all("td")
                    rows_found += 1
                    if len(cells) >= 2:
                        module_text = cells[0].get_text(strip=True)
                        description = cells[1].get_text(strip=True)
                        _LOGGER.debug("Checking row: module='%s', desc='%s'", module_text, description)

                        # Parse module format: "EI SM (1,1)" -> adr=1, ept=01
                        match = re.match(r"EI SM \((\d+),(\d+)\)", module_text)
                        if match and description:
                            adr = match.group(1)
                            ept_decimal = int(match.group(2))
                            ept_hex = f"{ept_decimal:02X}"

                            device = {
                                "id": f"{adr},{ept_hex}",
                                "name": description,
                                "module": module_text,
                                "adr": adr,
                                "ept": ept_hex,
                            }
                            devices.append(device)
                            _LOGGER.info("Found device: %s - %s", device["name"], device["id"])
                        else:
                            if module_text:
                                _LOGGER.debug("Row did not match pattern: '%s'", module_text)

                _LOGGER.info("Parsed %d table rows, discovered %d devices", rows_found, len(devices))
                return devices

        except aiohttp.ClientError as err:
            _LOGGER.error("HTTP error while discovering devices: %s", err)
            raise
        except Exception as err:
            _LOGGER.error("Failed to discover devices: %s", err, exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._http_session:
            try:
                await self._http_session.close()
            except Exception as err:
                _LOGGER.error("Error closing HTTP session: %s", err)

        self._initialized = False
        _LOGGER.info("Nice controller cleaned up")
