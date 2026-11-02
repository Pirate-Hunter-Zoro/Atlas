"""The one assistant: DeepSeek through OpenCode.

Every turn, wrap-up, `board see` and `board doctor` runs `spec()`; `ready`
says why it cannot take a turn here now, or None. This machine's
`config.json` carries the timeouts and `courses_dir`. It does not pick an
assistant: `provider`, `fallback`, `vision_agent` and `agents` in it are
ignored. `TUTORBOARD_OPENCODE` names another opencode binary, which is how a
test runs a fake one.
"""

import copy
import json
import os
import shutil
import time

from tutorboard import keys, limits, machine, paths, subjects

CONFIG_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")),
    "tutor-board")
CONFIG = os.path.join(CONFIG_DIR, "config.json")

NAME = "deepseek"
LABEL = "DeepSeek"
KEY = "DEEPSEEK_API_KEY"
# A model rename is `MODEL` and `vision.model`. Re-check the ids with
# `opencode models deepseek`.
MODEL = "deepseek/deepseek-flash"
API = "https://api.deepseek.com/chat/completions"

DEEPSEEK = {
    "name": NAME,
    "label": LABEL,
    # Every turn is a fresh conversation in the Atlas root; `--format json`
    # is what `usage` reads the cost and the error out of.
    "headless_first": ["opencode", "--pure", "run", "--auto", "-m", MODEL,
                       "--format", "json", "{prompt}"],
    "needs_key": KEY,
    # Keys ride in the environment, never argv (`turn.turn_environment`).
    "env": {
        KEY: "{%s}" % KEY,
        "OPENCODE_CONFIG_CONTENT": json.dumps({
            "small_model": MODEL,
            "permission": {"skill": "deny"},
            "provider": {"deepseek": {"options": {
                "apiKey": "{env:%s}" % KEY}}}}),
    },
    "egress_probe": [API],
    # deepseek-flash reads images through the chat-completions endpoint;
    # `board doctor` proves it with the witness strip.
    "vision": {"endpoint": API, "model": "deepseek-flash", "needs_key": KEY},
    "prices": {
        "peak": {"in": 0.30, "cache_write": 0.30, "cache_read": 0.006, "out": 1.20},
        "off": {"in": 0.15, "cache_write": 0.15, "cache_read": 0.003, "out": 0.60},
        "peak_utc": [["01:00", "04:00"], ["06:00", "10:00"]],
        "peak_weekdays_only": True,
    },
}

DEFAULT_CONFIG = {
    "courses_dir": subjects.root(),
    "headless_timeout": 900,
    "doing_timeout": 3600,
    "handoff_timeout": 600,
    "quota_tokens": None,
}

# Keys a config.json may still carry from when it chose an assistant.
IGNORED = ("provider", "fallback", "vision_agent", "agents", "default_agent",
           "only_agent", "session_turns")


def load_config():
    """The defaults above, with this machine's config file laid over them,
    less `IGNORED`. A missing or unreadable file is the defaults; nothing is
    written."""
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG, "r", encoding="utf-8") as fh:
            user = json.load(fh) or {}
    except (OSError, ValueError):
        user = {}
    if isinstance(user, dict):
        cfg.update((k, v) for k, v in user.items() if k not in IGNORED)
    # A `courses_dir` that does not hold the board's own package is not an
    # Atlas root, so it is dropped for the one this package derives.
    said = cfg.get("courses_dir")
    if said:
        said = os.path.expanduser(said)
        if not os.path.isdir(os.path.join(said, "board", "tutorboard")):
            cfg["courses_dir"] = subjects.root()
    return cfg


def spec():
    """The DeepSeek recipe, a copy, with `TUTORBOARD_OPENCODE` applied."""
    got = copy.deepcopy(DEEPSEEK)
    exe = os.environ.get("TUTORBOARD_OPENCODE")
    if exe:
        got["headless_first"][0] = exe
    return got


def argv(prompt, recipe=None):
    """The command one turn runs, with `prompt` in it."""
    return [a.replace("{prompt}", prompt)
            for a in (recipe or spec())["headless_first"]]


def this_host():
    """What this machine calls itself. One place decides; see boardlib."""
    return machine.node_name()


def ready(now=None):
    """Why DeepSeek cannot take a turn on this machine now, or None, from disk
    alone: no opencode, no key, or a spent balance (`limits.mark_limited`)."""
    exe = spec()["headless_first"][0]
    if not shutil.which(exe):
        return "`%s` is not on the path here" % exe
    if not keys.have(KEY):
        return "%s is not in %s or %s" % (KEY, keys.store(), paths.DEEPSEEK_KEY)
    until = limits.limited_until(now=now)
    if until:
        return ("DeepSeek's allowance is gone until %s"
                % time.strftime("%H:%M", time.localtime(until)))
    return None
