# Changelog

All notable changes to the Nice Blinds Controller integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.9.1] - 2025-11-25

### Fixed
- **CLI Tools**: Enhanced error handling with specific exception types
  - Added detailed connection error messages for `ClientConnectorError`
  - Explicit timeout error handling with helpful diagnostics
  - Improved authentication failure detection (401 errors)
  - Better error messages guide users to check controller connectivity and credentials

## [1.9.0] - 2025-11-10

### Added
- Periodic device polling powered by a shared `DataUpdateCoordinator` so entities stay in sync without per-entity sessions.
- Repository-level `LICENSE` (MIT) and `CODEOWNERS` to satisfy HACS Default requirements.

### Changed
- Covers now reuse a single Nice controller instance stored in integration runtime data.
- Pinned `aiohttp==3.9.5` to ensure reproducible installs.
- README now clarifies controller group behavior and how to refresh them from integration options.

### Fixed
- Eliminated redundant HTTP sessions and manual polling logic in each entity.
- Removed unused group configuration flow/residual CLI dependencies.

## [1.8.2] - 2025-10-27

### Fixed
- **Home Assistant Integration**: Fixed disabled buttons in cover entity UI
  - Added explicit `available` property to ensure entities are always available
  - Fixed `is_closed` property to return `None` when position is unknown instead of False
  - Entities now properly enable open/close/stop buttons even before initial position update
- Updated manifest version to 1.8.2

## [1.8.1] - 2025-10-24

### Fixed
- CLI status table borders now properly align on the right side
- Fixed controller groups table column width calculations
- Corrected summary line formatting for consistent table borders

## [1.8.0] - 2025-10-10

### Added
- Group cover entity (`BlindsGroupCover`) with true concurrent commands using `asyncio.gather()`
- Real-time status polling from controller; entities set `should_poll = True`

### Changed
- Discovery switched to XML endpoint `/cgi/devlst.xml`; removed BeautifulSoup dependency
- `NiceController` provides `get_device_status()` for per-device polling
- Cover commands return immediately; positions update via polling
- Manifest `iot_class` set to `local_polling`; added icon `mdi:blinds`

### Fixed
- Clean shutdown of HTTP session via `NiceController.cleanup()` on entity removal

## [1.7.0] - 2025-10-08

### 🎉 NEW FEATURE - Groups in Integration Settings!

Groups can now be configured during integration setup and are visible in Home Assistant's admin UI!

### Added
- **Group Configuration in Setup Flow**: Create groups during integration setup
  - New "Configure Groups" step after device selection
  - Create multiple groups (e.g., "Office Blinds", "Sunroom Blinds")
  - Select which devices belong to each group
  - Groups created as proper cover entities
- **Group Cover Entities**: Integration creates actual group cover entities
  - Groups appear in Home Assistant UI as `cover.office_blinds`, etc.
  - Control multiple blinds with single open/close/stop/position commands
  - Average position displayed across all group members
  - Works with automations, dashboards, and voice assistants

### Changed
- Config flow now has 3 steps instead of 2:
  1. Controller connection
  2. Select devices
  3. Configure groups (NEW!)
- Groups stored in config entry data
- Group entities created alongside individual blind entities

### Technical Details
- `BlindsGroupCover` entity class for group control
- Groups use `asyncio.gather()` to send commands to all members simultaneously
- Group position calculated as average of member positions
- Group opening/closing state shows true if any member is moving

## [1.6.0] - 2025-10-08

### 🎯 MAJOR IMPROVEMENT - Real Position Tracking!

**Breaking Change:** The integration now reads ACTUAL positions from the controller instead of estimating based on time.

### Added
- **Real-time Position Tracking**: Integration now polls the controller for actual blind positions
- **Automatic Status Updates**: Blinds update their position from the controller every poll interval
- **Moving State Detection**: Automatically detects when blinds are opening/closing

### Changed
- **Position Source**: Changed from time-based estimation to reading `pos` attribute from controller XML
- **Polling Enabled**: Set `should_poll = True` to fetch real status
- **Faster Commands**: Open/close commands return immediately, position updates via polling
- Added `get_device_status()` method to NiceController for fetching individual blind status

### Fixed
- Blinds now show actual position instead of estimated position
- Position stays in sync with physical blind state
- Moving state (opening/closing) now reflects actual motor state

