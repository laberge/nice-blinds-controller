#!/usr/bin/env python3
"""Diagnostic script to test Nice controller connection and device discovery."""

import asyncio
import aiohttp
import sys


async def test_controller(base_url: str, username: str, password: str):
    """Test controller connection and show what's happening."""
    
    print(f"\n{'='*60}")
    print(f"Testing Nice Controller Connection")
    print(f"{'='*60}\n")
    
    # Test 1: Basic connectivity
    print(f"Test 1: Basic connectivity to {base_url}")
    print(f"-" * 60)
    
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(base_url) as response:
                print(f"✓ Base URL reachable")
                print(f"  Status: {response.status}")
                print(f"  Headers: {dict(response.headers)}")
                html = await response.text()
                print(f"  Response size: {len(html)} bytes")
                print(f"  Preview: {html[:200]}")
        except Exception as e:
            print(f"✗ Failed to connect to base URL: {e}")
            return
        
        # Test 2: Device list endpoint WITHOUT auth
        print(f"\n\nTest 2: Device list endpoint (NO AUTH)")
        print(f"-" * 60)
        dev_list_url = f"{base_url.rstrip('/')}/dev_list.htm"
        print(f"URL: {dev_list_url}")
        
        try:
            async with session.get(dev_list_url) as response:
                print(f"  Status: {response.status}")
                html = await response.text()
                print(f"  Response size: {len(html)} bytes")
                print(f"  Content preview (first 500 chars):")
                print(f"  {'-'*58}")
                print(f"  {html[:500]}")
                print(f"  {'-'*58}")
                
                # Check for auth-related keywords
                html_lower = html.lower()
                auth_keywords = ['login', 'password', 'authentication', 'unauthorized', 'access denied']
                found_keywords = [kw for kw in auth_keywords if kw in html_lower]
                if found_keywords:
                    print(f"  ⚠ Auth keywords found: {', '.join(found_keywords)}")
                    print(f"  This suggests authentication is required")
                
        except Exception as e:
            print(f"  Error: {e}")
        
        # Test 3: Device list endpoint WITH auth
        print(f"\n\nTest 3: Device list endpoint (WITH AUTH)")
        print(f"-" * 60)
        print(f"URL: {dev_list_url}")
        print(f"Username: {username}")
        print(f"Password: {'*' * len(password)}")
        
        auth = aiohttp.BasicAuth(username, password)
        
        try:
            async with session.get(dev_list_url, auth=auth) as response:
                print(f"  Status: {response.status}")
                print(f"  Headers: {dict(response.headers)}")
                html = await response.text()
                print(f"  Response size: {len(html)} bytes")
                print(f"\n  Full HTML content:")
                print(f"  {'-'*58}")
                print(html)
                print(f"  {'-'*58}")
                
                # Try to find table rows
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                print(f"\n  HTML Analysis:")
                print(f"  - Tables found: {len(soup.find_all('table'))}")
                print(f"  - Rows found: {len(soup.find_all('tr'))}")
                
                for i, row in enumerate(soup.find_all('tr')):
                    cells = row.find_all('td')
                    if cells:
                        print(f"    Row {i}: {len(cells)} cells")
                        for j, cell in enumerate(cells):
                            text = cell.get_text(strip=True)
                            if text:
                                print(f"      Cell {j}: '{text}'")
                
        except aiohttp.ClientResponseError as e:
            print(f"  HTTP Error: {e.status} - {e.message}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Test 4: XML Device List (THE CORRECT ENDPOINT)
        print(f"\n\nTest 4: XML Device List endpoint (CORRECT ENDPOINT)")
        print(f"-" * 60)
        xml_url = f"{base_url.rstrip('/')}/cgi/devlst.xml"
        print(f"URL: {xml_url}")
        
        try:
            async with session.get(xml_url, auth=auth) as response:
                print(f"  Status: {response.status}")
                xml_content = await response.text()
                print(f"  Response size: {len(xml_content)} bytes")
                print(f"\n  Full XML content:")
                print(f"  {'-'*58}")
                print(xml_content)
                print(f"  {'-'*58}")
                
                # Parse XML to show devices
                from xml.etree import ElementTree as ET
                try:
                    root = ET.fromstring(xml_content)
                    device_elements = root.findall('.//device')
                    
                    print(f"\n  XML Analysis:")
                    print(f"  - Total devices in XML: {len(device_elements)}")
                    
                    installed_count = 0
                    for i, device in enumerate(device_elements):
                        installed = device.get('installed', '0')
                        if installed == '1':
                            installed_count += 1
                            product_name = device.get('productName', 'Unknown')
                            adr = device.get('adr', '0')
                            ept = device.get('ept', '0')
                            desc = device.get('desc', '')
                            
                            adr_dec = int(adr, 16)
                            ept_dec = int(ept, 16)
                            
                            print(f"\n  Device {installed_count}:")
                            print(f"    Name: {desc if desc else product_name}")
                            print(f"    Module: {product_name}")
                            print(f"    Address: {adr_dec} (0x{adr})")
                            print(f"    Endpoint: {ept_dec} (0x{ept})")
                            print(f"    ID for commands: adr={adr_dec}, ept={ept}")
                    
                    if installed_count == 0:
                        print(f"  ⚠ No installed devices found")
                        print(f"  Total devices in XML: {len(device_elements)}")
                        print(f"  They might not be marked as installed='1'")
                    else:
                        print(f"\n  ✓ Found {installed_count} installed devices!")
                        
                except ET.ParseError as e:
                    print(f"  ✗ XML Parse Error: {e}")
                    
        except Exception as e:
            print(f"  Error: {e}")
        
        # Test 5: Try different endpoints
        print(f"\n\nTest 5: Trying alternative endpoints")
        print(f"-" * 60)
        
        endpoints = [
            '/devices.htm',
            '/device.htm', 
            '/devlist.htm',
            '/status.htm',
            '/index.htm',
            '/cgi-bin/devices',
        ]
        
        for endpoint in endpoints:
            url = f"{base_url.rstrip('/')}{endpoint}"
            try:
                async with session.get(url, auth=auth) as response:
                    if response.status == 200:
                        html = await response.text()
                        print(f"  ✓ {endpoint} - Status: {response.status} ({len(html)} bytes)")
                    else:
                        print(f"    {endpoint} - Status: {response.status}")
            except:
                print(f"    {endpoint} - Not found/Error")

    print(f"\n{'='*60}")
    print(f"Test Complete")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python test_controller.py <base_url> <username> <password>")
        print("Example: python test_controller.py http://192.168.1.100 admin mypassword")
        sys.exit(1)
    
    base_url = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    asyncio.run(test_controller(base_url, username, password))

