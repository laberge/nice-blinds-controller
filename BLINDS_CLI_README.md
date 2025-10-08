# Nice Blinds CLI - Simple Control

Simple command-line interface for controlling your Nice blinds using friendly device names.

## Quick Setup

### 1. Set Your Password

Choose one of these methods:

**Method A: Environment Variable (Recommended)**
```bash
# Add to your ~/.zshrc (or ~/.bashrc if using bash)
echo 'export BLINDS_PASS="your_password_here"' >> ~/.zshrc
source ~/.zshrc
```

**Method B: Edit the Script Directly**
```bash
# Edit the blinds script
nano blinds

# Find this line near the top:
PASSWORD = os.getenv("BLINDS_PASS", "")

# Change it to:
PASSWORD = os.getenv("BLINDS_PASS", "your_password_here")
```

### 2. Verify Setup

```bash
./blinds list
```

You should see all 25 of your devices listed.

## Usage

### Basic Commands

```bash
# Open a blind
./blinds open "MBA 3"

# Close a blind  
./blinds close "Kitchen 1"

# Stop a blind
./blinds stop "Office 1"

# List all devices
./blinds list
```

### Your Device Names

- **Master Bedroom Area**: MBA 1, MBA 3
- **Master Bedroom**: MBR 1, MBR 2, MBR 4
- **Sunroom**: Sunroom 1, Sunroom 2, Sunroom 3, Sunroom 4, Sunroom 5
- **Kitchen**: Kitchen 1, Kitchen 2
- **Office**: Office 1-12
- **Living Room**: Living Room

### Shell Aliases (Optional)

Add these to your `~/.zshrc` for even simpler commands:

```bash
# Add to ~/.zshrc
alias open-blinds='./path/to/blinds open'
alias close-blinds='./path/to/blinds close'
alias stop-blinds='./path/to/blinds stop'

# Usage examples:
# open-blinds "MBA 3"
# close-blinds "Kitchen 1"
```

### Advanced: Create Individual Blind Commands

```bash
# Add to ~/.zshrc
alias mba3-open='~/path/to/blinds open "MBA 3"'
alias mba3-close='~/path/to/blinds close "MBA 3"'
alias kitchen-open='~/path/to/blinds open "Kitchen 1"'

# Then just run:
# mba3-open
# kitchen-close
```

## Configuration

The script uses these environment variables (or edit the script directly):

- `BLINDS_URL` - Controller URL (default: http://192.168.10.235)
- `BLINDS_USER` - Username (default: aaron)
- `BLINDS_PASS` - Password (required)

## Examples

```bash
# Morning routine - open all sunroom blinds
./blinds open "Sunroom 1"
./blinds open "Sunroom 2"
./blinds open "Sunroom 3"
./blinds open "Sunroom 4"
./blinds open "Sunroom 5"

# Close office blinds for presentation
for i in {1..12}; do ./blinds close "Office $i"; done

# Stop all kitchen blinds
./blinds stop "Kitchen 1"
./blinds stop "Kitchen 2"
```

## Troubleshooting

**"Device not found" error**
- Run `./blinds list` to see exact device names
- Device names are case-insensitive
- Make sure quotes are around the device name

**"Password not configured" error**
- Set BLINDS_PASS environment variable
- OR edit the script and hardcode the password

**Connection timeout**
- Verify controller is reachable: `ping 192.168.10.235`
- Check URL in script matches your controller IP

## Integration with Home Assistant

This is a standalone tool. For Home Assistant integration:
1. Install the Nice Blinds Controller integration via HACS
2. Update to v1.4.0 or later
3. Configure with your controller details
4. All 25 devices will be discovered automatically

## Script Files

- `blinds` - Main CLI script (this one!)
- `send_command.py` - Lower-level command sender (uses device IDs)
- `test_controller.py` - Diagnostic tool for troubleshooting

