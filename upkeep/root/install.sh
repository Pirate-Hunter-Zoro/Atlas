#!/bin/bash
# The one-time root half of upkeep. Run once per Mac, and again after editing root/:
#
#     sudo bash upkeep/root/install.sh
#
# Selects Xcode, accepts its license, runs its first launch, turns on App Store
# automatic updates, and installs the LaunchDaemon com.mikeyferguson.upkeep-root,
# which repeats the Xcode half daily and at load and writes the status upkeep reads.
# Root runs a COPY in a root-owned directory, never the repo file: a root job
# executing a user-writable script is a privilege escalation.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "run with sudo: sudo bash $0" >&2
  exit 1
fi

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="/Library/Application Support/upkeep-root"
PLIST="/Library/LaunchDaemons/com.mikeyferguson.upkeep-root.plist"

install -d -o root -g wheel -m 755 "$DEST"
install -o root -g wheel -m 755 "$SRC/upkeep-root.sh" "$DEST/upkeep-root.sh"
install -o root -g wheel -m 644 "$SRC/com.mikeyferguson.upkeep-root.plist" "$PLIST"

# App Store automatic updates (System Settings, App Store, Automatic Updates).
defaults write /Library/Preferences/com.apple.commerce AutoUpdate -bool true
defaults write /Library/Preferences/com.apple.SoftwareUpdate AutomaticallyInstallAppUpdates -bool true

launchctl bootout system/com.mikeyferguson.upkeep-root 2>/dev/null || true
launchctl bootstrap system "$PLIST"

# One pass now, so the status exists and the install is proven.
/bin/bash "$DEST/upkeep-root.sh" || true
echo "installed. status:"
cat "$DEST/status.json" 2>/dev/null || echo "(no status written)"
