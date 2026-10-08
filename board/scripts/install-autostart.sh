#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# install-autostart.sh -- remove the old cluster login hook.
#
#   bash scripts/install-autostart.sh --uninstall
#
# Boards run on the Mac and nowhere else, so nothing on the cluster starts one
# at login any more. This takes the `tutor resume` hook an earlier install put
# in ~/.bashrc back out. It installs nothing.
# ---------------------------------------------------------------------------
set -uo pipefail

BEGIN_MARK="# >>> tutor-board resume >>>"
END_MARK="# <<< tutor-board resume <<<"
RC="$HOME/.bashrc"

strip_hook() {
  [ -f "$RC" ] || return 0
  grep -qF "$BEGIN_MARK" "$RC" || return 0
  python3 - "$RC" "$BEGIN_MARK" "$END_MARK" <<'PYEOF'
import io, sys
rc, begin, end = sys.argv[1], sys.argv[2], sys.argv[3]
text = io.open(rc, encoding="utf-8").read()
while begin in text and end in text:
    a = text.index(begin)
    b = text.index(end) + len(end)
    text = text[:a].rstrip("\n") + "\n" + text[b:].lstrip("\n")
io.open(rc, "w", encoding="utf-8").write(text)
PYEOF
  echo "removed the login hook from $RC"
}

if [ "${1:-}" = "--uninstall" ]; then
  strip_hook
  exit 0
fi

echo "usage: $0 --uninstall"
exit 1
