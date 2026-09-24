"""Whether a turn can actually leave the building, and the exit node it leaves
through.

An exit node routes all of this machine's outbound traffic somewhere else.
Tailnet traffic is untouched, so the iPad reaches the board either way -- what
changes is whether the tutor can reach its model.
"""

import json
import os
import subprocess
import time
import urllib.error
import urllib.request

from .. import paths
from . import tailscale


# ---------------------------------------------------------------------------
# Exit nodes, and whether a turn can actually leave the building
# ---------------------------------------------------------------------------
# An exit node routes ALL of this machine's outbound traffic through somewhere
# else. Tailnet traffic is untouched, so the iPad reaches the board exactly as
# before and nothing about serving a lesson notices -- but every request the
# tutor makes to its provider now egresses from another country, and commercial
# VPN egress is precisely the sort of address a provider geo-blocks, rate-limits
# or challenges. The failure is total and looks like nothing: turns fail, the
# board shows a tutor listening, and the log fills with errors nobody reads.
#
# WHICH endpoints a turn needs is configuration, not code. The board is not
# allowed to know which assistant is driving it -- that is the same rule that
# makes a model a command recipe rather than a field -- so this is a list of URLs
# in the config with a default that happens to suit the default agent. Point it
# somewhere else and nothing here changes.
DEFAULT_EGRESS_PROBE = ("https://api.anthropic.com/v1/messages",)

# Exit nodes known to have carried a real turn. Tried first on a rotation,
# because the only evidence that an exit node works is that it once did.
EGRESS_KNOWN_GOOD = os.path.join(paths.STATE_DIR, "egress-ok.json")


def egress_probe_urls():
    """The endpoints whose reachability actually settles anything here.

    `egress_probe` in the config wins, always -- the board is not allowed to know
    which assistant is driving it, and a list of URLs is how that stays true.

    With nothing in the config, it is the endpoint below, which is the one the
    default agent opens a connection to. Point it somewhere else the moment the
    tutor does: a probe asking after a host the tutor never talks to answers a
    question about somebody else's server.
    """
    try:
        with open(paths.CONFIG, "r", encoding="utf-8") as fh:
            cfg = json.load(fh) or {}
    except (OSError, ValueError):
        cfg = {}
    urls = cfg.get("egress_probe")
    if isinstance(urls, str):
        urls = [urls]
    if urls:
        return tuple(urls)
    return DEFAULT_EGRESS_PROBE


def egress_ok(timeout=12, urls=None):
    """Can a turn reach what it needs from here?

    ANY http answer counts, including 401 and 405. We are asking whether the
    packets arrive, not whether we are allowed in -- an unauthenticated probe
    that gets a 401 has proved the whole path. Only a connection failure, a DNS
    failure or a timeout means the egress is broken, which is exactly the shape a
    bad exit node produces.

    `urls` asks about ONE PROVIDER rather than about the machine, and the two
    questions have different answers: a filter that drops one provider's
    hostname leaves every other host on the internet reachable, so the
    machine-wide probe says yes while the turn that just failed could not open a
    socket. The recipe names its own endpoint; see `agent_probe_urls` in
    `bin/tutor`.
    """
    import urllib.error
    import urllib.request
    for url in (urls if urls is not None else egress_probe_urls()):
        req = urllib.request.Request(url, data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=timeout)
            return True
        except urllib.error.HTTPError:
            return True                      # it answered; that is the question
        except (urllib.error.URLError, OSError):
            continue
    return False



# ---------------------------------------------------------------------------
# A provider this machine cannot reach, and until when
# ---------------------------------------------------------------------------
# A blocked hostname is not a broken agent and not a broken machine. The
# executable is here, the key is here, the allowance is intact, and every other
# host on the internet answers -- one provider's name is dropped on the wire, so
# every turn that recipe takes dies the same way and the board has no word for
# it. That is the failure this records, in the same shape `limits` records an
# exhausted allowance and for the same reasons: per AGENT, because one blocked
# provider says nothing about the next; with an EXPIRY, because a filter that
# was lifted must not demote a recipe for ever; and with the NODE, because the
# home directory is shared between compute nodes and a block seen on the
# allocation that ended yesterday is not this machine's news.
#
# Written from a turn that has ALREADY failed, and from the one other moment
# worth a round trip: a sitting being pointed at a recipe with a provider of its
# own, which is rare, deliberate, and the moment a dead provider costs a student
# a three-minute turn that writes nothing. Not before every card -- that would
# put a round trip to the internet in front of every answer to ask a question
# whose answer is almost always yes. See `probe_before_turn` in `bin/tutor`.
UNREACHABLE_RECORD = os.path.join(paths.STATE_DIR, "unreachable.json")

