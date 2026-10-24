#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# phi-probe.sh -- would the PHI guards refuse this path?
#
#   board/scripts/phi-probe.sh <path>
#
# Exits 0 only when both refuse it:
#   policy  ai-config/policy/phi.py's names_phi, loaded the way
#           tutorboard/leaving.py loads it before a push;
#   fence   tutorboard/fenced.py's refused_in, inside the path's subject.
# Exits 1 when either lets it through, 2 on a usage error or a policy that
# will not load. Prints one verdict per guard.
#
# The path is relative to the current directory or absolute, and need not
# exist. Nothing under it is listed or read: a probe of a fenced directory is a
# question about its name.
#
# Runs on the cluster's python3 (3.7) and on the Mac's bash 3.2.
# ---------------------------------------------------------------------------
set -u

if [ $# -ne 1 ] || [ -z "$1" ]; then
  echo "usage: phi-probe.sh <path>" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"

python3 - "$ROOT" "$1" <<'PY'
import os
import sys

root, arg = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(root, "board"))
from tutorboard import leaving                                # noqa: E402

full = os.path.abspath(os.path.expanduser(arg))
# The repository's spelling of the path: physical or logical, whichever the
# root is a prefix of. An absolute path outside the tree is asked as given.
rel = None
for top in (root, os.path.realpath(root)):
    for here in (full, os.path.realpath(os.path.dirname(full))
                 + os.sep + os.path.basename(full)):
        if here == top or here.startswith(top + os.sep):
            rel = os.path.relpath(here, top).replace(os.sep, "/")
            break
    if rel is not None:
        break
if rel is None:
    rel = full

policy, fence = leaving.probe(rel, root)
if policy is None:
    print("policy  missing: %s will not load" % leaving.POLICY)
    sys.exit(2)
print("policy  %s" % ("refuses" if policy else "PASSES"))
print("fence   %s" % ("refuses (%s/)" % fence if fence else "PASSES"))
sys.exit(0 if policy and fence else 1)
PY
