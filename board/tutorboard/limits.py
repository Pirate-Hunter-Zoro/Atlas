"""When the provider says no more, and until when.

A usage limit is not a broken turn: nothing is wrong and the same turn
succeeds later. It is recorded per agent with an expiry (a limit cleared by
hand outlives itself), and recognised by configured phrases, because the
board must not know which assistant drives it.
"""

import json
import os
import re
import time

from . import machine, paths


DEFAULT_USAGE_LIMIT_SAYS = (
    # Claude Code names the epoch second the allowance returns.
    r"usage limit reached\s*\|\s*(\d{9,})",
    r"usage limit reached",
    r"limit reached[^\n]{0,40}resets",
    r"\brate[ _-]?limit(?:_?error)?\b",
    r"\bquota (?:exceeded|exhausted)\b",
    r"\binsufficient[_ ]quota\b",
    # DeepSeek's exhausted balance (HTTP 402).
    r"insufficient balance",
    r"\b402\b[^\n]{0,40}balance",
    # Account-level ceilings (HTTP 429 org spend limit), which the patterns
    # above miss. They capture nothing on purpose: the reset is a wall-clock
    # time, and a group would be misread as an epoch; `limit_window()` answers.
    r"\bspend limit\b",
    r"\blimit resets\b",
)

# How long a limit lasts when the provider did not say: long enough not to
# thrash, short enough to recover the same evening.
DEFAULT_LIMIT_WINDOW = 3600

# The most we believe from a reset time we were handed.
LIMIT_CEILING = 24 * 3600

LIMIT_RECORD = os.path.join(paths.STATE_DIR, "limited.json")


def usage_limit_says():
    try:
        with open(paths.CONFIG, "r", encoding="utf-8") as fh:
            cfg = json.load(fh) or {}
    except (OSError, ValueError):
        cfg = {}
    says = cfg.get("usage_limit_says")
    if isinstance(says, str):
        says = [says]
    return tuple(says) if says else DEFAULT_USAGE_LIMIT_SAYS


def limit_window():
    try:
        with open(paths.CONFIG, "r", encoding="utf-8") as fh:
            cfg = json.load(fh) or {}
    except (OSError, ValueError):
        cfg = {}
    try:
        return max(60, int(cfg.get("usage_limit_window") or DEFAULT_LIMIT_WINDOW))
    except (TypeError, ValueError):
        return DEFAULT_LIMIT_WINDOW


def reads_as_usage_limit(text, now=None):
    """The epoch second the allowance is back if this failed turn ran out of
    it, else None. A captured number is the reset time unless it is more than
    a day out. Only asked of failed turns, since a lesson may say "rate
    limit" in earnest."""
    import re
    if not text:
        return None
    now = now or time.time()
    for pattern in usage_limit_says():
        try:
            m = re.search(pattern, text, re.IGNORECASE)
        except re.error:
            continue                 # a bad pattern in the config is not a crash
        if not m:
            continue
        when = None
        if m.groups() and m.group(1):
            try:
                when = float(m.group(1))
            except (TypeError, ValueError):
                when = None
        if when is None or not (now < when <= now + LIMIT_CEILING):
            when = now + limit_window()
        return when
    return None


def _load():
    """The record on disk, or {}. Never raises. A legacy single `{until,
    agent}` record becomes one entry under its agent (or ""), never a limit
    on every agent."""
    try:
        with open(LIMIT_RECORD, "r", encoding="utf-8") as fh:
            rec = json.load(fh) or {}
    except (OSError, ValueError):
        return {}
    if not isinstance(rec, dict):
        return {}
    if not isinstance(rec.get("agents"), dict):
        try:
            until = float(rec.get("until") or 0)
        except (TypeError, ValueError):
            return {}
        rec = {"node": rec.get("node"), "at": rec.get("at"),
               "agents": {str(rec.get("agent") or ""): until}} if until else {}
    return rec


def mark_limited(until, agent=None, node=None):
    """Record that this agent has nothing left to spend on this machine. Per
    agent, with the node (the home directory is shared), merged so one
    provider's ceiling never erases another's expiry."""
    node = node or machine.node_name()
    rec = _load()
    if rec.get("node") and rec["node"] != node:
        rec = {}                      # somebody else's machine; start our own
    agents = dict(rec.get("agents") or {})
    agents[str(agent or "")] = float(until)
    rec = {"node": node, "at": time.time(), "agents": agents}
    os.makedirs(paths.STATE_DIR, exist_ok=True)
    tmp = LIMIT_RECORD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)
    os.replace(tmp, LIMIT_RECORD)
    return rec


def limited_agents(now=None):
    """`{agent: until}` for every live limit on this machine; "" for a record
    that named no agent."""
    rec = _load()
    if not rec:
        return {}
    if rec.get("node") and rec["node"] != machine.node_name():
        return {}
    now = now or time.time()
    out = {}
    for name, until in (rec.get("agents") or {}).items():
        try:
            until = float(until)
        except (TypeError, ValueError):
            continue
        if until > now:
            out[str(name)] = until
    return out


def limit_record(agent=None, now=None):
    """The live limit on this machine, or {}: the agent's own, or bare the
    longest-lasting (what `/health` and `board limit` want), with `until`
    and `agent` fields."""
    live = limited_agents(now)
    if not live:
        return {}
    if agent is not None:
        until = live.get(str(agent))
        if not until:
            return {}
        return {"until": until, "agent": str(agent),
                "node": machine.node_name(), "agents": live}
    name, until = max(live.items(), key=lambda kv: kv[1])
    return {"until": until, "agent": name or None,
            "node": machine.node_name(), "agents": live}


def limited_until(agent=None, now=None):
    """When this agent's allowance comes back, or 0; bare, the machine-level
    answer `/health` and `board limit` use."""
    rec = limit_record(agent, now)
    return float(rec.get("until") or 0) if rec else 0.0


def clear_limited(agent=None):
    """Forget the limit: named, that agent's; bare, all of them
    (`board limit --clear`)."""
    if agent is not None:
        live = limited_agents()
        if str(agent) not in live:
            return False
        live.pop(str(agent), None)
        tmp = LIMIT_RECORD + ".tmp"
        os.makedirs(paths.STATE_DIR, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"node": machine.node_name(), "at": time.time(),
                       "agents": live}, fh, indent=2)
        os.replace(tmp, LIMIT_RECORD)
        return True
    try:
        os.remove(LIMIT_RECORD)
        return True
    except OSError:
        return False
