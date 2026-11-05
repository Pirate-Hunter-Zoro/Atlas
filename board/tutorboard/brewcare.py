"""What the machine's upkeep last said, for the board.

upkeep (`upkeep/upkeep.py`, the `com.mikeyferguson.upkeep` LaunchAgent, not
the board's) writes `state.json` in its own state directory
($UPKEEP_STATE_DIR, else ~/.local/state/upkeep). Atlas's hook,
`scripts/brew-upgrade.py`, writes `atlas-upkeep.json` in the board's state
directory, and `scripts/tools.sh` and the hook write `tools.json` beside it
(`toolplan`). `lines` are the `upkeep:`, `atlas:` and `tools:` sentences
`/sync.json` shows on home; `summary` and `tools_summary` are `board
doctor`'s lines. Neither reaches a tutor's brief. Runs under
/usr/bin/python3: stdlib only.
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


def upkeep_dir():
    return os.environ.get("UPKEEP_STATE_DIR") or os.path.join(
        os.path.expanduser("~"), ".local", "state", "upkeep")


def _json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def read_upkeep(where=None):
    """upkeep's state.json as a dict, or None when it is missing or broken."""
    return _json(os.path.join(where or upkeep_dir(), "state.json"))


def read(state_dir=None):
    """The hook's atlas-upkeep.json as a dict, or None."""
    return _json(os.path.join(state_dir or paths.STATE_DIR, "atlas-upkeep.json"))


def _when(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def _short(when):
    return "%s %d %s" % (when.strftime("%b"), when.day, when.strftime("%H:%M"))


def upkeep_lines_of(state, now=None):
    """upkeep's sentences: failures, holds, problems, then a success older
    than STALE_H hours. Repo hooks' lines are each repo's to show."""
    out = []
    for name, why in sorted((state.get("failed") or {}).items()):
        out.append("upkeep: %s failed: %s" % (name, why))
    for name, h in sorted((state.get("held") or {}).items()):
        h = h if isinstance(h, dict) else {}
        out.append("upkeep: %s %s -> %s is held: %s" % (
            name, h.get("installed") or "?", h.get("latest") or "?", h.get("why") or ""))
    for line in state.get("problems") or []:
        if isinstance(line, str):
            out.append("upkeep: %s" % line)
    base = _when(state.get("last_success")) or _when(state.get("first_seen"))
    now = now or datetime.now()
    if base and (now - base).total_seconds() > STALE_H * 3600:
        out.append("upkeep: no successful run since %s" % _short(base))
    return out


def lines_of(state, now=None):
    """The hook's sentences: each failed tool, then each problem."""
    out = []
    for name, why in sorted((state.get("failed") or {}).items()):
        if name.startswith("tool:"):
            out.append("tools: %s did not update: %s" % (name[5:], why))
        else:
            out.append("atlas: %s failed: %s" % (name, why))
    for p in state.get("problems") or []:
        if isinstance(p, dict):
            out.append("atlas: %s; %s" % (p.get("what"), p.get("fix")))
    return out


def lines(state_dir=None, now=None, upkeep=None):
    """upkeep's lines, the hook's, then `tool_lines_of` tools.json; [] when
    there is none of them. A tool the hook names as failed is not named
    twice."""
    out = []
    up = read_upkeep(upkeep)
    if up is not None:
        try:
            out += upkeep_lines_of(up, now)
        except (AttributeError, TypeError, ValueError):
            pass
    state = read(state_dir)
    if state is not None:
        try:
            out += lines_of(state, now)
        except (AttributeError, TypeError, ValueError):
            pass
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
    Brewfile line the union refused (`refused_brew`, once per file and
    reason), each tool or Brewfile entry no longer declared but still
    installed, and each mise pin behind."""
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
    refusals = []
    for r in doc.get("refused_brew") or []:
        if isinstance(r, dict):
            said = "tools: refused Brewfile line %s: %s" % (
                toolplan._printable(str(r.get("file") or "?")),
                toolplan._printable(str(r.get("why") or "refused")))
            if said not in refusals:
                refusals.append(said)
    out += refusals
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


def summary(state_dir=None, upkeep=None):
    """`board doctor`'s upkeep line: upkeep's last run, then the hook's."""
    up = read_upkeep(upkeep)
    if up is None or not up.get("last_attempt"):
        head = "no upkeep run yet (bash upkeep/setup-mac.sh)"
    else:
        when = _when(up.get("last_attempt"))
        head = "%s %s; %d held, %d failed, %d problems" % (
            up.get("last_result") or "?", _short(when) if when else "?",
            len(up.get("held") or {}), len(up.get("failed") or {}),
            len(up.get("problems") or []))
        if up.get("brew_by") and up.get("brew_by") != "upkeep":
            head += "; brew left to %s" % up["brew_by"]
    state = read(state_dir)
    if state is None:
        return head + "; no Atlas hook run yet"
    when = _when(state.get("toolchain_success"))
    return "%s; Atlas toolchain %s, %d failed, %d problems" % (
        head, _short(when) if when else "never", len(state.get("failed") or {}),
        len(state.get("problems") or []))
