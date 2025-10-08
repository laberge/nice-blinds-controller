# Changelog

All notable changes to the Nice Blinds Controller integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **CLI Tools**: Complete command-line interface for controlling blinds
  - `blinds` - Main CLI using friendly device names (e.g., `blinds open "MBA 3"`)
  - `send_command.py` - Standalone command sender using device IDs
  - `test_commands.py` - Command testing tool
- **Setup Tools**:
  - `setup_blinds_cli.sh` - Interactive setup script (zsh-native)
  - `blinds.zsh` - Dotfiles-ready configuration file
- **Documentation**:
  - `QUICK_START.md` - Complete quick start guide
  - `BLINDS_CLI_README.md` - Detailed CLI documentation
  - `DOTFILES_SETUP.md` - Dotfiles integration guide with security best practices
- Support for dotfiles workflows with multiple setup options
- Password security options (environment variables, keychain, password managers)
- Per-room batch operations and custom aliases

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

