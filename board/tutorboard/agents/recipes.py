"""Which assistant takes a turn: the recipes, this machine's config, and the choice.

A provider is a recipe plus a key. `DEFAULT_CONFIG` is the built-in table;
`load_config` lays this machine's `config.json` over it; `resolve_agent` says
which recipe a workspace asks for, `agent_unavailable` why one cannot run here,
and `choose_agent` who actually takes the turn.
"""

import json
import os
import shutil
import sys
import time

from tutorboard import atlas, keys, limits, machine
from tutorboard.course import config
from tutorboard.net import egress

CONFIG_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")),
    "tutor-board")
CONFIG = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "courses_dir": atlas.root(),
    "default_agent": "claude",
    "agents": {
        "claude": {
            "cmd": ["claude"], "prompt": "argv", "label": "Claude",
            "headless_first": ["claude", "-p", "{prompt}"],
            "headless": ["claude", "-p", "{prompt}", "--continue"],
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
            "headless": ["opencode", "--pure", "run", "--auto",
                         "-m", "deepseek/deepseek-flash", "--continue",
                         "{prompt}"],
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
            "headless": ["codex", "exec", "resume", "--last",
                         "--dangerously-bypass-approvals-and-sandbox",
                         "{prompt}"],
            "usage": "codex-jsonl",
            "usage_args": ["--json"],
            "egress_probe": ["https://chatgpt.com/backend-api/codex/responses"],
            "env": {},
        },
    },
    "vision_agent": "claude",
    "fallback": None,
    "only_agent": None,
    "headless_timeout": 900,
    "doing_timeout": 3600,
    "handoff_timeout": 600,
    "session_turns": 1,
    "quota_tokens": None,
}

def config_shadows():
    """Which fields of a BUILT-IN recipe this machine's config is holding down.

    `{agent: [field, ...]}`, empty when the config adds nothing or only adds
    agents of its own.

    A MERGED FIELD IS FROZEN AT THE DAY SOMEBODY WROTE IT, and nothing says so
    afterwards. The merge above exists so that a machine can adjust one field of
    a recipe without losing the rest, which is right -- but the copy it keeps
    wins for ever, so a fix shipped to the built-in table lands everywhere
    except the machine whose config mentions that field. Every symptom of that
    is the tool's own behaviour looking wrong.

    Found the hard way. This machine's config carried a verbatim copy of the
    whole `agents` table from an older version. Its `codex` entry was
    `["codex", "exec", "{prompt}"]`, so the resume path and the sandbox flag
    shipped in the built-in recipe were both overridden by a file nobody had
    opened in months, and every resumed Codex turn went on failing silently
    while the recipe in the repository read correctly.

    Only fields that DIFFER are named: a config repeating the built-in value is
    stale in the same way but changes nothing today, and a warning about it
    would be noise on every run of `board doctor`. `replace` is reported
    whatever it says, because it turns the whole recipe off.
    """
    try:
        with open(CONFIG, "r", encoding="utf-8") as fh:
            user = json.load(fh) or {}
    except (OSError, ValueError):
        return {}
    out = {}
    for name, spec in (user.get("agents") or {}).items():
        built = DEFAULT_CONFIG["agents"].get(name)
        # An agent this machine invented shadows nothing: there is no built-in
        # recipe behind it to go stale against.
        if not isinstance(spec, dict) or not isinstance(built, dict):
            continue
        if spec.get("replace"):
            out[name] = ["the whole recipe (replace)"]
            continue
        fields = sorted(k for k, v in spec.items()
                        if k in built and built[k] != v)
        if fields:
            out[name] = fields
    return out

