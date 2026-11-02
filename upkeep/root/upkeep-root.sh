#!/bin/bash
# Run as root by com.mikeyferguson.upkeep-root, daily and at load, from the copy
# in /Library/Application Support/upkeep-root. Keeps Xcode selected, licensed and
# past its first launch, and writes status.json, which `upkeep` reads.
set -uo pipefail

DEST="/Library/Application Support/upkeep-root"
XCODE="/Applications/Xcode.app"
DEV="$XCODE/Contents/Developer"
result=ok
detail=""

say() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ ! -d "$XCODE" ]; then
  result=no-xcode
  detail="Xcode is not installed: App Store, or sudo mas get 497799835"
else
  if [ "$(xcode-select -p 2>/dev/null)" != "$DEV" ]; then
    say "xcode-select -s $DEV"
    xcode-select -s "$DEV" || { result=failed; detail="xcode-select -s failed"; }
  fi
  if ! xcodebuild -license check >/dev/null 2>&1; then
    say "xcodebuild -license accept"
    xcodebuild -license accept || { result=failed; detail="xcodebuild -license accept failed"; }
  fi
  if ! xcodebuild -checkFirstLaunchStatus >/dev/null 2>&1; then
    say "xcodebuild -runFirstLaunch"
    xcodebuild -runFirstLaunch || { result=failed; detail="xcodebuild -runFirstLaunch failed"; }
  fi
  if ! xcodebuild -checkFirstLaunchStatus >/dev/null 2>&1; then
    result=failed
    detail="${detail:-Xcode still needs its first launch}"
  fi
fi
auto="$(defaults read /Library/Preferences/com.apple.commerce AutoUpdate 2>/dev/null || echo unset)"

mkdir -p "$DEST"
cat >"$DEST/status.json.tmp" <<JSON
{"at": "$(date '+%Y-%m-%dT%H:%M:%S')", "result": "$result", "detail": "$detail", "app_store_auto_update": "$auto"}
JSON
chmod 644 "$DEST/status.json.tmp"
mv "$DEST/status.json.tmp" "$DEST/status.json"
say "result: $result${detail:+ ($detail)}"
