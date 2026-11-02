"""When DeepSeek says no more, and until when.

A spent balance or a rate limit is not a broken turn: nothing is wrong and the
same turn succeeds later. It is one record with an expiry (a limit cleared by
hand outlives itself), recognised by DeepSeek's own phrases; config.json's
`usage_limit_says` replaces them.
"""

import json
import os
import re
import time

from . import machine, paths


DEFAULT_USAGE_LIMIT_SAYS = (
    # An exhausted balance (HTTP 402).
    r"insufficient balance",
    r"\b402\b[^\n]{0,40}balance",
    # Too many requests (HTTP 429). They capture nothing on purpose: no reset
    # time comes with them, so `limit_window()` answers.
    r"\brate[ _-]?limit(?:_?error)?\b",
    r"\btoo many requests\b",
)

# How long a limit lasts when DeepSeek did not say: long enough not to
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
    """The record on disk, or {}. Never raises. A per-agent record left from
    when there were several assistants counts only its DeepSeek entry."""
    try:
        with open(LIMIT_RECORD, "r", encoding="utf-8") as fh:
            rec = json.load(fh) or {}
    except (OSError, ValueError):
        return {}
    if not isinstance(rec, dict):
        return {}
    if isinstance(rec.get("agents"), dict):
        rec = dict(rec, until=rec["agents"].get("deepseek") or 0)
    try:
        until = float(rec.get("until") or 0)
    except (TypeError, ValueError):
        return {}
    return {"node": rec.get("node"), "at": rec.get("at"), "until": until} \
        if until else {}


def mark_limited(until, node=None):
    """Record that DeepSeek has nothing left to spend on this machine, with
    the node, because the home directory is shared."""
    rec = {"node": node or machine.node_name(), "at": time.time(),
           "until": float(until)}
    os.makedirs(paths.STATE_DIR, exist_ok=True)
    tmp = LIMIT_RECORD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)
    os.replace(tmp, LIMIT_RECORD)
    return rec


def limit_record(now=None):
    """The live limit on this machine, `{until, node}`, or {}."""
    rec = _load()
    if not rec:
        return {}
    if rec.get("node") and rec["node"] != machine.node_name():
        return {}
    if rec["until"] <= (now or time.time()):
        return {}
    return {"until": rec["until"], "node": machine.node_name()}


def limited_until(now=None):
    """When DeepSeek's allowance comes back, or 0."""
    return float(limit_record(now).get("until") or 0)


def clear_limited():
    """Forget the limit (`board limit --clear`, or a turn that went through).
    True when there was one."""
    try:
        os.remove(LIMIT_RECORD)
        return True
    except OSError:
        return False
