"""Whether a turn can actually leave the building, and the exit node it leaves
through.

An exit node routes this machine's outbound traffic elsewhere; the tailnet is
untouched, so the iPad still reaches the board while a provider that blocks
VPN egress fails every turn silently. Which endpoints to probe is config,
because the board must not know which assistant drives it.
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
DEFAULT_EGRESS_PROBE = ("https://api.anthropic.com/v1/messages",)

# Exit nodes that once carried a real turn, tried first.
EGRESS_KNOWN_GOOD = os.path.join(paths.STATE_DIR, "egress-ok.json")


def egress_probe_urls(also=()):
    """The endpoints whose reachability settles anything here: config
    `egress_probe` wins; else the default agent's endpoint plus each installed,
    keyed provider's own (`also`, from `provider_probe_urls`), once each.
    """
    try:
        with open(paths.CONFIG, "r", encoding="utf-8") as fh:
            cfg = json.load(fh) or {}
    except (OSError, ValueError):
        cfg = {}
    urls = cfg.get("egress_probe")
    if isinstance(urls, str):
        urls = [urls]
    out = list(urls) if urls else list(DEFAULT_EGRESS_PROBE)
    for url in also or ():
        if url and url not in out:
            out.append(url)
    return tuple(out)


def egress_ok(timeout=12, urls=None, also=()):
    """Can a turn reach what it needs from here? Any HTTP answer, 401 and 405
    included, proves the path; only connection, DNS or timeout failures mean
    broken egress. `urls` asks about one provider, whose host a filter may drop
    while the rest of the internet answers (`agent_probe_urls`).
    """
    import urllib.error
    import urllib.request
    for url in (urls if urls is not None else egress_probe_urls(also)):
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
# A provider this machine cannot reach, recorded like `limits` records an
# exhausted allowance: per agent, with an expiry (filters lift), and with the
# node (the home directory is shared). Written by `board see` when a vision
# endpoint refuses a connection; read by `seeing.route` and the board, never
# by the turn resolver.
UNREACHABLE_RECORD = os.path.join(paths.STATE_DIR, "unreachable.json")

# How long a block is believed.
UNREACHABLE_WINDOW = 3600

# The window doubles on each repeat finding, up to this, because a firewall
# rule outlives every expiry. Strikes outlive the expiry; only a turn that
# goes through resets them.
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
    """How many times this provider has been stood down here, read past the
    expiry on purpose."""
    got = (_unreachable_load().get("agents") or {}).get(str(agent or ""))
    try:
        return int((got or {}).get("strikes") or 0)
    except (TypeError, ValueError):
        return 0


def _stand_down(agent, host, why, until=None, node=None):
    """Record that this agent cannot take a turn here, and until when. Merged,
    so a second dark provider never erases the first's expiry."""
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


def stood_down(agent, now=None):
    """`{host, why, until}` while this agent's host does not answer here, else
    None."""
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
    """A turn that went through proves the provider answers: drop the record
    and its strikes."""
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
    """Every peer offering to be an exit node, as name and address (`tailscale
    set --exit-node` refuses unknown bare hostnames)."""
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
    """Point this machine's egress at one exit node. Never turns one off: an
    exit node is somebody's deliberate choice, so on failure the original is
    restored and the fault reported."""
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
    """Find an exit node a turn can actually get out through. `(ok, detail)`.

    Known-good nodes first, then the rest, each proved by a probe; bounded to
    `tries`. If none works the original is restored, since the owner chose it.
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
