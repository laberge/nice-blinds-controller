# Nice Blinds CLI Configuration
# Source this file in your zsh config or copy the contents to your dotfiles

# Configuration
export BLINDS_URL="http://192.168.10.235"
export BLINDS_USER="aaron"
export BLINDS_PASS=""  # Set your password here or in a separate secure file

# Path to the blinds script
BLINDS_SCRIPT_DIR="/Users/aaron/Developer/git/nice-blinds-controller"

# Main alias
alias blinds="${BLINDS_SCRIPT_DIR}/blinds"

# Optional: Shorter aliases
alias blind="${BLINDS_SCRIPT_DIR}/blinds"
alias b="${BLINDS_SCRIPT_DIR}/blinds"

# Optional: Command aliases (if you want open/close/stop as commands)
# Uncomment these if you want:
# alias open='blinds open'
# alias close='blinds close'
# alias stop='blinds stop'

# Optional: Per-room aliases
# alias office-open='for i in {1..12}; do blinds open "Office $i"; sleep 0.5; done'
# alias office-close='for i in {1..12}; do blinds close "Office $i"; sleep 0.5; done'
# alias sunroom-open='for i in {1..5}; do blinds open "Sunroom $i"; sleep 0.5; done'
# alias sunroom-close='for i in {1..5}; do blinds close "Sunroom $i"; sleep 0.5; done'

# Optional: Specific blind shortcuts
# alias mba3='blinds'  # Usage: mba3 open "MBA 3"
# alias kitchen='blinds'  # Usage: kitchen open "Kitchen 1"

