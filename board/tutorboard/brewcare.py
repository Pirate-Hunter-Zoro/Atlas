"""What the machine's brew upkeep last said, for the board.

`scripts/brew-upgrade.py` (the `atlas.brew-upgrade` LaunchAgent, setup's job,
not the board's) writes `brew.json` in the state directory. `lines` are the
`brew:` sentences `/relay.json` shows; `summary` is `board doctor`'s one line.
Neither reaches a tutor's brief. Runs on the cluster's python3 (3.7) and under
/usr/bin/python3: stdlib only.
"""

import json
import os
from datetime import datetime

from . import paths

STALE_H = 72


def read(state_dir=None):
    """brew.json as a dict, or None when it is missing or broken."""
    path = os.path.join(state_dir or paths.STATE_DIR, "brew.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _when(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def _short(when):
    return "%s %d %s" % (when.strftime("%b"), when.day, when.strftime("%H:%M"))


def lines_of(state, now=None):
    """The `brew:` sentences for one state dict: failures, holds, problems,
    then, in own mode, a success older than STALE_H hours."""
    out = []
    for name, why in sorted((state.get("failed") or {}).items()):
        out.append("brew: %s did not upgrade: %s" % (name, why))
    for name, h in sorted((state.get("held") or {}).items()):
        h = h if isinstance(h, dict) else {}
        out.append("brew: %s %s -> %s is held: %s" % (
            name, h.get("installed") or "?", h.get("latest") or "?", h.get("why") or ""))
    for p in state.get("problems") or []:
        if isinstance(p, dict):
            out.append("brew: %s; %s" % (p.get("what"), p.get("fix")))
    if state.get("mode") == "own":
        base = _when(state.get("last_success")) or _when(state.get("first_seen"))
        now = now or datetime.now()
        if base and (now - base).total_seconds() > STALE_H * 3600:
            out.append("brew: no successful upgrade since %s" % _short(base))
    return out


def lines(state_dir=None, now=None):
    """`lines_of` brew.json; [] when there is none."""
    state = read(state_dir)
    if state is None:
        return []
    try:
        return lines_of(state, now)
    except (AttributeError, TypeError, ValueError):
        return []


def summary(state_dir=None):
    """One line for `board doctor`, or None with no brew.json."""
    state = read(state_dir)
    if state is None:
        return None
    problems = len(state.get("problems") or [])
    if state.get("mode") == "defer":
        return "defers to %s; %d problems" % (
            (state.get("deferred_to") or {}).get("label") or "another upgrader",
            problems)
    when = _when(state.get("last_attempt"))
    head = ("own, %s %s" % (state.get("last_result") or "?", _short(when))
            if when else "own, no run yet")
    return "%s; %d held, %d failed, %d problems" % (
        head, len(state.get("held") or {}), len(state.get("failed") or {}), problems)
