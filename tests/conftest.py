"""Shared fixtures for the Nice Blinds Controller tests."""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"

BASE_URL = "http://controller.test"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of the custom integration in every test."""
    yield


@pytest.fixture
def http_config():
    """HTTP config for a NiceController."""
    return {
        "base_url": BASE_URL,
        "username": "user",
        "password": "pass",
        "timeout": 10,
    }


@pytest.fixture
def device_list_xml():
    """A device list with installed and not-installed devices (adr is hex)."""
    return """<?xml version="1.0"?>
<devlst>
  <device installed="1" mac="AA:01" productName="Era Mat MA" adr="01" ept="01" desc="MBA 3" sta="05" pos="0" inp="0"/>
  <device installed="1" mac="AA:0F" productName="Era Mat MA" adr="01" ept="0F" desc="Office 3" sta="04" pos="100" inp="0"/>
  <device installed="0" mac="AA:20" productName="Era Mat MA" adr="01" ept="20" desc="Spare" sta="00" pos="255" inp="0"/>
  <device installed="1" mac="AA:05" productName="Era Mat MA" adr="0A" ept="05" desc="Sunroom 1" sta="02" pos="255" inp="0"/>
</devlst>"""


@pytest.fixture
def group_list_xml():
    """A group list with enabled and disabled groups."""
    return """<?xml version="1.0"?>
<grplst>
  <group num="1" enabled="1" desc="Office"/>
  <group num="2" enabled="0" desc="Disabled"/>
  <group num="3" enabled="1" desc="Sunroom"/>
</grplst>"""


@pytest.fixture
def empty_device_list_xml():
    """A device list with no installed devices."""
    return """<?xml version="1.0"?>
<devlst>
  <device installed="0" productName="Era Mat MA" adr="01" ept="01" desc="Spare" sta="00" pos="255"/>
</devlst>"""
