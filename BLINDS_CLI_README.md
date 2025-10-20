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

# Show status of all devices (includes group summary)
./blinds status

# Show status of a specific device
./blinds status "Office 1"
```

### Group Commands

```bash
# List all controller groups
./blinds list-groups

# Open all blinds in a group (truly simultaneous via hardware)
./blinds open-group "Office"

# Close all blinds in a group
./blinds close-group "Sunroom"

# Stop all blinds in a group
./blinds stop-group "Kitchen"

# Groups are configured in your Nice controller's web interface
# Commands execute at the hardware level for instant, synchronized operation
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
# List all groups configured on your controller
./blinds list-groups

# Morning routine - open all sunroom blinds (hardware-synchronized)
./blinds open-group "Sunroom"

# Close all office blinds for presentation
./blinds close-group "Office"

# Check status of all devices and groups
./blinds status

# Individual device control
./blinds open "MBA 3"
./blinds close "Kitchen 1"
./blinds stop "Office 1"
```

## Configuring Groups

Groups are managed in your Nice controller's web interface:

1. Open: `http://192.168.10.235/grp_list.htm` (use your controller's IP)
2. Click "New" to create a group
3. Add devices to the group
4. Save the group
5. Groups are instantly available to the CLI - no restart needed!

When you execute a group command, the controller sends the command to all devices simultaneously at the hardware level for perfect synchronization.

### How Controller Groups Work

Nice controller groups execute **pre-programmed actions**. When you send a group command:

1. The controller receives your command (open/close/stop)
2. The controller executes the actions programmed for that group
3. Each device in the group receives its pre-programmed command **simultaneously**

**Important:**
- Groups execute whatever actions were programmed in the controller
- A group may include devices from multiple rooms
- Different devices may have different actions (some open, some close)
- This is controlled in the Nice controller's web interface, not in this CLI

**To see exactly what a group will do:**
- Open your controller's web UI: `http://192.168.10.235/grp_list.htm`
- View or edit the group to see which devices and actions are configured

**Recommendation:**
For predictable behavior, create groups in your controller where all devices perform the same action (all open, all close, etc.).

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

