"""Nice HTTP controller for blind motors."""
from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp
import xml.etree.ElementTree as ET

_LOGGER = logging.getLogger(__name__)

_LOGGER.debug("Nice protocol module loaded")


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

        _LOGGER.debug("NiceController initialized (base_url: %s)", http_config.get("base_url"))

    async def _initialize_http(self) -> None:
        """Initialize HTTP session for API communication."""
        try:
            timeout = aiohttp.ClientTimeout(total=self.http_config.get("timeout", 10))
            self._http_session = aiohttp.ClientSession(timeout=timeout)
            self._initialized = True
            _LOGGER.debug("HTTP session initialized (timeout: %ds)", self.http_config.get("timeout", 10))
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

    async def test_connection(self) -> bool:
        """Test if the controller is reachable.
        
        Returns:
            True if connection successful, False otherwise
        """
        await self._ensure_initialized()
        
        base_url = self.http_config.get("base_url", "")
        _LOGGER.debug("Testing connection to: %s", base_url)
        
        try:
            async with self._http_session.get(base_url) as response:
                _LOGGER.debug("Connection test response: %d", response.status)
                return response.status < 500
        except Exception as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False

    async def get_device_status(self, device_id: str) -> dict[str, str] | None:
        """Get current status of a specific device.
        
        Args:
            device_id: Device identifier in format "adr,ept" (e.g., "1,0E")
            
        Returns:
            Dict with device status info or None if not found
        """
        await self._ensure_initialized()
        
        if not self._http_session:
            _LOGGER.error("HTTP session not initialized")
            return None
            
        base_url = self.http_config.get("base_url", "")
        url = f"{base_url.rstrip('/')}/cgi/devlst.xml"
        
        auth = None
        username = self.http_config.get("username")
        password = self.http_config.get("password")
        if username and password:
            auth = aiohttp.BasicAuth(username, password)
        
        try:
            async with self._http_session.get(url, auth=auth) as response:
                response.raise_for_status()
                xml_content = await response.text()
                
                root = ET.fromstring(xml_content)
                device_elements = root.findall('.//device')
                
                # Parse device_id
                parts = device_id.split(",")
                if len(parts) != 2:
                    return None
                    
                search_adr = parts[0]
                search_ept = parts[1].upper()
                
                for device_elem in device_elements:
                    adr = device_elem.get('adr', '0')
                    ept = device_elem.get('ept', '0').upper()
                    
                    # Convert adr from hex to decimal for comparison
                    adr_dec = str(int(adr, 16))
                    
                    if adr_dec == search_adr and ept == search_ept:
                        return {
                            'sta': device_elem.get('sta', '00'),
                            'pos': device_elem.get('pos', '255'),
                            'inp': device_elem.get('inp', '0'),
                            'installed': device_elem.get('installed', '0'),
                        }
                
                return None
                
        except Exception as err:
            _LOGGER.error("Error getting device status: %s", err)
            return None

    async def discover_devices(self) -> list[dict[str, str]]:
        """Discover devices from Nice HTTP controller.

        Returns:
            List of device dicts with 'id', 'name', 'module', 'adr', 'ept'
        """
        _LOGGER.debug("Starting device discovery")

        if not self._http_session:
            _LOGGER.debug("Initializing HTTP session")
            await self._ensure_initialized()

        base_url = self.http_config.get("base_url", "")
        # Use XML endpoint instead of HTML page - devices are loaded via AJAX
        url = f"{base_url.rstrip('/')}/cgi/devlst.xml"
        
        _LOGGER.debug("Base URL: %s", base_url)
        _LOGGER.debug("Device list XML URL: %s", url)

        auth = None
        username = self.http_config.get("username")
        password = self.http_config.get("password")
        if username and password:
            auth = aiohttp.BasicAuth(username, password)
            _LOGGER.debug("Using basic auth (username: %s)", username)
        else:
            _LOGGER.warning("No authentication configured")

        try:
            _LOGGER.debug("Fetching device list from %s", url)
            _LOGGER.debug("Using authentication: %s", "Yes" if auth else "No")
            
            async with self._http_session.get(url, auth=auth) as response:
                _LOGGER.debug("HTTP response received (status: %d)", response.status)
                _LOGGER.debug("Response headers: %s", dict(response.headers))
                
                # Check for authentication/redirect issues before processing
                if response.status == 401:
                    _LOGGER.error("Authentication failed (401 Unauthorized)")
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=401,
                        message="Authentication required"
                    )
                
                response.raise_for_status()
                xml_content = await response.text()
                _LOGGER.debug("Received %d bytes of XML", len(xml_content))
                _LOGGER.debug("XML preview: %s", xml_content[:500])
                
                # Log full XML for debugging
                _LOGGER.debug("Full XML content:\n%s", xml_content)
                
                # Check if we got a login/error page instead of XML
                xml_lower = xml_content.lower()
                if any(keyword in xml_lower for keyword in ['<!doctype html', '<html', 'login', 'password']):
                    _LOGGER.error("Received HTML/login page instead of XML. Check credentials.")
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=401,
                        message="Authentication failed - received HTML instead of XML"
                    )

                # Parse XML to extract device information
                try:
                    root = ET.fromstring(xml_content)
                except ET.ParseError as err:
                    _LOGGER.error("Failed to parse XML: %s", err)
                    raise

                devices = []

                # Find all device elements
                device_elements = root.findall('.//device')
                _LOGGER.debug("Found %d device elements in XML", len(device_elements))

                for idx, device_elem in enumerate(device_elements, 1):
                    # Get device attributes
                    installed = device_elem.get('installed', '0')
                    mac = device_elem.get('mac', '')
                    product_name = device_elem.get('productName', 'Unknown')
                    adr = device_elem.get('adr', '0')
                    ept = device_elem.get('ept', '0')
                    desc = device_elem.get('desc', product_name)
                    
                    _LOGGER.debug("Device %d: mac=%s, name=%s, adr=%s, ept=%s, installed=%s", 
                                idx, mac, desc, adr, ept, installed)
                    
                    # Only process installed devices
                    if installed != '1':
                        _LOGGER.debug("  → Skipping (not installed)")
                        continue
                    
                    # Convert hex to decimal for display in module name
                    adr_dec = int(adr, 16)
                    ept_dec = int(ept, 16)
                    
                    device = {
                        "id": f"{adr_dec},{ept}",  # Use decimal adr, hex ept
                        "name": desc if desc else product_name,
                        "module": f"{product_name} ({adr_dec},{ept_dec})",
                        "adr": str(adr_dec),  # Store as decimal string for command
                        "ept": ept.upper(),  # Store as hex for command
                    }
                    devices.append(device)
                    _LOGGER.info("  → Added device: %s (ID: %s)", device["name"], device["id"])

                _LOGGER.info("Device discovery complete: found %d installed devices", len(devices))
                return devices

        except aiohttp.ClientError as err:
            _LOGGER.error("HTTP error during device discovery: %s", err)
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error during device discovery: %s", err, exc_info=True)
            raise

    async def discover_groups(self) -> list[dict[str, Any]]:
        """Discover groups from Nice HTTP controller.

        Returns:
            List of group dicts with 'num', 'name', 'enabled'
        """
        _LOGGER.debug("Starting group discovery")

        if not self._http_session:
            _LOGGER.debug("Initializing HTTP session")
            await self._ensure_initialized()

        base_url = self.http_config.get("base_url", "")
        url = f"{base_url.rstrip('/')}/cgi/grplst.xml"
        
        _LOGGER.debug("Group list XML URL: %s", url)

        auth = None
        username = self.http_config.get("username")
        password = self.http_config.get("password")
        if username and password:
            auth = aiohttp.BasicAuth(username, password)

        try:
            _LOGGER.debug("Fetching group list from %s", url)
            
            async with self._http_session.get(url, auth=auth) as response:
                _LOGGER.debug("HTTP response received (status: %d)", response.status)
                response.raise_for_status()
                xml_content = await response.text()
                _LOGGER.debug("Received %d bytes of XML", len(xml_content))
                
                # Parse XML
                try:
                    root = ET.fromstring(xml_content)
                except ET.ParseError as err:
                    _LOGGER.error("Failed to parse group XML: %s", err)
                    raise

                groups = []

                # Find all group elements
                group_elements = root.findall('.//group')
                _LOGGER.debug("Found %d group elements in XML", len(group_elements))

                for idx, group_elem in enumerate(group_elements, 1):
                    num = group_elem.get('num', '0')
                    enabled = group_elem.get('enabled', '0')
                    desc = group_elem.get('desc', f'Group {num}')
                    
                    _LOGGER.debug("Group %d: num=%s, desc=%s, enabled=%s", 
                                idx, num, desc, enabled)
                    
                    # Only process enabled groups
                    if enabled != '1':
                        _LOGGER.debug("  → Skipping (not enabled)")
                        continue
                    
                    group = {
                        "num": num,
                        "name": desc,
                        "enabled": enabled,
                    }
                    groups.append(group)
                    _LOGGER.info("  → Added group: %s (num: %s)", group["name"], group["num"])

                _LOGGER.info("Group discovery complete: found %d enabled groups", len(groups))
                return groups

        except aiohttp.ClientError as err:
            _LOGGER.error("HTTP error during group discovery: %s", err)
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error during group discovery: %s", err, exc_info=True)
            raise

    async def send_group_command(self, group_num: str, command: str) -> None:
        """Send a command to a group via HTTP.

        Args:
            group_num: Group number (e.g., "1", "2")
            command: Command to send (open, close, stop)
        """
        await self._ensure_initialized()

        _LOGGER.info("Sending group command: %s to group: %s", command, group_num)

        if not self._http_session:
            _LOGGER.error("HTTP session not initialized")
            return

        try:
            # Map commands to Nice protocol data codes
            cmd_data = {
                "stop": "02000000",
                "open": "03000000",
                "close": "04000000",
            }

            dat = cmd_data.get(command)
            if not dat:
                _LOGGER.error("Unknown command: %s", command)
                return

            # Build URL: /cgi/grpcmd.xml?req=R&num=1&dat=03000000
            base_url = self.http_config.get("base_url", "")
            url = f"{base_url.rstrip('/')}/cgi/grpcmd.xml?req=R&num={group_num}&dat={dat}"

            # Prepare authentication
            auth = None
            username = self.http_config.get("username")
            password = self.http_config.get("password")
            if username and password:
                auth = aiohttp.BasicAuth(username, password)

            _LOGGER.debug("Sending HTTP group request to: %s", url)
            async with self._http_session.get(url, auth=auth) as response:
                response.raise_for_status()
                xml_content = await response.text()
                
                # Parse response to check result
                try:
                    root = ET.fromstring(xml_content)
                    result = root.findtext('.//result', '0')
                    if result == '0':
                        _LOGGER.info(
                            "Group command '%s' sent successfully to group %s",
                            command, group_num
                        )
                    else:
                        _LOGGER.warning(
                            "Group command returned result: %s", result
                        )
                except ET.ParseError:
                    _LOGGER.warning("Could not parse group command response")

        except aiohttp.ClientError as err:
            _LOGGER.error("HTTP request failed for group command '%s': %s", command, err)
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error sending group command '%s': %s", command, err)
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
