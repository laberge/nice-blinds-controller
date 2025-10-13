# Nice Blinds - Dotfiles Integration

Setup instructions for managing Nice Blinds CLI configuration in your dotfiles.

## Quick Setup for Dotfiles Users

### Option 1: Source the Config File (Recommended)

1. **Link or copy** `blinds.zsh` to your dotfiles:
   ```zsh
   # Option A: Symlink
   ln -s ~/Developer/git/nice-blinds-controller/blinds.zsh ~/dotfiles/zsh/blinds.zsh
   
   # Option B: Copy
   cp ~/Developer/git/nice-blinds-controller/blinds.zsh ~/dotfiles/zsh/blinds.zsh
   ```

2. **Source it** in your main zsh config:
   ```zsh
   # In your dotfiles/.zshrc or dotfiles/zsh/config.zsh
   source ~/dotfiles/zsh/blinds.zsh
   ```

3. **Set your password** (choose a secure method):
   
   **Method A: Separate secure file (recommended)**
   ```zsh
   # Create ~/dotfiles/zsh/secrets.zsh (add to .gitignore!)
   export BLINDS_PASS="your_password_here"
   
   # Source it before blinds.zsh
   source ~/dotfiles/zsh/secrets.zsh
   source ~/dotfiles/zsh/blinds.zsh
   ```
   
   **Method B: Environment variable**
   ```zsh
   # In ~/dotfiles/zsh/env.zsh
   export BLINDS_PASS="your_password_here"
   ```
   
   **Method C: Use a password manager**
   ```zsh
   # Example with 1Password CLI
   export BLINDS_PASS="$(op read 'op://Personal/Nice Controller/password')"
   ```

4. **Reload your shell**:
   ```zsh
   source ~/.zshrc
   ```

### Option 2: Manual Configuration

Add this to your dotfiles (e.g., `~/dotfiles/zsh/aliases.zsh`):

```zsh
# Nice Blinds CLI
export BLINDS_URL="http://192.168.10.235"
export BLINDS_USER="aaron"
export BLINDS_PASS="your_password"  # Or load from secrets
alias blinds="/Users/aaron/Developer/git/nice-blinds-controller/blinds"
```

## Recommended Dotfiles Structure

```
~/dotfiles/
├── .gitignore          # Add: zsh/secrets.zsh
├── .zshrc              # Main config
└── zsh/
    ├── env.zsh         # Environment variables
    ├── aliases.zsh     # All aliases
    ├── secrets.zsh     # Passwords (gitignored!)
    └── blinds.zsh      # Nice Blinds config (symlinked or copied)
```

### .gitignore

```gitignore
# Sensitive files
zsh/secrets.zsh
**/*secrets*
**/*password*
```

### secrets.zsh (gitignored)

```zsh
# ~/dotfiles/zsh/secrets.zsh
export BLINDS_PASS="your_actual_password"
```

### Main .zshrc

```zsh
# ~/dotfiles/.zshrc

# Load secrets first (if you keep them separate)
[[ -f ~/dotfiles/zsh/secrets.zsh ]] && source ~/dotfiles/zsh/secrets.zsh

# Load environment variables
source ~/dotfiles/zsh/env.zsh

# Load aliases (including blinds)
source ~/dotfiles/zsh/aliases.zsh

# OR: Load blinds config directly
source ~/dotfiles/zsh/blinds.zsh
```

## Security Best Practices

### Don't Commit Passwords!

```zsh
# ❌ BAD - Don't commit this
export BLINDS_PASS="mypassword123"

# ✅ GOOD - Load from gitignored file
[[ -f ~/.secrets ]] && source ~/.secrets

# ✅ GOOD - Load from password manager
export BLINDS_PASS="$(security find-generic-password -a blinds -w 2>/dev/null)"

# ✅ GOOD - Load from environment (set outside dotfiles)
export BLINDS_PASS="${BLINDS_PASSWORD:-}"
```

### Using macOS Keychain

```zsh
# Store password in keychain (one time)
security add-generic-password -a blinds -s "Nice Blinds" -w "your_password"

# Load in your dotfiles
export BLINDS_PASS="$(security find-generic-password -a blinds -s 'Nice Blinds' -w 2>/dev/null)"
```