def load_config():
    """The defaults above, with this machine's config file laid over them.

    `agents` merges one level DEEPER than everything else, and the reason is a
    trap somebody has to fall into only once. A machine adjusting a single field
    of a built-in recipe -- saying that the claude on THIS machine takes an extra
    flag, say -- writes the obvious thing:

        "agents": { "claude": { "prompt": "none" } }

    With a plain `update` that REPLACES the whole recipe: the command, the
    headless turn, the handoff, all of it, gone. The machine then has an agent
    called `claude` that cannot run anything, and every turn fails into a log
    while the board shows a tutor listening. Nothing in the file the person wrote
    says that; they added one key.

    So a dict per agent merges into the built-in one, and adding an agent that
    does not exist yet works exactly as before because there is nothing to merge
    with. Replacing a recipe outright is still possible and is now something you
    have to mean: give the entry a `"replace": true`.
    """
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        with open(CONFIG, "r", encoding="utf-8") as fh:
            user = json.load(fh) or {}
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
            else:
                cfg[k] = v
    except (OSError, ValueError):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if not os.path.exists(CONFIG):
            with open(CONFIG, "w", encoding="utf-8") as fh:
                json.dump(DEFAULT_CONFIG, fh, indent=2)
                fh.write("\n")

    # A `courses_dir` LEFT OVER FROM THE FLAT LAYOUT is dropped here.
    #
    # The key used to mean "the directory the courses are siblings in", and
    # every machine has one saved from before the move naming the home
    # directory. Read literally after the move, the course walk went over `~`
    # flat, found the old working directories still sitting there, and listed
    # Tutor-Board itself as a course.
    #
    # The test is whether it holds the board's own package, which is what an
    # Atlas root is. So a person who deliberately points this at ANOTHER checkout
    # still gets what they asked for, and a value that can only be wrong is
    # wrong once, here, instead of at every use. `atlas.root()` needs no
    # configuring at all: it derives from where this package actually is.
    said = cfg.get("courses_dir")
    if said:
        said = os.path.expanduser(said)
        if not os.path.isdir(os.path.join(said, "board", "tutorboard")):
            cfg["courses_dir"] = atlas.root()
    return cfg

def read_course(root):
    """What a course calls itself: its `tutorboard.json`, name defaulted.

    A `mode` or `stance` left in the file is dropped on the way past: a key
    left in a course's own file must never be the reason two courses behave
    differently. Who writes the code is the session's mode.
    """
    cfg = {"name": os.path.basename(root).replace("-", " ")}
    try:
        with open(os.path.join(root, "tutorboard.json"), "r", encoding="utf-8") as fh:
            cfg.update(json.load(fh) or {})
    except (OSError, ValueError):
        pass
    cfg.pop("mode", None)
    cfg.pop("stance", None)
    return cfg

def this_host():
    """What this machine calls itself. One place decides; see boardlib."""
    return machine.node_name()

def missing_command(recipe):
    """The recipe's own executable, when this machine has not got it.

    Worth asking because the default is now a particular program rather than a
    self-contained script, and two machines do not have the same tools installed.
    An agent whose command is missing does not fail loudly: the daemon starts,
    the board shows an assistant listening, and every turn dies in a log file. Say
    it where somebody can still do something about it.

    A script agent runs under this interpreter, which is by definition present.
    """
    exe = (recipe or [None])[0]
    if not exe or os.path.basename(exe) == os.path.basename(sys.executable):
        return None
    return None if shutil.which(exe) else exe