# How long a block is believed for. One failed turn buys the finding, and one
# more failed turn is what every expiry costs to rediscover.
UNREACHABLE_WINDOW = 3600

# AND THE WINDOW DOUBLES EACH TIME THE SAME PROVIDER IS FOUND DARK AGAIN, up to
# this. A fixed hour is right for a filter that lifts by itself and wrong for one
# that does not: a firewall rule outlives every expiry, so the flat window costs
# a dead turn an hour for ever, each one a student waiting three minutes for
# nothing. The strike count is kept past the expiry -- that is the whole of what
# makes the second finding cheaper than the first -- and only a turn that goes
# through resets it, because that is the only evidence the host answers.
UNREACHABLE_MAX = 24 * 3600


def _unreachable_load():
    """The record on disk, or {}. Never raises: a lesson does not stop here."""
    try:
        with open(UNREACHABLE_RECORD, "r", encoding="utf-8") as fh:
            rec = json.load(fh) or {}
    except (OSError, ValueError):
        return {}
    if not isinstance(rec, dict) or not isinstance(rec.get("agents"), dict):
        return {}
    from .. import machine
    if rec.get("node") and rec["node"] != machine.node_name():
        return {}
    return rec


def _strikes(agent):
    """How many times this provider has already been stood down here.

    Read past the expiry on purpose: the count is what makes each rediscovery
    cheaper than the last, and an entry whose window has run out is exactly the
    one about to be written again.
    """
    got = (_unreachable_load().get("agents") or {}).get(str(agent or ""))
    try:
        return int((got or {}).get("strikes") or 0)
    except (TypeError, ValueError):
        return 0


def _stand_down(agent, host, why, until=None, node=None):
    """Write down that this AGENT cannot take a turn here, and until when.

    Merged rather than replaced, for the reason `limits.mark_limited` is: a
    second provider going dark must not erase the first one's expiry and send
    the daemon climbing home to something that is still unreachable.
    """
    from .. import machine
    node = node or machine.node_name()
    rec = _unreachable_load()
    if rec.get("node") and rec["node"] != node:
        rec = {}
    strikes = _strikes(agent) + 1
    if until is None:
        until = time.time() + min(UNREACHABLE_WINDOW * (2 ** (strikes - 1)),
                                  UNREACHABLE_MAX)
    agents = dict(rec.get("agents") or {})
    agents[str(agent or "")] = {"host": str(host or ""),
                                "why": str(why or ""),
                                "strikes": strikes,
                                "until": float(until)}
    rec = {"node": node, "at": time.time(), "agents": agents}
    try:
        os.makedirs(paths.STATE_DIR, exist_ok=True)
        tmp = UNREACHABLE_RECORD + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=2)
        os.replace(tmp, UNREACHABLE_RECORD)
    except OSError:
        pass
    return rec


def mark_unreachable(agent, host, until=None, node=None):
    """Write down that this AGENT's provider does not answer from this machine."""
    return _stand_down(agent, host, "", until=until, node=node)


def mark_failing(agent, why, until=None, node=None):
    """Write down that this AGENT's turns fail here for a reason that is not the network.

    A renamed model, a rejected key, a provider answering 404 to every request:
    the host answers, so nothing above notices, and `choose_agent` hands the next
    turn straight back to a recipe that cannot write a card. Every student
    message then costs a full failed turn, for ever. This is the same climb-down
    as a dark host, bought by repeated failure rather than by a probe, and `why`
    is the provider's own sentence so the board can say what is wrong.
    """
    return _stand_down(agent, "", why, until=until, node=node)


def stood_down(agent, now=None):
    """`{host, why, until}` while this agent cannot take a turn here, else None.

    Both kinds of stand-down: `host` is set when the provider's name does not
    answer, `why` when its turns fail for a reason the network is innocent of.
    """
    got = (_unreachable_load().get("agents") or {}).get(str(agent or ""))
    if not isinstance(got, dict):
        return None
    try:
        until = float(got.get("until") or 0)
    except (TypeError, ValueError):
        return None
    if until <= (now or time.time()):
        return None
    return {"host": got.get("host") or "", "why": got.get("why") or "",
            "until": until}


def unreachable(agent, now=None):
    """`{host, until}` while this agent's provider is known not to answer, else None."""
    got = stood_down(agent, now)
    return {"host": got["host"], "until": got["until"]} if got and got["host"] else None