### Using 1Password CLI

```zsh
# If you use 1Password
export BLINDS_PASS="$(op read 'op://Personal/Nice Controller/password' 2>/dev/null)"
```

## Optional Enhancements

### Per-Room Functions

Add to your dotfiles:

```zsh
# ~/dotfiles/zsh/blinds.zsh

# Open/close all office blinds
office() {
  local cmd=$1
  [[ -z "$cmd" ]] && cmd="list"
  
  if [[ "$cmd" == "open" ]] || [[ "$cmd" == "close" ]] || [[ "$cmd" == "stop" ]]; then
    for i in {1..12}; do
      blinds $cmd "Office $i"
      sleep 0.3
    done
  else
    echo "Usage: office [open|close|stop]"
  fi
}

# Open/close all sunroom blinds
sunroom() {
  local cmd=$1
  [[ -z "$cmd" ]] && cmd="list"
  
  if [[ "$cmd" == "open" ]] || [[ "$cmd" == "close" ]] || [[ "$cmd" == "stop" ]]; then
    for i in {1..5}; do
      blinds $cmd "Sunroom $i"
      sleep 0.3
    done
  else
    echo "Usage: sunroom [open|close|stop]"
  fi
}

# Usage:
# office open
# sunroom close
```

### Completion

Add zsh completion for device names:

```zsh
# ~/dotfiles/zsh/completions/_blinds

#compdef blinds

_blinds() {
  local -a commands devices
  commands=(
    'open:Open a blind'
    'close:Close a blind'
    'stop:Stop a blind'
    'list:List all devices'
  )
  
  devices=(
    '"MBA 3"'
    '"MBA 1"'
    '"Kitchen 1"'
    '"Kitchen 2"'
    '"Office 1"'
    # ... add all your devices
  )
  
  if (( CURRENT == 2 )); then
    _describe 'command' commands
  elif (( CURRENT == 3 )); then
    _describe 'device' devices
  fi
}

_blinds
```

## Testing Your Setup

```zsh
# Reload your shell
source ~/.zshrc

# Test the command
blinds list

# Test a blind
blinds open "Living Room"

# Verify environment variables
echo $BLINDS_URL
echo $BLINDS_USER
echo $BLINDS_PASS  # Should show your password
```

## Troubleshooting

**Command not found:**
- Check the path in your alias matches the script location
- Ensure blinds.zsh is sourced in your .zshrc

**Password not set:**
- Check BLINDS_PASS is exported before sourcing blinds.zsh
- Verify your secrets file is being loaded

**Permission denied:**
- Ensure the blinds script is executable: `chmod +x ~/path/to/blinds`

## Migration from ~/.zshrc

If you already added config to ~/.zshrc directly:

```zsh
# 1. Move the config to your dotfiles
grep -A 5 "Nice Blinds" ~/.zshrc >> ~/dotfiles/zsh/blinds.zsh

# 2. Remove from ~/.zshrc
# (manually edit and remove the Nice Blinds section)

# 3. Add source to your dotfiles loader
echo "source ~/dotfiles/zsh/blinds.zsh" >> ~/dotfiles/.zshrc
```

## Example Full Setup

```zsh
# ~/dotfiles/.zshrc
source ~/dotfiles/zsh/secrets.zsh  # Password (gitignored)
source ~/dotfiles/zsh/blinds.zsh   # Blinds config

# ~/dotfiles/zsh/secrets.zsh (gitignored)
export BLINDS_PASS="actual_password"

# ~/dotfiles/zsh/blinds.zsh
export BLINDS_URL="http://192.168.10.235"
export BLINDS_USER="aaron"
alias blinds="/Users/aaron/Developer/git/nice-blinds-controller/blinds"

# Optional functions
office() { for i in {1..12}; do blinds ${1:-list} "Office $i"; sleep 0.3; done }
sunroom() { for i in {1..5}; do blinds ${1:-list} "Sunroom $i"; sleep 0.3; done }
```

---

**Ready to go!** Your blinds CLI will now be managed through your dotfiles and work across machines. 🎉

