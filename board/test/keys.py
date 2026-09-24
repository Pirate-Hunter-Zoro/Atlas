#!/usr/bin/env python3
"""A provider is a recipe plus a key, and this is the key half.

    python3 test/keys.py

Nothing in this tool could hand a turn a credential, and that was the only
reason a hosted provider other than the two we are logged into could not be run.
Two things fix it and they are useless apart: a store outside the tree, and an
`env` on a recipe that spends what is in it.

Three rules underneath, and each one is here because getting it wrong is silent:

  - A KEY NEVER REACHES ARGV. `ps` output is readable by anything on the
    machine, which is why `ai-config/policy/credentials.txt` exists at all.
    `with_usage` puts flags on the command; `turn_environment` puts secrets in
    the environment, and the two must not be confused.
  - A RECIPE WITH NO KEY IS `unkeyed`, in the same word the browser already
    understands for an executable that is not here. A button that is drawn,
    tapped, and dies in a log file hands the person holding the iPad the one
    thing they can least act on.
  - AND THE MODE RULE IS THE NARROW ONE. World-readable is refused. Group-
    readable is NOT, and the obvious rule that refuses it would refuse every
    file in this home -- see `tutorboard/keys.py` for the measurement.
"""

import importlib.machinery
import importlib.util
import os
import stat
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

os.environ.setdefault("BOARD_STATE_DIR", tempfile.mkdtemp(prefix="keys-state-"))
os.environ.setdefault("BOARD_NODE_NAME", "test-node")
os.environ.setdefault("BOARD_NO_TAILNET", "1")

from tutorboard import keys, paths                            # noqa: E402

loader = importlib.machinery.SourceFileLoader("tutor", os.path.join(ROOT, "bin", "tutor"))
spec = importlib.util.spec_from_loader("tutor", loader)
tutor = importlib.util.module_from_spec(spec)
loader.exec_module(tutor)

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


box = tempfile.mkdtemp(prefix="keys-")
paths.KEYS = os.path.join(box, "keys.env")


