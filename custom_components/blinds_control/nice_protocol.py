"""Nice protocol controller for blind motors."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)


class NiceController:
    """Controller for Nice protocol blind motors."""

    def __init__(
        self,
        protocol_type: str = "rf433",
        gpio_pin: int = 17,
        http_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the Nice controller.

        Args:
            protocol_type: Type of Nice protocol (rf433, bidi_bus, http)
            gpio_pin: GPIO pin for RF transmitter (for RF433 protocol)
            http_config: HTTP configuration dict with base_url, endpoints, auth, timeout
        """
        self.protocol_type = protocol_type
        self.gpio_pin = gpio_pin
        self.http_config = http_config or {}
        self._initialized = False
        self._tx_module = None
        self._http_session = None

        _LOGGER.info(
            "Nice controller initialized with protocol: %s, GPIO: %s",
            protocol_type,
            gpio_pin,
        )

    async def _initialize_rf433(self) -> None:
        """Initialize RF 433MHz transmitter.

        This method should be implemented based on your specific hardware.
        Common options:
        - rpi-rf library for Raspberry Pi
        - pigpio library for more precise timing
        - Custom implementation based on your hardware
        """
        try:
            # Example using rpi-rf (uncomment when you have the library installed):
            # from rpi_rf import RFDevice
            # self._tx_module = RFDevice(self.gpio_pin)
            # self._tx_module.enable_tx()

            # For now, just mark as initialized
            self._initialized = True
            _LOGGER.info("RF433 transmitter initialized on GPIO %s", self.gpio_pin)
        except Exception as err:
            _LOGGER.error("Failed to initialize RF433 transmitter: %s", err)
            raise

    async def _initialize_bidi_bus(self) -> None:
        """Initialize BiDi-Bus communication.

        This would require implementation specific to Nice BiDi-Bus protocol.
        Typically involves serial communication or network protocol.
        """
        # TODO: Implement BiDi-Bus initialization
        self._initialized = True
        _LOGGER.info("BiDi-Bus initialized")

    async def _initialize_http(self) -> None:
        """Initialize HTTP session for API communication."""
        try:
            timeout = aiohttp.ClientTimeout(total=self.http_config.get("timeout", 10))
            self._http_session = aiohttp.ClientSession(timeout=timeout)
            self._initialized = True
            _LOGGER.info("HTTP controller initialized with base URL: %s", self.http_config.get("base_url"))
        except Exception as err:
            _LOGGER.error("Failed to initialize HTTP session: %s", err)
            raise

    async def _ensure_initialized(self) -> None:
        """Ensure the controller is initialized."""
        if not self._initialized:
            if self.protocol_type == "rf433":
                await self._initialize_rf433()
            elif self.protocol_type == "bidi_bus":
                await self._initialize_bidi_bus()
            elif self.protocol_type == "http":
                await self._initialize_http()
            else:
                _LOGGER.warning("Unknown protocol type: %s", self.protocol_type)
                self._initialized = True

    async def send_command(
        self, device_id: str | None, command: str, **kwargs: Any
    ) -> None:
        """Send a command to the Nice motor.

        Args:
            device_id: Device identifier (e.g., RF code, channel number)
            command: Command to send (open, close, stop)
            **kwargs: Additional parameters for the command
        """
        await self._ensure_initialized()

        _LOGGER.info(
            "Sending Nice protocol command: %s to device: %s", command, device_id
        )

        if self.protocol_type == "rf433":
            await self._send_rf433_command(device_id, command)
        elif self.protocol_type == "bidi_bus":
            await self._send_bidi_bus_command(device_id, command)
        elif self.protocol_type == "http":
            await self._send_http_command(device_id, command)
        else:
            _LOGGER.error("Unsupported protocol type: %s", self.protocol_type)

    async def _send_rf433_command(self, device_id: str | None, command: str) -> None:
        """Send RF 433MHz command.

        Nice motors typically use specific RF codes for each operation.
        You'll need to learn/capture these codes from your existing remote.

        Common approaches:
        1. Use RF receiver to capture existing remote codes
        2. Use manufacturer-provided codes
        3. Generate codes based on Nice protocol specification
        """
        # Command mapping (you'll need to replace these with actual codes)
        # These should be learned from your actual Nice remote
        command_codes = {
            "open": None,  # Replace with actual code
            "close": None,  # Replace with actual code
            "stop": None,  # Replace with actual code
        }

        code = command_codes.get(command)

        if code is None:
            _LOGGER.warning(
                "No RF code configured for command '%s'. "
                "Please capture codes from your Nice remote.",
                command,
            )
            return

        try:
            # Example transmission (uncomment when rpi-rf is installed):
            # if self._tx_module:
            #     self._tx_module.tx_code(code, protocol=1, pulselength=350)
            #     _LOGGER.debug("Transmitted RF code: %s", code)

            # Simulate transmission for now
            await asyncio.sleep(0.1)
            _LOGGER.debug(
                "RF433 command '%s' sent to device %s (code: %s)",
                command,
                device_id,
                code,
            )

        except Exception as err:
            _LOGGER.error("Failed to send RF433 command: %s", err)
            raise

    async def _send_bidi_bus_command(self, device_id: str | None, command: str) -> None:
        """Send BiDi-Bus command.

        Nice BiDi-Bus protocol implementation.
        This requires specific protocol knowledge and hardware interface.
        """
        # TODO: Implement actual BiDi-Bus command transmission
        await asyncio.sleep(0.1)
        _LOGGER.debug("BiDi-Bus command '%s' sent to device %s", command, device_id)

    async def _send_http_command(self, device_id: str | None, command: str) -> None:
        """Send HTTP API command to Nice controller.

        Args:
            device_id: Device endpoint in format "adr,ept" (e.g., "1,0F")
            command: Command to send (open, close, stop)
        """
        if not self._http_session:
            _LOGGER.error("HTTP session not initialized")
            return

        # Parse device_id to extract address and endpoint
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
        """Discover devices from Nice controller.

        Returns:
            List of device dicts with 'id', 'name', 'module', 'adr', 'ept'
        """
        if not self._http_session:
            await self._ensure_initialized()

        if self.protocol_type != "http":
            _LOGGER.warning("Device discovery only available for HTTP protocol")
            return []

        base_url = self.http_config.get("base_url", "")
        url = f"{base_url.rstrip('/')}/dev_list.htm"

        auth = None
        username = self.http_config.get("username")
        password = self.http_config.get("password")
        if username and password:
            auth = aiohttp.BasicAuth(username, password)

        try:
            _LOGGER.info("Fetching device list from: %s", url)
            async with self._http_session.get(url, auth=auth) as response:
                _LOGGER.info("HTTP Response status: %s", response.status)
                response.raise_for_status()
                html = await response.text()
                _LOGGER.debug("HTML response length: %d bytes", len(html))

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
            return []
        except Exception as err:
            _LOGGER.error("Failed to discover devices: %s", err, exc_info=True)
            return []

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._tx_module:
            try:
                # Example cleanup for rpi-rf:
                # self._tx_module.cleanup()
                pass
            except Exception as err:
                _LOGGER.error("Error during cleanup: %s", err)

        if self._http_session:
            try:
                await self._http_session.close()
            except Exception as err:
                _LOGGER.error("Error closing HTTP session: %s", err)

        self._initialized = False
        _LOGGER.info("Nice controller cleaned up")