def resolve_agent(cfg, course, override=None, interactive=False, say=None,
                  why=None):
    """Which assistant tutors this course, on this machine, in this sitting.

    Most specific wins, and every layer is configuration rather than code:

      1. --agent on the command line          -- this once
      2. "agent" in the sitting's state       -- this sitting's work
      3. "agent" in the course's tutorboard.json -- this course, everywhere
      4. default_agent                        -- everything else

    THE SITTING IS THE LAYER THAT WAS MISSING, and the one the iPad can reach.
    Without it, choosing the local model for one evening's work meant editing a
    file that is a statement about the workspace for ever. A `tutorboard.json`
    `agent` is one name for every sitting: there is no per-kind form.

    AN ASSISTANT IS RE-RESOLVED EVERY TURN. This function answers the question
    and `for_this_turn` asks it again at the top of each turn, so a tap on the
    front door or a sitting rewritten from the iPad lands on the next card
    rather than the next sitting. What makes that cheap is that `session_turns`
    is 1: a hosted turn holds no conversation, and reconstructs the evening from
    `board brief` and `board recap` off disk whoever takes it.

    The sitting layer is what the iPad writes: `_mark` writes it with the
    sitting, and a sitting that does not name one clears it.

    Which model an assistant runs is not a layer here and never should be: an
    agent entry is a command recipe, so a second model is a second entry whose
    `cmd` carries the flag. Nothing in this file knows what a model is.

    `only_agent` is not a fifth layer but a fence over all four: when it names
    a recipe, whatever the layers picked is refused unless it is that recipe or
    a `private` one, and the line saying which layer was overruled goes to `say`
    and, when `why` is a list, onto it -- `for_this_turn` paints it.
    """
    say = say or (lambda m: print(m, file=sys.stderr))
    mine = config.sitting_agent((course or {}).get("root"))
    # The sitting's own answer is DROPPED when this machine has no such agent,
    # where every other layer refuses. It is the one layer written from a
    # browser, and a name that resolves to nothing leaves the course with no
    # tutor at all -- which is a worse answer to a misspelling than the
    # workspace's own.
    if mine and mine not in cfg["agents"]:
        say("this sitting asks for '%s', which is not an assistant here; "
            "falling back" % mine)
        mine = None
    picked = None
    ws = config.workspace_agent(course)
    layer = None
    for layer, pick in (("--agent", override), ("this sitting", mine),
                        ("this workspace's tutorboard.json", ws),
                        ("`default_agent`", cfg.get("default_agent"))):
        if pick and pick in cfg["agents"]:
            picked = pick
            break
        if pick:
            say("no agent called '%s'; try: tutor --agents" % pick)
            return None
    # THE SWITCH IS ASKED LAST AND OVERRULES EVERY LAYER ABOVE IT, and says
    # which layer it overruled: a workspace naming claude on a machine running
    # DeepSeek only is refused rather than quietly re-read, and the next layer
    # down is not consulted -- it is the switch's answer or nothing.
    only = only_agent(cfg)
    if only and (not picked or only_bars(cfg, picked)):
        if only not in cfg["agents"]:
            say("`only_agent` in %s names '%s', which is not an assistant "
                "here; try: tutor agent only --off" % (CONFIG, only))
            return None
        if picked:
            line = ("%s asks for '%s'; %s (\"only_agent\": \"%s\" in %s), so "
                    "'%s' takes it" % (layer, picked, only_bars(cfg, picked),
                                       only, CONFIG, only))
            say(line)
            if why is not None:
                why.append(line)
        picked = only
    return picked


def only_agent(cfg):
    """The one assistant this machine runs (`only_agent`), or None for any."""
    name = (cfg or {}).get("only_agent")
    return name.strip() if isinstance(name, str) and name.strip() else None


def agent_label(cfg, name):
    """What a person calls a recipe: its `label`, or its name."""
    return ((cfg.get("agents") or {}).get(name) or {}).get("label") or name


def only_bars(cfg, name):
    """The switch's sentence when `only_agent` rules `name` out, or None.

    Every recipe but the one named, in one sentence the board can paint. A
    `private` recipe is never barred: the switch is about hosted providers, and
    the fenced reader is resolved only where a workspace names it anyway.
    """
    only = only_agent(cfg)
    if not only or not name or name == only:
        return None
    if ((cfg.get("agents") or {}).get(name) or {}).get("private"):
        return None
    return "this machine is running %s only" % agent_label(cfg, only)


