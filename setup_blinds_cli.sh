#!/bin/zsh
# Setup script for Nice Blinds CLI

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          Nice Blinds CLI - Setup                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${(%):-%x}" )" && pwd )"

# Prompt for password
echo "Enter your Nice controller password (or press Enter to skip):"
read -s PASSWORD
echo ""

# Generate configuration
CONFIG="# Nice Blinds CLI Configuration
export BLINDS_PASS='$PASSWORD'
export BLINDS_URL='http://192.168.10.235'
export BLINDS_USER='aaron'
alias blinds='$SCRIPT_DIR/blinds'
"

echo "Generated configuration:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$CONFIG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Choose how to configure:"
echo "  1) Add to your dotfiles manually (recommended)"
echo "  2) Add to ~/.zshrc automatically"
echo "  3) Show me the commands only (I'll configure myself)"
echo ""
read "choice?Enter choice (1-3): "

case $choice in
    1)
        echo ""
        echo "Add the above configuration to your dotfiles."
        echo "Suggested locations:"
        echo "  - ~/dotfiles/.zshrc"
        echo "  - ~/dotfiles/zsh/env.zsh"
        echo "  - ~/dotfiles/aliases.zsh"
        echo ""
        echo "Then reload your shell:"
        echo "  source ~/.zshrc"
        ;;
    2)
        echo "" >> "$HOME/.zshrc"
        echo "$CONFIG" >> "$HOME/.zshrc"
        echo "✓ Configuration added to ~/.zshrc"
        echo ""
        echo "Reload your shell:"
        echo "  source ~/.zshrc"
        ;;
    3)
        echo ""
        echo "Manual setup instructions:"
        echo ""
        echo "1. Add these environment variables to your shell config:"
        echo "   export BLINDS_PASS='your_password'"
        echo "   export BLINDS_URL='http://192.168.10.235'"
        echo "   export BLINDS_USER='aaron'"
        echo ""
        echo "2. Add this alias:"
        echo "   alias blinds='$SCRIPT_DIR/blinds'"
        echo ""
        echo "3. Reload your shell"
        ;;
    *)
        echo "Invalid choice. Configuration not applied."
        exit 1
        ;;
esac

echo ""
echo "Usage examples:"
echo "  blinds open \"MBA 3\""
echo "  blinds close \"Kitchen 1\""
echo "  blinds list"
echo ""
echo "Setup complete! 🎉"

