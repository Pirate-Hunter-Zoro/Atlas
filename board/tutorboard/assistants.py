"""Which assistants this machine has, for the board to offer.

The table is `recipes.listing`, read in-process: the provider, its fallback,
who takes the next turn, and every recipe with why it cannot take one. Cached
for a minute, because `unavailable` moves while the board is up (an allowance
runs out) and a person edits no file to change it; `forget` drops the cache
the moment `/default-agent` writes the setting.
"""

import time


TTL = 60.0
_CACHE = {"at": 0.0, "was": None}


def listing():
    """`{"default": provider, "machine": ..., "agents": [...]}`, or None.

    None only when the table could not be built, which the board draws as no
    chooser at all.
    """
    now = time.time()
    if _CACHE["was"] is not None and now - _CACHE["at"] <= TTL:
        return _CACHE["was"]
    from .agents import recipes

    try:
        got = recipes.listing()
    except Exception:                                        # noqa: BLE001
        got = None
    _CACHE["was"] = got
    _CACHE["at"] = now
    return got


def forget():
    """Drop the cache. For a test, and for a write that changed the setting."""
    _CACHE["at"] = 0.0
    _CACHE["was"] = None