def clear_unreachable(agent):
    """A turn that went through is proof the provider answers, whatever this says.

    A measurement beats a record: the expiry above is a guess about when a
    filter might lift, and a card written through the provider settles it. The
    strike count goes with it, so a provider that comes back starts its next bad
    evening at one hour rather than at a day.
    """
    rec = _unreachable_load()
    agents = dict(rec.get("agents") or {})
    if agents.pop(str(agent or ""), None) is None:
        return
    rec["agents"] = agents
    try:
        tmp = UNREACHABLE_RECORD + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=2)
        os.replace(tmp, UNREACHABLE_RECORD)
    except OSError:
        pass


def exit_node(status=None):
    """The exit node this machine is using, or None. Name and address."""
    st = status if status is not None else tailscale._ts_status()
    for peer in (st.get("Peer") or {}).values():
        if peer.get("ExitNode"):
            ips = peer.get("TailscaleIPs") or []
            return {"name": peer.get("HostName") or peer.get("DNSName", "").split(".")[0],
                    "ip": ips[0] if ips else None}
    return None


def exit_node_options(status=None):
    """Every peer offering to be an exit node, as name and address.

    The address is what matters: `tailscale set --exit-node` refuses a bare
    hostname it does not recognise, and an IP is never ambiguous.
    """
    st = status if status is not None else tailscale._ts_status()
    out = []
    for peer in (st.get("Peer") or {}).values():
        if not peer.get("ExitNodeOption"):
            continue
        ips = peer.get("TailscaleIPs") or []
        if not ips:
            continue
        out.append({"name": peer.get("HostName") or peer.get("DNSName", "").split(".")[0],
                    "ip": ips[0], "online": bool(peer.get("Online"))})
    return sorted(out, key=lambda p: p["name"])


def set_exit_node(ip):
    """Point this machine's egress at one exit node. Never turns one off.

    Disabling would be the obvious repair and it is the wrong one: somebody
    running everything through an exit node is doing it on purpose, and silently
    dropping back to the bare connection would expose the address they arranged
    not to expose in order to fix a tutoring session. If nothing works, the
    original is put back and the fault is reported.
    """
    prefix, _ = tailscale.tailscale_cli()
    if not prefix or not ip:
        return False
    import subprocess
    try:
        p = subprocess.run(prefix + ["set", "--exit-node=" + ip],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=40)
        return p.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _known_good():
    try:
        with open(EGRESS_KNOWN_GOOD, "r", encoding="utf-8") as fh:
            got = json.load(fh)
        return [x for x in got if isinstance(x, str)] if isinstance(got, list) else []
    except (OSError, ValueError):
        return []


def remember_good_exit_node(ip):
    if not ip:
        return
    seen = [x for x in _known_good() if x != ip]
    seen.insert(0, ip)
    try:
        os.makedirs(paths.STATE_DIR, exist_ok=True)
        tmp = EGRESS_KNOWN_GOOD + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(seen[:12], fh)
        os.replace(tmp, EGRESS_KNOWN_GOOD)
    except OSError:
        pass


def rotate_exit_node(tries=4, log=None, settle=4.0):
    """Find an exit node a turn can actually get out through.

    Returns (ok, detail). Only ever called when egress is already broken, so the
    machine starts in a state nobody wants to keep.

    Order: exit nodes that have carried a turn before, then the rest. Each one is
    tried and then PROVED, because the only way to know whether a provider
    answers from a given country is to ask from it. Bounded, because a rotation
    that walks four hundred Mullvad endpoints is an outage of its own.

    If nothing works the original is restored: a machine on a broken exit node
    the person chose is a better place to leave them than a machine on a random
    one they did not.
    """
    import time as _t

    def note(msg):
        if log:
            log(msg)

    status = tailscale._ts_status()
    was = exit_node(status)
    if not was:
        note("no exit node in use; the egress fault is not one this can repair")
        return False, "no exit node"

    options = [o for o in exit_node_options(status)
               if o["online"] and o["ip"] != was["ip"]]
    if not options:
        return False, "no other exit node is available"

    good = _known_good()
    options.sort(key=lambda o: good.index(o["ip"]) if o["ip"] in good else len(good))

    for cand in options[:max(1, tries)]:
        note("egress: trying exit node %s" % cand["name"])
        if not set_exit_node(cand["ip"]):
            continue
        _t.sleep(settle)                  # the route does not move instantly
        if egress_ok():
            remember_good_exit_node(cand["ip"])
            note("egress: %s works; staying there" % cand["name"])
            return True, cand["name"]

    set_exit_node(was["ip"])
    note("egress: no exit node tried could reach it; put %s back" % was["name"])
    return False, "tried %d, none worked" % min(len(options), max(1, tries))