def put(text, mode=0o600):
    with open(paths.KEYS, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(paths.KEYS, mode)
    keys.forget()


# ---- the store -------------------------------------------------------------
keys.forget()
check("with no file at all there are no keys, and it is not a crash",
      not keys.have("DEEPSEEK_API_KEY") and keys.get("DEEPSEEK_API_KEY") is None)
check("and it says why, naming the file somebody has to create",
      paths.KEYS in (keys.why_not() or ""))

put("# a comment\nDEEPSEEK_API_KEY=sk-abc123\n\nOTHER = spaced \n")
check("a key reads back", keys.get("DEEPSEEK_API_KEY") == "sk-abc123")
check("a comment is not a key", not keys.have("# a comment"))
check("whitespace around a name and a value is not part of either",
      keys.get("OTHER") == "spaced")
check("an absent name is absent rather than empty",
      keys.get("NOPE") is None and not keys.have("NOPE"))

put('QUOTED="sk-quoted"\nHALF="sk-half\n')
check("a value somebody pasted with quotes round it loses them",
      keys.get("QUOTED") == "sk-quoted")
check("and one with a stray quote keeps it, because it is part of the value",
      keys.get("HALF") == '"sk-half')

put("EMPTY=\n")
check("a name with nothing after it is not a key", not keys.have("EMPTY"))

# ---- the mode, and the one rule that is deliberately NOT here --------------
put("DEEPSEEK_API_KEY=sk-abc123\n", mode=0o644)
check("a world-readable key file is refused and the key reads as absent",
      not keys.have("DEEPSEEK_API_KEY"))
check("and it says so in words that name the fix",
      "chmod" in (keys.why_not() or ""))

put("DEEPSEEK_API_KEY=sk-abc123\n", mode=0o660)
check("a GROUP-readable one is not refused -- this filer forces 770 on every "
      "file in the home, and refusing it would refuse the lot",
      keys.have("DEEPSEEK_API_KEY"))
src = open(os.path.join(ROOT, "tutorboard", "keys.py"), encoding="utf-8").read()
check("and the measurement that settles that is written down where the next "
      "person tightening it will read it",
      "NFSv4" in src and "770" in src)

# ---- substitution ----------------------------------------------------------
put("DEEPSEEK_API_KEY=sk-abc123\n")
check("{KEY} with a key present produces the value",
      keys.fill("Bearer {DEEPSEEK_API_KEY}") == "Bearer sk-abc123")
check("and with it absent produces nothing rather than the literal braces -- "
      "a provider handed `{NAME}` verbatim fails as an auth error in a log",
      keys.fill("Bearer {NOT_A_KEY}") is None)
check("a value with no braces in it is itself",
      keys.fill("deepseek-flash") == "deepseek-flash")

# ---- unkeyed ---------------------------------------------------------------
check("a recipe that needs nothing is never unkeyed",
      keys.unkeyed({"cmd": ["claude"]}) is None)
check("one whose key is here is not either",
      keys.unkeyed({"needs_key": "DEEPSEEK_API_KEY"}) is None)
check("and one whose key is absent reports the key's NAME, so the dimmed "
      "button can say which line to add",
      keys.unkeyed({"needs_key": "NOT_A_KEY"}) == "NOT_A_KEY")

# ---- env on a recipe -------------------------------------------------------
plain = {"cmd": ["claude"]}
check("a recipe with no env leaves the turn's environment exactly as it was",
      tutor.turn_environment(plain) is None
      and tutor.turn_environment(plain, {"A": "1"}) == {"A": "1"})

routed = {"env": {"ANTHROPIC_BASE_URL": "https://example.test",
                  "ANTHROPIC_AUTH_TOKEN": "{DEEPSEEK_API_KEY}"}}
env = tutor.turn_environment(routed, {"COLI_SESSION_ID": "s1"})
check("env reaches the subprocess", env["ANTHROPIC_BASE_URL"] == "https://example.test")
check("with {KEY} substituted", env["ANTHROPIC_AUTH_TOKEN"] == "sk-abc123")
check("and a colibri mission's own variable lands in the SAME dict rather than "
      "in a second one that fights it", env["COLI_SESSION_ID"] == "s1")

missing = {"env": {"TOKEN": "{NOT_A_KEY}"}}
check("a value naming a key that is not here is dropped rather than passed "
      "through with the braces on",
      "TOKEN" not in tutor.turn_environment(missing, {}))

# THE RULE THIS FILE EXISTS FOR. Nothing a recipe routes with may end up on a
# command line, because argv is in `ps` output.
tutor_src = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
cmd = tutor.with_usage(dict(routed, usage_args=["--output-format", "json"]),
                       ["claude", "-p", "hello"])
check("a key never reaches argv: `with_usage` adds flags and nothing else",
      not any("sk-abc123" in a or "AUTH_TOKEN" in a for a in cmd))
check("and the reason is written beside the function rather than in a commit "
      "message", "must not reach argv" in tutor_src
      and "credentials.txt" in tutor_src)

# ---- the whole of a provider: one entry and one line -----------------------
D = tutor.DEFAULT_CONFIG
ds = D["agents"]["deepseek"]
check("deepseek runs the claude binary, so every part of this tool that knows "
      "how to drive Claude Code drives it unchanged",
      ds["cmd"] == ["claude"] and ds["headless_first"][0] == "claude")
check("it resumes the way the claude recipe does",
      "--continue" in ds["headless"] and "--continue" not in ds["headless_first"])
check("it reports what it cost", ds["usage"] == "claude-json")
check("it names the key it needs", ds["needs_key"] == "DEEPSEEK_API_KEY")
check("the endpoint is the Anthropic-format one, which is why the binary works",
      ds["env"]["ANTHROPIC_BASE_URL"].endswith("/anthropic"))
check("AND THE MODEL IS PINNED TWICE. Unpinned, a `claude-opus` name maps to a "
      "text-only model that substitutes a placeholder for an image rather than "
      "failing -- a tutor handed a slate PNG would answer about nothing",
      ds["env"]["ANTHROPIC_MODEL"]
      == ds["env"]["ANTHROPIC_SMALL_FAST_MODEL"] != "")
check("and the reason is next to the pin",
      "PIN THE MODEL OR LOSE THE HANDWRITING" in tutor_src)
check("it is not driven through opencode, which would be a second agent's "
      "config file and a second credential store for one binary",
      ds["cmd"] != ["opencode"])

# AND THE ENV IS A CONTRACT WITH A BINARY THIS TREE DOES NOT OWN, so it is
# pinned here: four names, and the failure of any of them is silent rather than
# loud. `ANTHROPIC_CUSTOM_MODEL_OPTION` and its `_NAME` / `_DESCRIPTION` /
# `_SUPPORTED_CAPABILITIES` siblings read as if they belong in this list and do
# not: they add an entry to the interactive `/model` picker, which a `-p` turn
# never opens.
check("the routing is exactly four names, so a variable that does nothing "
      "cannot drift in beside the ones that do",
      sorted(ds["env"]) == ["ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
                            "ANTHROPIC_MODEL", "ANTHROPIC_SMALL_FAST_MODEL"])
# THE THREE PLACES THE MODEL NAME APPEARS ARE ASKED TO AGREE WITH EACH OTHER,
# and deliberately not compared to a literal. The recipe's own comment calls
# this "the field that goes stale, and it is a one-string change when it does";
# a test holding a fourth copy makes it a four-string change and fires on the
# CORRECT action. What must not drift is the three against each other.
check("every variable that selects a model selects the SAME one, and so does "
      "the eye `board see` lends a sitting -- so updating a renamed model stays "
      "the one-string change the recipe says it is",
      len(set(v for k, v in ds["env"].items() if "MODEL" in k)
          | {ds["vision"]["model"]}) == 1)
check("the credential is named rather than written, so the tree holds no key",
      ds["env"]["ANTHROPIC_AUTH_TOKEN"] == "{DEEPSEEK_API_KEY}")

# THE ARGV RULE, ASKED OF THE REAL RECIPE rather than of a stand-in, because
# this is the one that is unrecoverable: `ps` is readable by every account on
# this machine and a leaked key cannot be un-leaked.
real_env = tutor.turn_environment(ds, {})
check("the real recipe spends the key through the environment",
      real_env["ANTHROPIC_AUTH_TOKEN"] == "sk-abc123"
      and real_env["ANTHROPIC_MODEL"] == "deepseek-flash")
real_cmd = tutor.with_usage(ds, [a.replace("{prompt}", "hello")
                                 for a in ds["headless"]])
check("and nothing of it reaches the command line",
      not any("sk-abc123" in a or "DEEPSEEK" in a or "AUTH_TOKEN" in a
              for a in real_cmd))

# AND THE PRECONDITION NO VARIABLE SUPPLIES: a route to the host. The variables
# are correct and a turn still dies if the network drops the name, so the recipe
# names the host it opens and the reasons are beside it rather than in a log.
check("the recipe names the host its turns open, and it is the host the base "
      "URL points at rather than a second guess about it",
      ds["egress_probe"] and all(u.startswith(ds["env"]["ANTHROPIC_BASE_URL"])
                                 for u in ds["egress_probe"]))
check("the stderr line this provider prints on every turn is written off where "
      "the next person reads it, rather than re-diagnosed as a refusal",
      "ON STDERR IS COSMETIC" in tutor_src)
check("and the one thing four variables cannot supply is stated with them",
      "THE VARIABLES CANNOT SUPPLY IS A ROUTE" in tutor_src)

# ---- and the refusals, on the surfaces that draw them ----------------------
unkeyed_cfg = {"default_agent": "ghost", "agents": {
    "ghost": {"cmd": ["sh"], "headless": ["sh", "-c", "{prompt}"],
              "needs_key": "NOT_A_KEY"}}}
check("an unkeyed recipe cannot take a turn, in the same words a missing "
      "executable cannot",
      "NOT_A_KEY" in (tutor.agent_unavailable(unkeyed_cfg, "ghost") or ""))
check("and the daemon refuses to start on one rather than listening and "
      "failing every turn into a log",
      "needs the key %s" in tutor_src)

print("%d FAILURES" % len(fails) if fails
      else "a provider is a recipe plus a key, and neither is in the tree")
sys.exit(1 if fails else 0)
