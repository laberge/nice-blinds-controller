# Nice Blinds Controller - Quick Start Guide

## ✅ What's Working

Your Nice controller at **192.168.10.235** has been successfully integrated with **25 devices** discovered:

- MBA 1, MBA 3
- MBR 1, MBR 2, MBR 4  
- Sunroom 1-5 (5 blinds)
- Kitchen 1-2 (2 blinds)
- Office 1-12 (12 blinds)
- Living Room

## 🚀 Three Ways to Control Your Blinds

### 1. Simple CLI (Easiest) ✨

**One-Time Setup:**
```bash
./setup_blinds_cli.sh
# Enter your password when prompted
source ~/.zshrc  # or restart terminal
```

**Usage:**
```bash
blinds open "MBA 3"
blinds close "Kitchen 1"
blinds stop "Office 1"
blinds list
```

**The syntax you requested:**
```bash
open "MBA 3"     # If you create an alias: alias open='blinds open'
close "MBA 3"    # If you create an alias: alias close='blinds close'
stop "MBA 3"     # If you create an alias: alias stop='blinds stop'
```

### 2. Direct Commands (More Control)

```bash
python3 send_command.py http://192.168.10.235 aaron PASSWORD 1,01 open
python3 send_command.py http://192.168.10.235 aaron PASSWORD 1,0B close
```

### 3. Home Assistant Integration (Automation)

**Update Integration:**
1. Open HACS in Home Assistant
2. Update "Nice Blinds Controller" to **v1.4.0**
3. Remove old integration (Settings → Devices & Services)
4. Add integration again with controller details
5. Select devices (all 25 will appear!)

**Then use:**
- Dashboard controls
- Voice commands (Alexa, Google, Siri)
- Automations and scenes
- Scripts

## 📋 Quick Reference

### Device IDs

| Device | ID | Device | ID |
|--------|-----|--------|-----|
| MBA 3 | 1,01 | Kitchen 1 | 1,0B |
| MBR 1 | 1,02 | Kitchen 2 | 1,0C |
| MBR 2 | 1,03 | Office 1 | 1,0E |
| MBR 4 | 1,04 | Office 2 | 1,0D |
| Sunroom 1 | 1,05 | Office 3 | 1,0F |
| MBA 1 | 1,06 | Office 4-12 | 1,10-1,18 |
| Sunroom 2-5 | 1,07-0A | Living Room | 1,19 |

### Commands

| Command | Code | Function |
|---------|------|----------|
| `open` | 03 | Opens blind (moves up) |
| `close` | 04 | Closes blind (moves down) |
| `stop` | 02 | Stops movement |

### API Format

```
http://192.168.10.235/cgi/devcmd.xml?adr=1&ept=01&cmd=03
                                          ^      ^      ^
                                          |      |      |
                                      address  endpoint  command
```

## 🛠 Tools Available

| Tool | Purpose | Usage |
|------|---------|-------|
| `blinds` | Simple CLI with device names | `./blinds open "MBA 3"` |
| `send_command.py` | Direct commands with IDs | `python3 send_command.py URL USER PASS ID CMD` |
| `test_controller.py` | Diagnostic/troubleshooting | `python3 test_controller.py URL USER PASS` |
| `test_commands.py` | Test commands (HA dependent) | Requires Home Assistant modules |

## 🔧 Setup Files

- `setup_blinds_cli.sh` - One-command setup for CLI
- `BLINDS_CLI_README.md` - Detailed CLI documentation
- `QUICK_START.md` - This file
- `CHANGELOG.md` - Version history

## 📝 Example Automations

**Morning Routine (Shell Script):**
```bash
#!/bin/bash
# morning_routine.sh
blinds open "Sunroom 1"
blinds open "Sunroom 2"
blinds open "Sunroom 3"
blinds open "Sunroom 4"
blinds open "Sunroom 5"
blinds open "Kitchen 1"
blinds open "Kitchen 2"
```

**Close All Office (Loop):**
```bash
for i in {1..12}; do
  blinds close "Office $i"
  sleep 0.5
done
```

**Home Assistant Automation:**
```yaml
automation:
  - alias: "Open blinds at sunrise"
    trigger:
      platform: sun
      event: sunrise
    action:
      service: cover.open_cover
      target:
        entity_id: 
          - cover.sunroom_1
          - cover.sunroom_2
          - cover.kitchen_1
```

## 🎯 Next Steps

1. **Run setup:** `./setup_blinds_cli.sh`
2. **Test it:** `blinds list`
3. **Try a command:** `blinds open "Living Room"`
4. **Update HA integration** to v1.4.0
5. **Create automations** for your daily routines

## 🐛 Troubleshooting

**Device not found:**
- Run `blinds list` to see exact names
- Names are case-insensitive
- Use quotes around device name

**Connection errors:**
- Check controller is on: `ping 192.168.10.235`
- Verify credentials
- Check firewall settings

**HA integration not finding devices:**
- Update to v1.4.0 or later
- Remove and re-add integration
- Check logs with debug enabled

## 📚 Documentation

- Main README: `README.md`
- CLI Guide: `BLINDS_CLI_README.md`
- Changelog: `CHANGELOG.md`
- GitHub: https://github.com/laberge/nice-blinds-controller

---

**Version:** 1.4.0  
**Controller:** Nice IT4WiFi at 192.168.10.235  
**Protocol:** HTTP/XML via `/cgi/devlst.xml` and `/cgi/devcmd.xml`  
**Devices:** 25 EI SM smart motors detected

