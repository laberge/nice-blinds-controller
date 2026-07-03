# Nice Blinds CLI

Standalone command-line interface for controlling Nice blinds by device name — no Home Assistant required.

## Setup

Run the interactive setup script, which installs dependencies and generates shell configuration:

```bash
./setup_blinds_cli.sh
```

Or configure manually with environment variables (e.g. in `~/.zshrc`):

```bash
export BLINDS_URL="http://192.168.1.100"   # your controller's URL
export BLINDS_USER="admin"                 # controller username
export BLINDS_PASS="your_password"         # controller password
```

> **Tip:** Keep `BLINDS_PASS` in a separate gitignored file or load it from a password manager (e.g. `export BLINDS_PASS="$(op read 'op://Personal/Nice Controller/password')"`) rather than committing it to your dotfiles.

Verify the setup:

```bash
./blinds list
```

You should see every device configured on your controller.

## Usage

### Device commands

```bash
./blinds open "Living Room"    # Open a blind
./blinds close "Kitchen 1"     # Close a blind
./blinds stop "Office 1"       # Stop a blind
./blinds list                  # List all devices with their IDs
./blinds status                # Status of all devices (plus group summary)
./blinds status "Office 1"     # Status of one device
```

Device names come from your controller's configuration and are matched case-insensitively.

### Group commands

```bash
./blinds list-groups           # List all controller groups
./blinds open-group "Office"   # Open all blinds in a group
./blinds close-group "Sunroom" # Close all blinds in a group
./blinds stop-group "Kitchen"  # Stop all blinds in a group
```

Group commands execute at the hardware level, so all member devices move simultaneously.

### Shell aliases (optional)

```bash
# Add to ~/.zshrc — see blinds.zsh for a ready-made template
alias blinds='~/path/to/nice-blinds-controller/blinds'
alias office-open='blinds open-group "Office"'
```

## Configuring groups

Groups are managed in your Nice controller's web interface, not in this CLI:

1. Open `http://<controller-ip>/grp_list.htm`
2. Create a group and add devices to it
3. Save — the group is instantly available to the CLI, no restart needed

### How controller groups work

Nice controller groups execute **pre-programmed actions**: when you send a group command, the controller replays whatever actions were programmed for that group on each member device, simultaneously. A group may span rooms, and different devices may be programmed with different actions. For predictable behavior, create groups where all devices perform the same action.

To see exactly what a group will do, view it in the controller's web UI.

## Troubleshooting

**"Device not found"** — run `./blinds list` to see exact names; quote names containing spaces.

**"Password not configured" / "Controller URL not configured"** — export `BLINDS_PASS` / `BLINDS_URL` as shown above.

**Connection timeout** — verify the controller is reachable (`ping <controller-ip>`) and `BLINDS_URL` is correct.

## Related tools

- `blinds` — this CLI (friendly device names)
- `send_command.py` — lower-level command sender using raw device IDs
- `test_controller.py` — connection/discovery diagnostic

For Home Assistant integration, see the main [README](README.md).
