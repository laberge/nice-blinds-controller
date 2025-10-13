#!/usr/bin/env python3
"""Verify that all devices in groups can be found on the controller."""

import asyncio
import aiohttp
import os
import xml.etree.ElementTree as ET
import yaml

CONTROLLER_URL = os.getenv("BLINDS_URL", "http://192.168.10.235")
USERNAME = os.getenv("BLINDS_USER", "aaron")
PASSWORD = os.getenv("BLINDS_PASS", "")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GROUPS_FILE = os.path.join(SCRIPT_DIR, "blinds_groups.yaml")


async def get_controller_devices():
    """Get all devices from the controller."""
    url = f"{CONTROLLER_URL.rstrip('/')}/cgi/devlst.xml"
    
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        auth = aiohttp.BasicAuth(USERNAME, PASSWORD) if USERNAME and PASSWORD else None
        
        async with session.get(url, auth=auth) as response:
            response.raise_for_status()
            xml_content = await response.text()
            
            root = ET.fromstring(xml_content)
            device_elements = root.findall('.//device')
            
            devices = {}
            for device_elem in device_elements:
                installed = device_elem.get('installed', '0')
                if installed != '1':
                    continue
                
                adr = device_elem.get('adr', '0')
                ept = device_elem.get('ept', '0')
                desc = device_elem.get('desc', '')
                
                adr_dec = int(adr, 16)
                ept_upper = ept.upper()
                device_id = f"{adr_dec},{ept_upper}"
                
                # Store both normalized key and original name
                devices[desc.lower().strip()] = {
                    'name': desc.strip(),
                    'id': device_id,
                    'adr': adr,
                    'ept': ept_upper
                }
            
            return devices


async def verify_groups():
    """Verify all groups and their devices."""
    
    print("\n" + "="*70)
    print("VERIFYING GROUPS CONFIGURATION")
    print("="*70)
    
    # Get devices from controller
    print("\nFetching devices from controller...")
    controller_devices = await get_controller_devices()
    print(f"✓ Found {len(controller_devices)} devices on controller")
    
    # Load groups
    print("\nLoading groups configuration...")
    with open(GROUPS_FILE, 'r') as f:
        config = yaml.safe_load(f)
        groups = config.get('groups', {})
    print(f"✓ Loaded {len(groups)} groups")
    
    # Verify each group
    print("\n" + "="*70)
    print("GROUP VERIFICATION")
    print("="*70)
    
    total_devices_in_groups = 0
    total_found = 0
    total_missing = 0
    
    for group_id, group_info in groups.items():
        group_name = group_info.get('name', group_id)
        device_names = group_info.get('devices', [])
        
        print(f"\n📁 {group_name} ({len(device_names)} devices)")
        print("-" * 70)
        
        found_devices = []
        missing_devices = []
        
        for dev_name in device_names:
            total_devices_in_groups += 1
            normalized_name = dev_name.lower().strip()
            
            if normalized_name in controller_devices:
                dev_info = controller_devices[normalized_name]
                found_devices.append(dev_name)
                total_found += 1
                print(f"  ✓ {dev_name:<20} → ID: {dev_info['id']:<8} (adr={dev_info['adr']}, ept={dev_info['ept']})")
            else:
                missing_devices.append(dev_name)
                total_missing += 1
                print(f"  ✗ {dev_name:<20} → NOT FOUND ON CONTROLLER")
                
                # Try to find similar names
                similar = []
                for ctrl_key, ctrl_dev in controller_devices.items():
                    if dev_name.lower().replace(' ', '') in ctrl_key.replace(' ', ''):
                        similar.append(ctrl_dev['name'])
                
                if similar:
                    print(f"     Similar devices: {', '.join(similar)}")
        
        # Summary for this group
        if missing_devices:
            print(f"\n  ⚠️  WARNING: {len(missing_devices)} devices not found!")
        else:
            print(f"\n  ✓ All devices found and verified")
    
    # Final summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total devices in groups: {total_devices_in_groups}")
    print(f"  ✓ Found:   {total_found}")
    print(f"  ✗ Missing: {total_missing}")
    
    if total_missing == 0:
        print("\n✓ SUCCESS: All group devices verified!")
    else:
        print(f"\n⚠️  WARNING: {total_missing} devices could not be found on controller")
        print("\nPossible solutions:")
        print("  1. Check device names in blinds_groups.yaml for typos")
        print("  2. Ensure devices are installed and powered on")
        print("  3. Run './blinds list' to see actual device names")
    
    print("="*70 + "\n")
    
    return total_missing == 0


if __name__ == "__main__":
    if not PASSWORD:
        print("✗ Error: Password not configured")
        print("Set BLINDS_PASS environment variable")
        exit(1)
    
    try:
        success = asyncio.run(verify_groups())
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        exit(1)

