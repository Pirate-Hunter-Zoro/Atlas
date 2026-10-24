"""materials.py -- `board pull --materials`: a coding laptop copies the Mac
mini's ignored inputs over SSH.

Git carries none of what a tutor reads beside the code: every `materials/`,
a course's `textbook/`, its chapters' `reading/` and `lectures/`, and any
`assignment*` under a course. `rsync` copies those, and only those, from
`host` in this machine's `~/.config/tutor-board/config.json` (the Mac mini's
tailnet name; `user@host` works too), out of `host_atlas` there (the Atlas
checkout, relative to the remote home unless absolute; default
`Developer/Atlas`). `setup-mac.sh --coding` asks for `host` and writes it.

`NEVER` is excluded before anything is included: `.ink/`, `sessions/` and
any `.env*` never cross, nor `phi/` and `results/`, nor a build or a checkout.
Nothing here is ever deleted. SSH runs in batch mode, so a missing key is a
refusal, not a password prompt.

The constraint: standard library only, python 3.7 syntax.
"""

import os
import re
import subprocess

from . import paths, subjects

DEFAULT_ATLAS = "Developer/Atlas"
SSH = "ssh -o BatchMode=yes -o ConnectTimeout=15"

# Excluded wherever they are, first, so no include below can reach them.
NEVER = (".ink/", "sessions/", ".env*", "phi/", "results/", ".git/",
         ".venv/", ".lake/", "node_modules/", "__pycache__/",
         "/vendor/", "/ai-config/")
# The ignored inputs, as rsync include patterns (`dir/***` is the directory
# and everything under it). rsync's `/**/` needs at least one directory, unlike
# git's, so an assignment directly under a course needs its own line.
INPUTS = ("materials/***",
          "/courses/*/textbook/***",
          "/courses/*/chapters/*/reading/***",
          "/courses/*/chapters/*/lectures/***",
          "/courses/*/assignment*/***",
          "/courses/*/**/assignment*/***")

HOST_RE = re.compile(r"^(?:[A-Za-z0-9._-]+@)?[A-Za-z0-9][A-Za-z0-9.-]*$")
ATLAS_RE = re.compile(r"^[A-Za-z0-9._/~-]+$")


def filters(subject_ids=()):
    """The rsync filter arguments, in order: `NEVER`, then (given subjects
    such as `courses/Probability`) every subject directory but those, then
    `INPUTS`, then any directory to walk, then nothing else."""
    out = ["--exclude=" + p for p in NEVER]
    if subject_ids:
        out += ["--include=/%s/" % s.strip("/") for s in subject_ids]
        out.append("--exclude=/*/*")
    out += ["--include=" + p for p in INPUTS]
    out += ["--include=*/", "--exclude=*"]
    return out


def argv(host, atlas, base, subject_ids=()):
    """The whole rsync command: from `host:atlas/` into `base/`, pruning the
    directories that hold nothing it copies, deleting nothing."""
    return (["rsync", "-rlt", "--prune-empty-dirs", "-e", SSH]
            + filters(subject_ids)
            + ["%s:%s/" % (host, atlas.rstrip("/")),
               os.path.join(os.path.abspath(base), "")])


def where(cfg=None):
    """`(host, atlas, refusal)` off config.json."""
    cfg = paths.config() if cfg is None else cfg
    host = str(cfg.get("host") or "").strip()
    atlas = str(cfg.get("host_atlas") or DEFAULT_ATLAS).strip()
    if not host:
        return "", "", ("no `host` in %s: the Mac mini's tailnet name. "
                        "`bash scripts/setup-mac.sh --coding` asks for it"
                        % paths.CONFIG)
    if not HOST_RE.match(host):
        return "", "", "`host` %r in %s is not a host name" % (host, paths.CONFIG)
    if not ATLAS_RE.match(atlas):
        return "", "", ("`host_atlas` %r in %s is not a plain path"
                        % (atlas, paths.CONFIG))
    return host, atlas, ""


def pull(base, idents=(), cfg=None, say=print, run=subprocess.call):
    """Copy the Mac mini's ignored inputs into checkout `base`, for every
    subject or only `idents` (ids, slugs or paths `subjects.find` knows).
    Exit code: 0 copied, 1 refused or failed."""
    host, atlas, why = where(cfg)
    if why:
        say("board pull --materials: refused, " + why)
        return 1
    ids = []
    for ident in idents:
        found = subjects.find(ident, base)
        if not found:
            say("board pull --materials: refused, no subject %r here" % ident)
            return 1
        ids.append(found["id"])
    cmd = argv(host, atlas, base, ids)
    say("materials from %s:%s%s" % (host, atlas,
                                    (" for " + ", ".join(ids)) if ids else ""))
    try:
        code = run(cmd)
    except OSError as exc:
        say("board pull --materials: rsync did not run (%s)" % exc)
        return 1
    if code != 0:
        say("board pull --materials: rsync exited %s. Is Remote Login on at "
            "the Mac mini, and this laptop's key in its authorized_keys?"
            % code)
        return 1
    say("materials: up to date")
    return 0