def agent_probe_urls(spec):
    """The endpoints THIS recipe's turns open, or None for the machine's own.

    A recipe that points the binary somewhere else -- `ANTHROPIC_BASE_URL` at a
    third party -- talks to a host the machine-wide probe never asks about, and
    the two questions have different answers when one hostname is filtered and
    the rest of the internet is not. None means the recipe adds nothing to the
    default agent's, which is what `egress.egress_probe_urls` already returns.
    """
    urls = (spec or {}).get("egress_probe")
    if isinstance(urls, str):
        urls = [urls]
    return [u for u in urls if u] if urls else None


def provider_probe_urls(cfg):
    """Every configured provider's own endpoints, for the machine-wide probe.

    Configured means a recipe this machine could run: its command is here and
    its key is in `keys.env`. A recipe with neither opens no connection from
    here, so asking after its host would answer a question about nobody's turn.
    """
    out = []
    for name in sorted(cfg.get("agents") or {}):
        spec = cfg["agents"][name] or {}
        if missing_command(spec.get("cmd")) or keys.unkeyed(spec):
            continue
        for url in agent_probe_urls(spec) or ():
            if url not in out:
                out.append(url)
    return out


# How long one answer about a third-party provider's reachability stands before
# it is asked again. Long enough that a sitting cannot make the daemon probe
# once a turn, short enough that a filter lifted at lunchtime is picked up in the
# afternoon -- and the stand-down record, not this, is what remembers a NO.
PROBE_TTL = 600
_PROBED = {}


def probe_before_turn(cfg, name, log=None, now=None):
    """Ask whether this recipe's own provider answers, before a turn is spent on it.

    THE ONE MOMENT A ROUND TRIP IS WORTH IT. A recipe pointed at a third party
    -- `ANTHROPIC_BASE_URL` somewhere else -- talks to a host nothing else on
    this machine talks to, so nothing else has an opinion about it, and the first
    news of a filtered hostname is a student watching three minutes of retries
    end in no card. That turn is the expensive way to learn something a socket
    answers in a tenth of a second.

    Only for a recipe that names its OWN endpoints. Everything driving the
    machine's default provider is covered by the machine-wide probe the failure
    path already runs, and would pay a round trip here for nothing.

    Cached, and never in front of an answer: the result stands for `PROBE_TTL`,
    a recipe already stood down is not asked about again, and a machine with no
    egress at all is not this provider's fault and is left to
    `egress.rotate_exit_node` on the failure path.
    """
    spec = (cfg.get("agents") or {}).get(name) or {}
    own = agent_probe_urls(spec)
    now = now or time.time()
    if not own or egress.stood_down(name, now):
        return None
    if now - _PROBED.get(name, 0) < PROBE_TTL:
        return None
    _PROBED[name] = now
    if egress.egress_ok(urls=own, timeout=8) or not egress.egress_ok(
            also=provider_probe_urls(cfg)):
        return None
    host = probe_host(own)
    egress.mark_unreachable(name, host)
    until = (egress.stood_down(name, now) or {}).get("until", now)
    if log:
        log.write("!! '%s' cannot reach %s from here, and everything else on "
                  "the network answers; standing it down until %s before a turn "
                  "is spent on it\n"
                  % (name, host, time.strftime("%H:%M", time.localtime(until))))
    return host


def probe_host(urls):
    """The hostname a probe list is about, for saying which one went dark."""
    try:
        from urllib.parse import urlsplit
        return urlsplit((urls or [""])[0]).hostname or ""
    except (ValueError, IndexError):
        return ""


