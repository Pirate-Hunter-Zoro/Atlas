"""What the machine's brew and tool upkeep last said, for the board.

`scripts/brew-upgrade.py` (the `atlas.brew-upgrade` LaunchAgent, setup's job,
not the board's) writes `brew.json` in the state directory, and
`scripts/tools.sh` and brew-upgrade.py write `tools.json` beside it
(`toolplan`). `lines` are the `brew:` and `tools:` sentences `/sync.json`
shows on home; `summary` and `tools_summary` are `board doctor`'s lines.
Neither reaches a tutor's brief. Runs under /usr/bin/python3: stdlib only.
"""

import json
import os
import sys
from datetime import datetime

from . import paths, toolplan

STALE_H = 72
TOOL_STALE_DAYS = 14


def _prefix():
    """Homebrew's prefix on this machine, or None."""
    for p in ("/opt/homebrew", "/usr/local"):
        if os.path.isfile(os.path.join(p, "bin", "brew")):
            return p
    return None


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
        if name.startswith("tool:"):
            out.append("tools: %s did not update: %s" % (name[5:], why))
        else:
            out.append("brew: %s did not upgrade: %s" % (name, why))
    for name, h in sorted((state.get("held") or {}).items()):
        h = h if isinstance(h, dict) else {}
        out.append("brew: %s %s -> %s is held: %s" % (
            name, h.get("installed") or "?", h.get("latest") or "?", h.get("why") or ""))
    for p in state.get("problems") or []:
        if isinstance(p, dict):
            out.append("brew: %s; %s" % (p.get("what"), p.get("fix")))
    cover = state.get("covered") if isinstance(state.get("covered"), dict) else {}
    if state.get("mode") == "defer" and cover.get("at"):
        out.append("brew: %s last succeeded %s, so atlas.brew-upgrade ran the brew "
                   "upgrade itself %s" % (
                       cover.get("for") or "the other upgrader",
                       _short(_when(cover.get("other_success")))
                       if _when(cover.get("other_success")) else "never",
                       _short(_when(cover["at"])) if _when(cover["at"]) else "?"))
    if state.get("mode") == "own":
        base = _when(state.get("last_success")) or _when(state.get("first_seen"))
        now = now or datetime.now()
        if base and (now - base).total_seconds() > STALE_H * 3600:
            out.append("brew: no successful upgrade since %s" % _short(base))
    return out


def lines(state_dir=None, now=None):
    """`lines_of` brew.json, then `tool_lines_of` tools.json; [] when there
    is neither. A tool brew.json names as failed is not named twice."""
    state = read(state_dir)
    out = []
    if state is not None:
        try:
            out = lines_of(state, now)
        except (AttributeError, TypeError, ValueError):
            out = []
    doc = read_tools(state_dir)
    if doc is not None:
        skip = set(k[5:] for k in ((state or {}).get("failed") or {})
                   if isinstance(k, str) and k.startswith("tool:"))
        try:
            out += tool_lines_of(doc, now, skip=skip)
        except (AttributeError, TypeError, ValueError):
            pass
    return out


def read_tools(state_dir=None):
    """tools.json as a dict, or None when it is missing or broken."""
    path = os.path.join(state_dir or paths.STATE_DIR, "tools.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def tool_lines_of(doc, now=None, skip=(), prefix=None):
    """The `tools:` sentences for tools.json: each failed tool (unless in
    `skip`), each one not updated in its T_STALE_DAYS, each conflict, each
    tool or Brewfile entry no longer declared but still installed, and each
    mise pin behind."""
    now = now or datetime.now()
    prefix = prefix if prefix is not None else _prefix()
    out = []
    for name, rec in sorted((doc.get("tools") or {}).items()):
        rec = rec if isinstance(rec, dict) else {}
        if rec.get("failed"):
            if name not in skip:
                out.append("tools: %s failed: %s" % (name, rec["failed"]))
            continue
        base = _when(rec.get("updated")) or _when(rec.get("seen"))
        try:
            days = int(rec.get("stale_days") or TOOL_STALE_DAYS)
        except (TypeError, ValueError):
            days = TOOL_STALE_DAYS
        if base and (now - base).total_seconds() > days * 86400:
            out.append("tools: %s not updated since %s (stale after %d days)%s"
                       % (name, _short(base), days,
                          "; %s" % rec["manual"] if rec.get("manual") else ""))
    for c in doc.get("conflicts") or []:
        if isinstance(c, dict):
            out.append("tools: %s is declared differently in %s; the copies must be "
                       "the same bytes" % (c.get("name"), " and ".join(c.get("paths") or [])))
    for name, rec in sorted((doc.get("left") or {}).items()):
        rec = rec if isinstance(rec, dict) else {}
        where = rec.get("dir") or ""
        if where and os.path.exists(os.path.join(where, rec.get("bin") or name)):
            out.append("tools: no longer declared: %s at %s" % (name, where))
    for entry in sorted(doc.get("left_brew") or {}):
        where = toolplan.brew_installed(entry, prefix)
        if where:
            out.append("tools: no longer declared: %s at %s"
                       % (entry.split('"')[1], where))
    for p in doc.get("pins") or []:
        if isinstance(p, dict):
            out.append("tools: pin behind: %s %s %s -> %s" % (
                p.get("subject"), p.get("tool"), p.get("pinned"), p.get("latest")))
    return out


def tools_summary(state_dir=None, now=None):
    """`board doctor`'s tools line, or None with no tools.json."""
    doc = read_tools(state_dir)
    if doc is None:
        return None
    said = tool_lines_of(doc, now)
    failed = len([1 for r in (doc.get("tools") or {}).values()
                  if isinstance(r, dict) and r.get("failed")])
    return "%d declared, %d failed, %d stale, %d no longer declared, %d pins behind" % (
        len(doc.get("tools") or {}), failed,
        len([l for l in said if " not updated since " in l]),
        len([l for l in said if l.startswith("tools: no longer declared: ")]),
        len([l for l in said if l.startswith("tools: pin behind: ")]))


def tools_doctor(state_dir=None, now=None, platform=None):
    """`board doctor`'s tools line, always. With no tools.json, what to do
    about it: on a Mac, run setup; off one, nothing, since setup skips the
    descriptors and mise there and never writes it."""
    said = tools_summary(state_dir, now)
    if said is not None:
        return said
    if (platform or sys.platform) == "darwin":
        return "no tools.json yet (bash scripts/setup.sh)"
    return "not kept here (the descriptors and mise are Mac only)"


def summary(state_dir=None):
    """One line for `board doctor`, or None with no brew.json."""
    state = read(state_dir)
    if state is None:
        return None
    problems = len(state.get("problems") or [])
    if state.get("mode") == "defer":
        cover = state.get("covered") if isinstance(state.get("covered"), dict) else {}
        when = _when(cover.get("at"))
        return "defers to %s%s; %d failed, %d problems" % (
            (state.get("deferred_to") or {}).get("label") or "another upgrader",
            ", covered for it %s (%s)" % (_short(when), state.get("last_result") or "?")
            if when else "", len(state.get("failed") or {}), problems)
    when = _when(state.get("last_attempt"))
    head = ("own, %s %s" % (state.get("last_result") or "?", _short(when))
            if when else "own, no run yet")
    return "%s; %d held, %d failed, %d problems" % (
        head, len(state.get("held") or {}), len(state.get("failed") or {}), problems)
