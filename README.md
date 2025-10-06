# Nice Blinds Controller - Home Assistant Custom Integration

A Home Assistant custom integration for controlling blinds using the Nice protocol. Supports both RF 433MHz and BiDi-Bus communication methods.

## Features

- **Nice Protocol Support**: RF 433MHz and BiDi-Bus protocols
- **Full Control**: Open, close, stop, and position control (0-100%)
- **UI Configuration**: Easy setup through Home Assistant interface
- **Raspberry Pi Compatible**: Uses GPIO pins for RF transmission
- **Position Tracking**: Automatic position estimation based on movement time

## Requirements

### Hardware
- **Raspberry Pi** (or compatible device) running Home Assistant
- **RF 433MHz Transmitter** (for RF protocol) - connected to GPIO pin
  - Recommended: FS1000A or similar 433MHz transmitter module
- **Nice-compatible blinds motor** (Nice Era, Nice Inti, or similar)

### Software
- Home Assistant (tested on 2024.1+)
- Python 3.11+
- `rpi-rf` library (automatically installed)

## Installation

### HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Open HACS in your Home Assistant instance
3. Go to "Integrations"
4. Click the three dots in the top right and select "Custom repositories"
5. Add this repository URL: `https://github.com/laberge/nice-blinds-controller`
6. Select "Integration" as the category
7. Click "Install"
8. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/blinds_control` directory to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Hardware Setup

### RF 433MHz Transmitter Wiring

Connect your RF transmitter to the Raspberry Pi:
- **VCC** → 5V (Pin 2)
- **GND** → Ground (Pin 6)
- **DATA** → GPIO 17 (Pin 11) - or your chosen GPIO pin

```
RF Transmitter        Raspberry Pi
    VCC  ----------→  5V (Pin 2)
    GND  ----------→  GND (Pin 6)
    DATA ----------→  GPIO 17 (Pin 11)
```

## Configuration

### Initial Setup

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Nice Blinds Controller"
4. Configure the following:
   - **Blind Name**: Friendly name for your blinds (e.g., "Living Room Blinds")
   - **Protocol Type**:
     - `rf433` - For RF 433MHz control
     - `bidi_bus` - For BiDi-Bus (experimental)
   - **Device ID**: RF code for your blind (optional, can configure later)
   - **GPIO Pin**: GPIO pin number for RF transmitter (default: 17)
   - **Move Time**: Time in seconds for full open/close (default: 30)

### Learning RF Codes

To capture RF codes from your existing Nice remote:

1. Install an RF receiver module (like RXB6) on your Raspberry Pi
2. Use `rpi-rf_receive` tool to capture codes:
   ```bash
   rpi-rf_receive -g 27
   ```
3. Press buttons on your Nice remote and note the codes
4. Update the codes in `nice_protocol.py`:
   ```python
   command_codes = {
       "open": 1234567,    # Your captured code
       "close": 7654321,   # Your captured code
       "stop": 1111111,    # Your captured code
   }
   ```

## Advanced Configuration

### Customizing RF Codes

Edit `custom_components/blinds_control/nice_protocol.py` and update the `command_codes` dictionary:

```python
command_codes = {
    "open": 1234567,    # Replace with your captured code
    "close": 7654321,   # Replace with your captured code
    "stop": 1111111,    # Replace with your captured code
}
```

### Multiple Blinds

To control multiple blinds, add the integration multiple times with different:
- Names
- Device IDs (RF codes)
- GPIO pins (if using multiple transmitters)

### BiDi-Bus Protocol (Experimental)

The BiDi-Bus protocol support is experimental and requires additional implementation in `nice_protocol.py`. This is suitable for Nice systems with Bus-T4 connectors and BiDi-WiFi modules.

### Adjusting Movement Time

If position tracking is inaccurate:
1. Measure the actual time for full open/close
2. Update the **Move Time** setting during configuration
3. Or modify `_move_time` in the entity settings

## Usage

Once configured, your blinds will appear as a cover entity in Home Assistant. You can:

- **Lovelace UI**: Control from the dashboard with open/close/stop buttons and position slider
- **Automations**: Trigger based on time, sun position, or other events
- **Voice Control**: Use with Alexa, Google Home, or Siri
- **Scenes & Scripts**: Include in complex automation scenarios

### Example Automations

#### Open blinds at sunrise
```yaml
automation:
  - alias: "Open blinds at sunrise"
    trigger:
      platform: sun
      event: sunrise
      offset: "00:15:00"  # 15 minutes after sunrise
    action:
      service: cover.open_cover
      target:
        entity_id: cover.living_room_blinds
```

#### Close blinds when it gets hot
```yaml
automation:
  - alias: "Close blinds when hot"
    trigger:
      platform: numeric_state
      entity_id: sensor.outdoor_temperature
      above: 28
    action:
      service: cover.close_cover
      target:
        entity_id: cover.living_room_blinds
```

#### Set blinds to 50% at sunset
```yaml
automation:
  - alias: "Partial close at sunset"
    trigger:
      platform: sun
      event: sunset
    action:
      service: cover.set_cover_position
      target:
        entity_id: cover.living_room_blinds
      data:
        position: 50
```

## Troubleshooting

### Blinds not responding
- Check RF transmitter wiring
- Verify GPIO pin configuration
- Ensure RF codes are correctly captured
- Check Home Assistant logs for errors

### Position tracking is off
- Adjust the `move_time` parameter to match your blinds' actual movement time
- Test with full open/close cycles

### Permission denied on GPIO
- Ensure Home Assistant has permission to access GPIO pins
- Add the user to the `gpio` group: `sudo usermod -a -G gpio homeassistant`

## Nice Protocol Information

The Nice protocol is proprietary and varies by device type:
- **RF 433MHz**: Common for older Nice motors (Era, Inti series)
- **BiDi-Bus**: Used in newer systems with bidirectional communication
- **Frequency**: Typically 433.92 MHz for RF variants

This integration currently focuses on RF transmission. For BiDi-Bus, additional protocol implementation is needed.

## Support

For issues and feature requests, please visit the [GitHub Issues](https://github.com/laberge/nice-blinds-controller/issues) page.

## Contributing

Contributions are welcome! Especially:
- BiDi-Bus protocol implementation
- Additional Nice protocol variants
- Code improvements and bug fixes

## License

This project is open source. Feel free to modify and distribute as needed.

## Disclaimer

This is an unofficial integration. Nice is a trademark of Nice S.p.A. This project is not affiliated with or endorsed by Nice S.p.A.
