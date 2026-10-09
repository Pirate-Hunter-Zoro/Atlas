"""Which assistant takes a turn: the recipes, this machine's config, and the choice.

A provider is a recipe plus a key. `DEFAULT_CONFIG` is the built-in table;
`load_config` lays this machine's `config.json` over it. The config names one
`provider`, one `fallback` and a `vision_agent`, and nothing else chooses: no
session, subject or command line overrides it. `resolve` says who takes the
next turn, `unavailable` why a recipe cannot, and `listing` is what the board
draws.
"""

import json
import os
import shutil
import sys
import time

from tutorboard import keys, limits, machine, subjects

CONFIG_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")),
    "tutor-board")
CONFIG = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "courses_dir": subjects.root(),
    "agents": {
        "claude": {
            "cmd": ["claude"], "prompt": "argv", "label": "Claude",
            "headless_first": ["claude", "-p", "{prompt}"],
            # The brief and the recap ride here (`runner.loop.handed`); any
            # recipe without this field reads them prepended to its prompt.
            "system_args": ["--append-system-prompt", "{system}"],
            "usage": "claude-json",
            "usage_args": ["--output-format", "json"],
            "extra_args": [],
            "vision": {"cmd": ["claude", "-p", "{prompt}"],
                       "model": "whatever this machine's Claude Code settings "
                                "select",
                       "sighted": True},
        },
        # A model rename is two strings, `-m` and `vision.model`. Re-check the
        # id at huggingface.co `deepseek-ai/DeepSeek-V4.1-Flash`, at
        # `github.com/deepseek-ai/deepseek-recipe`, or with
        # `opencode models deepseek`.
        "deepseek": {
            "cmd": ["opencode", "--pure", "-m", "deepseek/deepseek-flash"],
            "label": "DeepSeek",
            "prompt": "--prompt",
            "headless_first": ["opencode", "--pure", "run", "--auto",
                               "-m", "deepseek/deepseek-flash", "{prompt}"],
            "usage": "opencode-json",
            "usage_args": ["--format", "json"],
            "extra_args": [],
            "needs_key": "DEEPSEEK_API_KEY",
            "env": {
                "DEEPSEEK_API_KEY": "{DEEPSEEK_API_KEY}",
                "OPENCODE_CONFIG_CONTENT": json.dumps({
                    "small_model": "deepseek/deepseek-flash",
                    "permission": {"skill": "deny"},
                    "provider": {"deepseek": {"options": {
                        "apiKey": "{env:DEEPSEEK_API_KEY}"}}}}),
            },
            "egress_probe": ["https://api.deepseek.com/chat/completions"],
            "vision": {
                "endpoint": "https://api.deepseek.com/v1/chat/completions",
                "model": "deepseek-flash",
                "needs_key": "DEEPSEEK_API_KEY",
                "sighted": True,
            },
            "prices": {
                "peak": {"in": 0.30, "cache_write": 0.30,
                         "cache_read": 0.006, "out": 1.20},
                "off": {"in": 0.15, "cache_write": 0.15,
                        "cache_read": 0.003, "out": 0.60},
                "peak_utc": [["01:00", "04:00"], ["06:00", "10:00"]],
                "peak_weekdays_only": True,
            },
        },
        "codex": {
            "cmd": ["codex"], "prompt": "argv", "label": "Codex",
            "headless_first": ["codex", "exec",
                               "--dangerously-bypass-approvals-and-sandbox",
                               "{prompt}"],
            "usage": "codex-jsonl",
            "usage_args": ["--json"],
            "egress_probe": ["https://chatgpt.com/backend-api/codex/responses"],
            "env": {},
        },
    },
    # THE ONE PROVIDER SETTING: who takes every turn, who takes it when that
    # one cannot (missing binary, missing key, usage limit), and who reads an
    # image for a recipe with no eyes. `/default-agent` writes `provider`.
    "provider": "claude",
    "fallback": "codex",
    "vision_agent": "claude",
    "headless_timeout": 900,
    "doing_timeout": 3600,
    "handoff_timeout": 600,
    "quota_tokens": None,
}

def load_config():
    """The defaults above, with this machine's config file laid over them.
    `agents` merges one level deeper (`"replace": true` replaces an entry).
    A missing or unreadable file is the defaults; nothing is written.
    `default_agent`, `only_agent` and `session_turns` are ignored.
    """
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        with open(CONFIG, "r", encoding="utf-8") as fh:
            user = json.load(fh) or {}
    except (OSError, ValueError):
        user = {}
    if not isinstance(user, dict):
        user = {}
    for k, v in user.items():
        if k == "agents" and isinstance(v, dict):
            for name, spec in v.items():
                have = cfg["agents"].get(name)
                if isinstance(spec, dict) and isinstance(have, dict) \
                        and not spec.get("replace"):
                    merged = dict(have)
                    merged.update(spec)
                    cfg["agents"][name] = merged
                else:
                    cfg["agents"][name] = spec
        elif k not in ("default_agent", "only_agent", "session_turns"):
            cfg[k] = v

    # A `courses_dir` that does not hold the board's own package is not an
    # Atlas root, so it is dropped for the one this package derives.
    said = cfg.get("courses_dir")
    if said:
        said = os.path.expanduser(said)
        if not os.path.isdir(os.path.join(said, "board", "tutorboard")):
            cfg["courses_dir"] = subjects.root()
    return cfg


def this_host():
    """What this machine calls itself. One place decides; see boardlib."""
    return machine.node_name()

