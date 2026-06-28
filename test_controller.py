#!/usr/bin/env python3
"""Diagnostic script to test Nice controller connection and device discovery."""

import asyncio
import aiohttp
import sys
import xml.etree.ElementTree as ET


async def test_controller(base_url: str, username: str, password: str):
    """Test controller connectivity and parse the XML device list."""

    print(f"\n{'='*60}")
    print(f"Testing Nice Controller Connection")
    print(f"{'='*60}\n")

    timeout = aiohttp.ClientTimeout(total=10)
    auth = aiohttp.BasicAuth(username, password) if username and password else None

    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Test 1: Basic connectivity
        print(f"Test 1: Basic connectivity to {base_url}")
        print(f"-" * 60)
        try:
            async with session.get(base_url, auth=auth) as response:
                print(f"✓ Base URL reachable (status: {response.status})")
        except Exception as e:
            print(f"✗ Failed to connect to base URL: {e}")
            return

        # Test 2: XML device list (the endpoint the integration uses)
        print(f"\nTest 2: XML device list endpoint")
        print(f"-" * 60)
        xml_url = f"{base_url.rstrip('/')}/cgi/devlst.xml"
        print(f"URL: {xml_url}")

        try:
            async with session.get(xml_url, auth=auth) as response:
                print(f"  Status: {response.status}")
                xml_content = await response.text()
                print(f"  Response size: {len(xml_content)} bytes")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            print(f"  ✗ XML Parse Error: {e}")
            print(f"  (A login/HTML page here usually means bad credentials.)")
            return

        device_elements = root.findall(".//device")
        print(f"\n  Total devices in XML: {len(device_elements)}")

        installed_count = 0
        for device in device_elements:
            if device.get("installed", "0") != "1":
                continue
            installed_count += 1
            product_name = device.get("productName", "Unknown")
            adr = device.get("adr", "0")
            ept = device.get("ept", "0")
            desc = device.get("desc", "")

            adr_dec = int(adr, 16)
            ept_dec = int(ept, 16)

            print(f"\n  Device {installed_count}:")
            print(f"    Name: {desc if desc else product_name}")
            print(f"    Module: {product_name}")
            print(f"    Address: {adr_dec} (0x{adr})")
            print(f"    Endpoint: {ept_dec} (0x{ept})")
            print(f"    ID for commands: adr={adr_dec}, ept={ept.upper()}")

        if installed_count == 0:
            print(f"\n  ⚠ No installed devices found (none marked installed='1').")
        else:
            print(f"\n  ✓ Found {installed_count} installed devices!")

    print(f"\n{'='*60}")
    print(f"Test Complete")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python test_controller.py <base_url> <username> <password>")
        print("Example: python test_controller.py http://192.168.1.100 admin mypassword")
        sys.exit(1)

    asyncio.run(test_controller(sys.argv[1], sys.argv[2], sys.argv[3]))
