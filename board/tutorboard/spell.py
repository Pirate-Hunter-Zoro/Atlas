"""How this side spells a §2.1 address. One speller, and this is it.

`web/address.js` is the grammar: it parses, it spells, and `Address.format` is
the only thing on the board that builds an address. This is the same speller for
the half of the system that is Python -- a meeting frame pointing at a box, a
card handing the work over to another one -- and it exists as a module of its own
so that there is one of it rather than one per caller.

THERE IS ONE GRAMMAR AND THIS OBEYS IT. A second speller is a second set of
links that resolve slightly differently, and the whole point of the grammar is
that a note written in March opens in September or says plainly that it cannot.
"""

import os
import re

from . import atlas


_SAFE = re.compile(r"^[A-Za-z0-9._~-]$")


def enc(s):
    """Percent-encoding, the same subset `encodeURIComponent` leaves alone."""
    out = []
    for ch in str(s):
        if _SAFE.match(ch):
            out.append(ch)
        else:
            out.extend("%%%02X" % b for b in ch.encode("utf-8"))
    return "".join(out)


def spell(ws_id, surface=None, **rest):
    """One address, in the §2.1 grammar, or "" for a workspace with no family.

    `ws_id` is `family/name` -- what `atlas.identify` answers. A bare name means
    a directory sitting in no family, which has no address at all; "" is the
    honest answer and is never written into a card.
    """
    fam, _, name = str(ws_id or "").partition("/")
    if not fam or not name:
        return ""
    bits = ["#/w/" + enc(fam) + "/" + enc(name)]
    if surface == "node":
        bits.append("/node/" + rest["node"])
    elif surface == "code":
        segs = [enc(s) for s in str(rest["path"]).split("/")]
        tail = "/".join(segs)
        if rest.get("symbol"):
            tail += "::" + rest["symbol"]
        bits.append("/code/" + tail)
    return "".join(bits)


def here(root, surface=None, **rest):
    """The same, for a repository ROOT rather than an id already resolved.

    `atlas.identify` rather than `atlas.find`: a board running in a workspace
    that has since been renamed still has to be able to say where it is.
    """
    if not root:
        return ""
    try:
        return spell(atlas.identify(os.path.realpath(root)), surface, **rest)
    except Exception:                                        # noqa: BLE001
        return ""