### Technical Details
- Polls `/cgi/devlst.xml` endpoint for device status
- Parses `sta` (status code) and `pos` (position) attributes
- Status codes: `00/01`=Stopped, `02`=Opening, `03`=Closing, `04`=Open, `05`=Closed
- Position: 0-100 (0=closed, 100=open), 255=unknown

## [1.5.0] - 2025-10-08

### Added - CLI Tools & Enhancements
- **Complete CLI Tools Suite**: Standalone command-line interface for controlling blinds without Home Assistant
  - `blinds` - Main CLI using friendly device names (e.g., `blinds open "MBA 3"`)
  - `send_command.py` - Standalone command sender using device IDs
  - `test_commands.py` - Command testing tool
  - `test_controller.py` - Diagnostic tool (from v1.3.0)
- **Status Command**: Beautiful table display showing all blinds status
  - Color-coded indicators (🟢 Open, 🔴 Closed, 🔵 Opening, 🟡 Closing)
  - Visual progress bars (██████████ / ░░░░░░░░░░)
  - Real-time position tracking
  - Alphabetically sorted device list
  - Summary statistics
- **Setup Tools**:
  - `setup_blinds_cli.sh` - Interactive setup script (zsh-native)
  - `blinds.zsh` - Dotfiles-ready configuration file
- **Groups Support** (Infrastructure):
  - `blinds_groups.yaml` - Group configuration file with pre-defined rooms
  - Group command infrastructure for batch operations
- **Comprehensive Documentation**:
  - `QUICK_START.md` - Complete quick start guide
  - `BLINDS_CLI_README.md` - Detailed CLI documentation
  - `DOTFILES_SETUP.md` - Dotfiles integration guide with security best practices
- Support for dotfiles workflows with multiple setup options
- Password security options (environment variables, keychain, password managers)

### Fixed
- Status table alignment (all borders now align properly)
- Column width optimization for better readability

### Dependencies
- Added PyYAML for groups configuration support

## [1.4.0] - 2025-10-08

### 🎉 FIXED - Device Discovery Now Works!

This release fixes the critical device discovery issue where no devices were being found during setup.

### Changed
- **BREAKING FIX**: Switched from HTML parsing (`/dev_list.htm`) to XML endpoint (`/cgi/devlst.xml`)
- Replaced BeautifulSoup with native Python `xml.etree.ElementTree` for XML parsing
- Device discovery now correctly finds all installed blinds from the controller

### Fixed
- Device discovery now works with Nice controllers that use AJAX to load device lists
- Properly parses device attributes from XML: address, endpoint, productName, description
- Correctly filters for installed devices only (`installed='1'`)
- Better error detection for authentication issues

### Removed
- Removed `beautifulsoup4` dependency (no longer needed)

### Technical Details
The Nice controller uses JavaScript/AJAX to dynamically load devices via XML, not static HTML tables. The integration now fetches and parses the XML directly.

### Testing
Successfully tested with Nice controller - detected all 25 installed devices including:
- Master Bedroom blinds
- Sunroom blinds (5 devices)
- Kitchen blinds (2 devices)
- Office blinds (12 devices)
- Living Room blind

## [1.3.0] - 2025-10-08

### Added
- Comprehensive debug logging throughout device discovery and authentication
- Full HTML response logging for troubleshooting
- Authentication error detection for controllers that return 200 with login page
- Connection testing method (`test_connection()`) for basic connectivity checks
- Flexible regex patterns to match different controller formats
- Enhanced HTML parsing with detailed row/cell analysis
- Diagnostic script (`test_controller.py`) to test controller connection and see raw responses
- Complete debug logging configuration in `logger.yaml`

### Changed
- Improved error messages for authentication failures
- Enhanced device discovery logging with step-by-step details
- Updated logger.yaml with full debug configuration examples

### Fixed
- Better detection of authentication failures
- More robust device pattern matching for various controller types

## [1.2.0] - Previous Release

### Features
- HTTP Controller Support
- Device Discovery
- Multi-device Selection
- Position Control

## [1.1.0] - Previous Release

### Features
- Initial HTTP controller implementation
- Basic device control

## [1.0.0] - Initial Release

### Features
- Initial release of Nice Blinds Controller integration
- Basic HTTP support

