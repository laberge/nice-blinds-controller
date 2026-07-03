# Nice Blinds CLI Configuration
# Source this file in your zsh config or copy the contents to your dotfiles.

# Configuration - update for your controller
export BLINDS_URL="http://192.168.1.100"
export BLINDS_USER="admin"
# Set BLINDS_PASS in a separate, gitignored file (or a password manager):
#   export BLINDS_PASS="your_password"

# Path to the blinds script - update to where you cloned this repo
BLINDS_SCRIPT_DIR="$HOME/Developer/git/nice-blinds-controller"

alias blinds="${BLINDS_SCRIPT_DIR}/blinds"

# Optional: per-group shortcuts (groups are configured on the controller)
# alias office-open='blinds open-group "Office"'
# alias office-close='blinds close-group "Office"'