def agent_unavailable(cfg, name, now=None):
    """Why this agent cannot take a turn on this machine right now, or None.

    The switch first: with `only_agent` set, every other hosted recipe is
    "this machine is running <label> only" and nothing else is asked of it.

    Then five reasons and they are all facts rather than opinions: the executable is
    not here, the key is not here, the allowance is gone until a time somebody
    wrote down, the provider's own hostname does not answer from this machine, or
    its turns fail here for a reason the network is innocent of -- a renamed
    model, a rejected key. In the words the board already uses.

    The last two are READ here and never measured here. This runs behind
    `--agents --json`, which the board asks several times a second, and a probe
    on that path would put a round trip to the internet under every poll. A
    failed turn does the measuring and writes the finding down, and so does the
    one probe a sitting pays when it is pointed at a recipe with a provider of
    its own; see `egress.mark_unreachable`, `egress.mark_failing` and
    `probe_before_turn`.
    """
    spec = (cfg.get("agents") or {}).get(name)
    if not spec:
        return "there is no recipe called '%s'" % name
    # THE SWITCH FIRST, before any binary or key check: a machine running one
    # provider only says so about every other, rather than whatever else is
    # also true of them.
    barred = only_bars(cfg, name)
    if barred:
        return barred
    if not (spec.get("headless") or spec.get("headless_first")):
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
    dark = egress.stood_down(name, now)
    if dark and dark["host"]:
        return ("%s does not answer from this machine; asking again after %s"
                % (dark["host"],
                   time.strftime("%H:%M", time.localtime(dark["until"]))))
    if dark:
        return ("its turns keep failing here (%s); asking again after %s"
                % (dark["why"][:120],
                   time.strftime("%H:%M", time.localtime(dark["until"]))))
    return None


def choose_agent(cfg, wanted, now=None):
    """Who actually takes the next turn. `(name, why)`; `why` is None if nothing moved.

    THE LIMIT BELONGS TO AN AGENT, NOT TO THE MACHINE, AND THIS IS WHERE THAT
    STOPS BEING A SENTENCE. When the one we want has run out, the next one that
    is installed, keyed, unlimited and not `private` takes the turn, and the
    lesson goes on.

    AND THE STUDENT IS TOLD, which is the condition on all of it: `why` comes
    back so the caller can put it in the log and in `agent_state`, and the strip
    names the assistant that is writing. A lesson answered by something else
    without anybody saying so would be worse than a board that reports the
    failure -- see the standing rule in `AI_INSTRUCTIONS.md`.

    WHAT MAKES IT SAFE IS ALREADY TRUE, and it is the reason this is small:
    `session_turns` is 1, so every ordinary turn is cold -- it reconstructs the
    evening from `board brief` and `board recap`, off disk. A provider swap
    between turns therefore loses NOTHING: there is no conversation to
    transfer.

    `private` is never fallen into. It is the fence flag -- the only assistant
    allowed to read `phi`, whose cards must not reach a remote -- and an
    automatic choice is exactly the kind of choice that must not cross it.
    """
    # THE SWITCH NEVER CROSSES. With `only_agent` set, a turn wanted by any
    # other hosted recipe goes to the switch's recipe whether or not that one
    # can take it -- failing visibly on the provider the machine is running is
    # the switch's whole promise -- and the loop below can only find the
    # switch's recipe, because `agent_unavailable` bars every other.
    only = only_agent(cfg)
    if only and only_bars(cfg, wanted) and only in (cfg.get("agents") or {}):
        return only, ("'%s' cannot take this turn -- %s; '%s' is taking it"
                      % (wanted, only_bars(cfg, wanted), only))
    if wanted and not agent_unavailable(cfg, wanted, now):
        return wanted, None
    said = cfg.get("fallback")
    if not isinstance(said, list) or not said:
        # What `--agents` reports, in the order it reports it.
        said = sorted(cfg.get("agents") or {})
    for name in said:
        if name == wanted:
            continue
        spec = (cfg.get("agents") or {}).get(name) or {}
        if spec.get("private"):
            continue
        if agent_unavailable(cfg, name, now):
            continue
        return name, ("'%s' cannot take this turn -- %s; '%s' is taking it"
                      % (wanted, agent_unavailable(cfg, wanted, now), name))
    # Nobody else can either, so the turn goes to the one we wanted and fails
    # where it is visible. Exactly today's behaviour, which is the right answer
    # when there is no second provider to reach for.
    return wanted, None