def missing_command(recipe):
    """The recipe's executable when this machine lacks it (the resolver then
    hands its turns to the fallback); a script agent never lacks one."""
    exe = (recipe or [None])[0]
    if not exe or os.path.basename(exe) == os.path.basename(sys.executable):
        return None
    return None if shutil.which(exe) else exe

def agent_label(cfg, name):
    """What a person calls a recipe: its `label`, or its name."""
    return ((cfg.get("agents") or {}).get(name) or {}).get("label") or name


def agent_probe_urls(spec):
    """The endpoints this recipe's turns open (e.g. via `ANTHROPIC_BASE_URL`),
    or None for the default agent's own, since a filter may drop one host
    while the rest of the internet answers."""
    urls = (spec or {}).get("egress_probe")
    if isinstance(urls, str):
        urls = [urls]
    return [u for u in urls if u] if urls else None


def provider_probe_urls(cfg):
    """Every configured provider's endpoints for the machine-wide probe: only
    recipes whose command and key are both here."""
    out = []
    for name in sorted(cfg.get("agents") or {}):
        spec = cfg["agents"][name] or {}
        if missing_command(spec.get("cmd")) or keys.unkeyed(spec):
            continue
        for url in agent_probe_urls(spec) or ():
            if url not in out:
                out.append(url)
    return out


def probe_host(urls):
    """The hostname a probe list is about, for saying which one went dark."""
    try:
        from urllib.parse import urlsplit
        return urlsplit((urls or [""])[0]).hostname or ""
    except (ValueError, IndexError):
        return ""


# ---------------------------------------------------------------------------
# THE RESOLVER: the provider, else the one fallback
# ---------------------------------------------------------------------------
def provider(cfg):
    """The name the config gives every turn: `provider`, else claude."""
    said = (cfg or {}).get("provider")
    return said.strip() if isinstance(said, str) and said.strip() else "claude"


def fallback(cfg):
    """The one recipe that takes a turn the provider cannot, or None."""
    said = (cfg or {}).get("fallback")
    return said.strip() if isinstance(said, str) and said.strip() else None


def in_fence(cfg, name):
    """The refusal for an in-fence recipe (`private`), else None: only it
    reads phi and it runs only as a cluster relay task, never as a hosted
    turn, fallback or vision route here."""
    spec = ((cfg or {}).get("agents") or {}).get(name)
    if isinstance(spec, dict) and spec.get("private"):
        return ("'%s' is an in-fence model: only it reads phi, and it never "
                "takes a turn here" % name)
    return None


def unavailable(cfg, name, now=None):
    """Why `name` cannot take a turn on this machine now, or None, from disk
    alone: no recipe, in-fence, no headless recipe, missing binary or key, or
    a spent allowance (`limits.mark_limited`)."""
    spec = ((cfg or {}).get("agents") or {}).get(name)
    if not isinstance(spec, dict):
        return "there is no recipe called '%s'" % name
    fenced = in_fence(cfg, name)
    if fenced:
        return fenced
    if not (spec.get("headless_first") or spec.get("headless")):
        return "'%s' has no headless recipe" % name
    gone = missing_command(spec.get("cmd"))
    if gone:
        return "`%s` is not on the path here" % gone
    need = keys.unkeyed(spec)
    if need:
        return "%s is not in %s" % (need, keys.store())
    until = limits.limited_until(name, now)
    if until:
        return ("its allowance is gone until %s"
                % time.strftime("%H:%M", time.localtime(until)))
    return None


def resolve(cfg, now=None):
    """Who takes the next turn: `(name, why)`.

    The provider when it can. Else the fallback, with `why` the sentence the
    board paints. Else `(None, why)`: nobody here can, and the turn is not run.
    """
    want = provider(cfg)
    why = unavailable(cfg, want, now)
    if not why:
        return want, None
    alt = fallback(cfg)
    if alt and alt != want and not unavailable(cfg, alt, now):
        return alt, ("'%s' cannot take this turn -- %s; '%s' is taking it"
                     % (want, why, alt))
    return None, ("'%s' cannot take this turn -- %s, and %s" % (
        want, why, ("there is no fallback" if not alt or alt == want else
                    "neither can '%s' (%s)" % (alt, unavailable(cfg, alt, now)))))


# ---------------------------------------------------------------------------
# what the board draws
# ---------------------------------------------------------------------------
def listing(cfg=None):
    """The table the board and `board see` read: the setting and every recipe.

    `default` is the provider; `machine` who takes the next turn (None when
    nobody can) and `why` the sentence when that is not the provider.
    In-process and file reads only, so it can sit under a poll.
    """
    cfg = cfg or load_config()
    took, why = resolve(cfg)
    return {
        "default": provider(cfg),
        "fallback": fallback(cfg),
        "machine": took,
        "why": why,
        "vision_agent": cfg.get("vision_agent") or None,
        "agents": [
            {"name": n,
             "label": agent_label(cfg, n),
             "cmd": " ".join(spec.get("cmd", [])),
             "missing": missing_command(spec.get("cmd")),
             "unkeyed": keys.unkeyed(spec),
             "keys": keys.store(),
             "exclusive": spec.get("exclusive") or None,
             "private": spec.get("private") or None,
             "vision": spec.get("vision") or None,
             "unavailable": unavailable(cfg, n),
             "headless": bool(spec.get("headless_first") or spec.get("headless"))}
            for n, spec in sorted((cfg.get("agents") or {}).items())
            if isinstance(spec, dict)],
    }
