# Nice Blinds Controller - Home Assistant Custom Integration

A Home Assistant custom integration for controlling Nice blinds and motors. Supports HTTP/network controllers, RF 433MHz, and BiDi-Bus communication methods.

## Features

- **HTTP Controller Support**: Connect to Nice network/HTTP controllers with automatic device discovery
- **Multiple Protocol Support**: HTTP, RF 433MHz, and BiDi-Bus protocols
- **Automatic Device Discovery**: Finds all devices from your Nice controller
- **Full Control**: Open, close, stop, and position control (0-100%)
- **UI Configuration**: Easy setup through Home Assistant interface
- **Position Tracking**: Automatic position estimation based on movement time
- **CLI Tools**: Standalone command-line interface for direct control (see [CLI Tools](#cli-tools-standalone) below)

## CLI Tools (Standalone)

Control your blinds directly from the command line without Home Assistant!

```bash
# Simple, friendly device names
blinds open "MBA 3"
blinds close "Kitchen 1"
blinds stop "Office 1"
blinds list
```

**Quick Setup:**
```bash
./setup_blinds_cli.sh
```

**Features:**
- Control blinds using friendly device names
- Dotfiles integration support
- Batch operations for multiple blinds
- Secure password management (environment variables, keychain, password managers)

**Documentation:**
- [Quick Start Guide](QUICK_START.md) - Get started in 30 seconds
- [CLI Documentation](BLINDS_CLI_README.md) - Detailed usage and examples
- [Dotfiles Setup](DOTFILES_SETUP.md) - Integration with your dotfiles workflow

## Requirements

### For HTTP Controllers (Recommended)
- Home Assistant (tested on 2024.1+)
- Nice HTTP/network controller (e.g., IT4WiFi, MyNice, or compatible)
- Network access to your Nice controller

### For RF 433MHz (Alternative)
- Raspberry Pi (or compatible device) running Home Assistant
- RF 433MHz Transmitter connected to GPIO pin
- Nice-compatible blinds motor (Nice Era, Nice Inti, or similar)

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

## Configuration

### Method 1: HTTP Controller (Recommended)

This method works with Nice network controllers that provide an HTTP interface for device control.

#### Setup Steps

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Nice Blinds Controller"
4. Select **HTTP** as the protocol type
5. Enter your controller details:
   - **Base URL**: Your controller's IP address (e.g., `http://192.168.1.100`)
   - **Username**: Controller username (default: `admin`)
   - **Password**: Controller password
   - **Timeout**: Request timeout in seconds (default: 10)
6. Click **Submit**
7. The integration will automatically discover all connected devices
8. **Select devices** you want to add to Home Assistant
9. Click **Submit** to complete setup

#### Supported Controllers

This integration works with Nice controllers that use the following API format:
```
http://controller-ip/cgi/devcmd.xml?adr=1&ept=0F&cmd=03
```

Command codes:
- `cmd=02` - Stop
- `cmd=03` - Open/Up
- `cmd=04` - Close/Down

Compatible with:
- Nice IT4WiFi
- Nice MyNice controllers
- Other Nice network controllers with HTTP API

### Method 2: RF 433MHz (Advanced)

This method requires a Raspberry Pi with an RF transmitter module.

#### Hardware Setup

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

#### Configuration Steps

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Nice Blinds Controller"
4. Select **RF433** as the protocol type
5. Configure:
   - **Blind Name**: Friendly name for your blinds
   - **Device ID**: RF code for your blind (optional)
   - **GPIO Pin**: GPIO pin number for RF transmitter (default: 17)
   - **Move Time**: Time in seconds for full open/close (default: 30)

#### Learning RF Codes

To capture RF codes from your existing Nice remote:

1. Install an RF receiver module (like RXB6) on your Raspberry Pi
2. Use `rpi-rf_receive` tool to capture codes:
   ```bash
   rpi-rf_receive -g 27
   ```
3. Press buttons on your Nice remote and note the codes
4. Update the codes in `nice_protocol.py`

## Usage

Once configured, your blinds will appear as cover entities in Home Assistant. You can:

- **Dashboard Control**: Use open/close/stop buttons and position slider
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

### Enable Debug Logging

To see detailed debug information during setup and operation, add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.blinds_control: debug
```

Then restart Home Assistant. Debug logs will show HTTP requests, device discovery details, and error information.

### HTTP Controller Issues

**Integration not found:**
- Restart Home Assistant after installation
- Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
- Check logs: Settings → System → Logs

**Cannot connect to controller:**
- Verify controller IP address and network connectivity
- Check username and password
- Ensure controller's web interface is accessible from Home Assistant

**No devices found:**
- Verify devices are configured in your Nice controller
- Check controller's device list page is accessible
- Review Home Assistant logs for parsing errors

### RF433 Issues

**Blinds not responding:**
- Check RF transmitter wiring
- Verify GPIO pin configuration
- Ensure RF codes are correctly captured
- Check Home Assistant logs for errors

**Permission denied on GPIO:**
- Ensure Home Assistant has permission to access GPIO pins
- Add the user to the `gpio` group: `sudo usermod -a -G gpio homeassistant`

### Position Tracking Issues

If position tracking is inaccurate:
1. Measure the actual time for full open/close
2. Adjust the **Move Time** setting during configuration
3. Test with full open/close cycles

## Advanced Configuration

### Multiple Controllers

You can add multiple controllers by adding the integration multiple times. Each instance will discover and manage its own set of devices.

### Adjusting Movement Time

The **Move Time** parameter controls how long the integration waits for a full open/close operation. Adjust this to match your blinds' actual movement time for accurate position tracking.

## Nice Protocol Information

The Nice protocol is proprietary and varies by device type:
- **HTTP/Network**: Modern Nice controllers with web interface and network API
- **RF 433MHz**: Older Nice motors (Era, Inti series) using 433.92 MHz frequency
- **BiDi-Bus**: Newer systems with bidirectional communication (experimental support)

## Support

For issues and feature requests, please visit the [GitHub Issues](https://github.com/laberge/nice-blinds-controller/issues) page.

## Contributing

Contributions are welcome! Especially:
- Additional Nice controller protocol support
- BiDi-Bus protocol implementation
- Code improvements and bug fixes

## License

This project is open source. Feel free to modify and distribute as needed.

## Disclaimer

This is an unofficial integration. Nice is a trademark of Nice S.p.A. This project is not affiliated with or endorsed by Nice S.p.A.
