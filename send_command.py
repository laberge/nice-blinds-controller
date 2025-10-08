#!/usr/bin/env python3
"""Standalone script to send commands to Nice blinds - no HA dependencies required."""

import asyncio
import aiohttp
import sys
import xml.etree.ElementTree as ET


async def send_command(base_url: str, username: str, password: str, device_id: str, command: str):
    """Send a command to a Nice blind."""
    
    # Parse device ID (format: "adr,ept" e.g., "1,01")
    parts = device_id.split(",")
    if len(parts) != 2:
        print(f"Error: Invalid device_id format. Expected 'adr,ept', got: {device_id}")
        return False
    
    adr = parts[0]
    ept = parts[1]
    
    # Map commands to Nice protocol codes
    cmd_codes = {
        "stop": "02",
        "open": "03",
        "close": "04",
    }
    
    cmd = cmd_codes.get(command.lower())
    if not cmd:
        print(f"Error: Unknown command '{command}'. Use: open, close, or stop")
        return False
    
    # Build URL
    url = f"{base_url.rstrip('/')}/cgi/devcmd.xml?adr={adr}&ept={ept}&cmd={cmd}"
    
    # Send command
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        auth = aiohttp.BasicAuth(username, password) if username and password else None
        
        try:
            print(f"\n{'='*60}")
            print(f"Sending Command to Nice Blind")
            print(f"{'='*60}")
            print(f"Device ID: {device_id} (adr={adr}, ept={ept})")
            print(f"Command: {command} (code={cmd})")
            print(f"URL: {url}")
            print(f"-" * 60)
            
            async with session.get(url, auth=auth) as response:
                response.raise_for_status()
                xml_response = await response.text()
                
                print(f"✓ Command sent successfully!")
                print(f"Status: {response.status}")
                print(f"Response: {xml_response[:200] if len(xml_response) > 200 else xml_response}")
                print(f"{'='*60}\n")
                return True
                
        except aiohttp.ClientError as e:
            print(f"✗ HTTP Error: {e}")
            return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False


async def list_devices(base_url: str, username: str, password: str):
    """List all available devices."""
    
    url = f"{base_url.rstrip('/')}/cgi/devlst.xml"
    
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        auth = aiohttp.BasicAuth(username, password) if username and password else None
        
        try:
            async with session.get(url, auth=auth) as response:
                response.raise_for_status()
                xml_content = await response.text()
                
                # Parse XML
                root = ET.fromstring(xml_content)
                device_elements = root.findall('.//device')
                
                print(f"\n{'='*60}")
                print(f"Available Devices")
                print(f"{'='*60}\n")
                
                devices = []
                for device_elem in device_elements:
                    installed = device_elem.get('installed', '0')
                    if installed != '1':
                        continue
                    
                    product_name = device_elem.get('productName', 'Unknown')
                    adr = device_elem.get('adr', '0')
                    ept = device_elem.get('ept', '0')
                    desc = device_elem.get('desc', product_name)
                    
                    adr_dec = int(adr, 16)
                    ept_dec = int(ept, 16)
                    
                    device_id = f"{adr_dec},{ept}"
                    devices.append({
                        'name': desc,
                        'id': device_id,
                        'module': f"{product_name} ({adr_dec},{ept_dec})"
                    })
                
                for i, device in enumerate(devices, 1):
                    print(f"{i:2}. {device['name']:15} (ID: {device['id']:6}) - {device['module']}")
                
                print(f"\n{'='*60}")
                print(f"Total: {len(devices)} devices")
                print(f"{'='*60}\n")
                
                return devices
                
        except Exception as e:
            print(f"✗ Error: {e}")
            return []


def print_usage():
    """Print usage instructions."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║          Nice Blinds Command Tool - Standalone               ║
╚══════════════════════════════════════════════════════════════╝

Usage:
  List all devices:
    python3 send_command.py <base_url> <username> <password> list

  Send a command:
    python3 send_command.py <base_url> <username> <password> <device_id> <command>

Examples:
  # List all devices
  python3 send_command.py http://192.168.10.235 aaron mypassword list

  # Open MBA 3 (device_id: 1,01)
  python3 send_command.py http://192.168.10.235 aaron mypassword 1,01 open

  # Close Kitchen 1 (device_id: 1,0B)
  python3 send_command.py http://192.168.10.235 aaron mypassword 1,0B close

  # Stop Office 1 (device_id: 1,0E)
  python3 send_command.py http://192.168.10.235 aaron mypassword 1,0E stop

Available Commands:
  - open   : Opens the blind (moves up)
  - close  : Closes the blind (moves down)
  - stop   : Stops the blind movement

Your Device IDs:
  MBA 3       -> 1,01    |  Sunroom 2   -> 1,0A    |  Office 5    -> 1,11
  MBR 1       -> 1,02    |  Kitchen 1   -> 1,0B    |  Office 6    -> 1,12
  MBR 2       -> 1,03    |  Kitchen 2   -> 1,0C    |  Office 7    -> 1,13
  MBR 4       -> 1,04    |  Office 2    -> 1,0D    |  Office 8    -> 1,14
  Sunroom 1   -> 1,05    |  Office 1    -> 1,0E    |  Office 9    -> 1,15
  MBA 1       -> 1,06    |  Office 3    -> 1,0F    |  Office 10   -> 1,16
  Sunroom 3   -> 1,07    |  Office 4    -> 1,10    |  Office 11   -> 1,17
  Sunroom 4   -> 1,08    |                          |  Office 12   -> 1,18
  Sunroom 5   -> 1,09    |                          |  Living Room -> 1,19
""")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print_usage()
        sys.exit(1)
    
    base_url = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    if len(sys.argv) == 5 and sys.argv[4].lower() == "list":
        # List devices
        asyncio.run(list_devices(base_url, username, password))
    elif len(sys.argv) == 6:
        # Send command
        device_id = sys.argv[4]
        command = sys.argv[5].lower()
        
        success = asyncio.run(send_command(base_url, username, password, device_id, command))
        sys.exit(0 if success else 1)
    else:
        print_usage()
        sys.exit(1)

