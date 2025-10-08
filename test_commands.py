#!/usr/bin/env python3
"""Test script to send commands to Nice blinds."""

import asyncio
import sys
from custom_components.blinds_control.nice_protocol import NiceController


async def send_test_command(base_url: str, username: str, password: str, device_id: str, command: str):
    """Send a command to a specific device."""
    
    http_config = {
        "base_url": base_url,
        "username": username,
        "password": password,
        "timeout": 10,
    }
    
    controller = NiceController(http_config=http_config)
    
    try:
        print(f"\n{'='*60}")
        print(f"Sending Command to Nice Blind")
        print(f"{'='*60}")
        print(f"Device ID: {device_id}")
        print(f"Command: {command}")
        print(f"Base URL: {base_url}")
        print(f"-" * 60)
        
        await controller.send_command(device_id, command)
        
        print(f"✓ Command sent successfully!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        await controller.cleanup()


async def list_devices(base_url: str, username: str, password: str):
    """List all available devices."""
    
    http_config = {
        "base_url": base_url,
        "username": username,
        "password": password,
        "timeout": 10,
    }
    
    controller = NiceController(http_config=http_config)
    
    try:
        print(f"\n{'='*60}")
        print(f"Available Devices")
        print(f"{'='*60}\n")
        
        devices = await controller.discover_devices()
        
        for i, device in enumerate(devices, 1):
            print(f"{i}. {device['name']}")
            print(f"   ID: {device['id']}")
            print(f"   Module: {device['module']}")
            print(f"   Commands: python3 test_commands.py {base_url} {username} <password> {device['id']} <open|close|stop>")
            print()
        
        print(f"Total: {len(devices)} devices")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        await controller.cleanup()


def print_usage():
    """Print usage instructions."""
    print("""
Usage:
  List all devices:
    python3 test_commands.py <base_url> <username> <password> list

  Send a command:
    python3 test_commands.py <base_url> <username> <password> <device_id> <command>

Examples:
  # List all devices
  python3 test_commands.py http://192.168.10.235 aaron mypassword list

  # Open MBA 3 (device_id: 1,01)
  python3 test_commands.py http://192.168.10.235 aaron mypassword 1,01 open

  # Close Kitchen 1 (device_id: 1,0B)
  python3 test_commands.py http://192.168.10.235 aaron mypassword 1,0B close

  # Stop Office 1 (device_id: 1,0E)
  python3 test_commands.py http://192.168.10.235 aaron mypassword 1,0E stop

Available Commands:
  - open   : Opens the blind
  - close  : Closes the blind
  - stop   : Stops the blind movement

Device IDs from your system:
  MBA 3       -> 1,01
  MBR 1       -> 1,02
  MBR 2       -> 1,03
  MBR 4       -> 1,04
  Sunroom 1   -> 1,05
  MBA 1       -> 1,06
  Sunroom 3   -> 1,07
  Sunroom 4   -> 1,08
  Sunroom 5   -> 1,09
  Sunroom 2   -> 1,0A
  Kitchen 1   -> 1,0B
  Kitchen 2   -> 1,0C
  Office 2    -> 1,0D
  Office 1    -> 1,0E
  Office 3    -> 1,0F
  Office 4    -> 1,10
  Office 5    -> 1,11
  Office 6    -> 1,12
  Office 7    -> 1,13
  Office 8    -> 1,14
  Office 9    -> 1,15
  Office 10   -> 1,16
  Office 11   -> 1,17
  Office 12   -> 1,18
  Living Room -> 1,19
""")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print_usage()
        sys.exit(1)
    
    base_url = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    if len(sys.argv) == 5 and sys.argv[4] == "list":
        # List devices
        asyncio.run(list_devices(base_url, username, password))
    elif len(sys.argv) == 6:
        # Send command
        device_id = sys.argv[4]
        command = sys.argv[5].lower()
        
        if command not in ["open", "close", "stop"]:
            print(f"Error: Invalid command '{command}'. Must be: open, close, or stop")
            sys.exit(1)
        
        asyncio.run(send_test_command(base_url, username, password, device_id, command))
    else:
        print_usage()
        sys.exit(1)

