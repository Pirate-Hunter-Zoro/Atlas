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

from tutorboard.agents import recipes  # noqa: E402
from tutorboard.runner import turn as runturn  # noqa: E402
from tutorboard.agents import usage  # noqa: E402

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
check("a recipe with no env leaves the turn's environment as it was, and "
      "marks it a turn so the pre-commit hook guards it",
      runturn.turn_environment(plain, {"A": "1"}) == {"A": "1", "TUTORBOARD_TURN": "1"}
      and runturn.turn_environment(plain).get("TUTORBOARD_TURN") == "1"
      and runturn.turn_environment(plain).get("PATH") == os.environ.get("PATH"))

routed = {"env": {"ANTHROPIC_BASE_URL": "https://example.test",
                  "ANTHROPIC_AUTH_TOKEN": "{DEEPSEEK_API_KEY}"}}
env = runturn.turn_environment(routed, {"COLI_SESSION_ID": "s1"})
check("env reaches the subprocess", env["ANTHROPIC_BASE_URL"] == "https://example.test")
check("with {KEY} substituted", env["ANTHROPIC_AUTH_TOKEN"] == "sk-abc123")
check("and a colibri mission's own variable lands in the SAME dict rather than "
      "in a second one that fights it", env["COLI_SESSION_ID"] == "s1")

missing = {"env": {"TOKEN": "{NOT_A_KEY}"}}
check("a value naming a key that is not here is dropped rather than passed "
      "through with the braces on",
      "TOKEN" not in runturn.turn_environment(missing, {}))

# THE RULE THIS FILE EXISTS FOR. Nothing a recipe routes with may end up on a
# command line, because argv is in `ps` output.
# The recipes, a turn's environment, and the daemon that refuses an unkeyed one.
tutor_src = "".join(open(os.path.join(ROOT, "tutorboard", *p), encoding="utf-8").read()
                    for p in (("agents", "recipes.py"), ("runner", "turn.py"),
                              ("runner", "loop.py")))
cmd = usage.with_usage(dict(routed, usage_args=["--output-format", "json"]),
                       ["claude", "-p", "hello"])
check("a key never reaches argv: `with_usage` adds flags and nothing else",
      not any("sk-abc123" in a or "AUTH_TOKEN" in a for a in cmd))
check("and the reason is written beside the function rather than in a commit "
      "message", "must not reach argv" in tutor_src
      and "credentials.txt" in tutor_src)

# ---- the whole of a provider: one entry and one line -----------------------
D = recipes.DEFAULT_CONFIG
ds = D["agents"]["deepseek"]
check("deepseek runs through opencode, its own harness, and never through "
      "another provider's client",
      ds["cmd"][0] == "opencode" and ds["headless_first"][0] == "opencode"
      and ds["headless"][0] == "opencode"
      and "claude" not in ds["cmd"] + ds["headless_first"] + ds["headless"])
check("the model is named on the command line of both turns and of the "
      "interactive sitting, because this machine's opencode default is another "
      "provider",
      all(t[t.index("-m") + 1] == "deepseek/deepseek-flash"
          for t in (ds["cmd"], ds["headless_first"], ds["headless"])))
check("and it is the model the vision route reads with, so a rename is one "
      "id in two places that a test holds together",
      ds["headless_first"][ds["headless_first"].index("-m") + 1]
      == "deepseek/" + ds["vision"]["model"])
check("it resumes with --continue, and only the resumed turn does",
      "--continue" in ds["headless"] and "--continue" not in ds["headless_first"])
check("no external plugin and no permission prompt: --pure and --auto on both",
      all("--pure" in t and "--auto" in t
          for t in (ds["headless_first"], ds["headless"])))
check("no `--` before the prompt, because `with_usage` appends flags after it",
      "--" not in ds["headless_first"] and "--" not in ds["headless"])
check("it reports what it cost through its own parser",
      ds["usage"] == "opencode-json" and ds["usage_args"] == ["--format", "json"]
      and "opencode-json" in usage.USAGE_PARSERS)
check("it names the key it needs", ds["needs_key"] == "DEEPSEEK_API_KEY")
check("and no ANTHROPIC_* routing is left anywhere in the recipe",
      not any(k.startswith(("ANTHROPIC_", "CLAUDE_CODE_")) for k in ds["env"]))
check("the credential is named rather than written, so the tree holds no key",
      ds["env"]["DEEPSEEK_API_KEY"] == "{DEEPSEEK_API_KEY}")
overlay = __import__("json").loads(ds["env"]["OPENCODE_CONFIG_CONTENT"])
check("the overlay makes keys.env the key OpenCode uses, over a saved login",
      overlay["provider"]["deepseek"]["options"]["apiKey"]
      == "{env:DEEPSEEK_API_KEY}")
check("titles go to DeepSeek too, not to the machine's small model",
      overlay["small_model"] == "deepseek/deepseek-flash")
check("and skills are off: this machine's describe-image skill sends a slate "
      "to another provider", overlay["permission"]["skill"] == "deny")

real_env = runturn.turn_environment(ds, {})
check("the real recipe spends the key through the environment",
      real_env["DEEPSEEK_API_KEY"] == "sk-abc123")
check("and the overlay's own braces pass through keys.fill untouched",
      __import__("json").loads(real_env["OPENCODE_CONFIG_CONTENT"]) == overlay)
check("keys.fill leaves a brace that does not open a bare name alone",
      keys.fill('{"a": "{env:X}"}') == '{"a": "{env:X}"}'
      and keys.fill("{env:X} {DEEPSEEK_API_KEY}") == "{env:X} sk-abc123")

# THE ARGV RULE, ASKED OF THE REAL RECIPE rather than of a stand-in, because
# this is the one that is unrecoverable: `ps` is readable by every account on
# this machine and a leaked key cannot be un-leaked.
real_cmd = usage.with_usage(ds, [a.replace("{prompt}", "hello")
                                 for a in ds["headless"]])
check("and nothing of it reaches the command line",
      not any("sk-abc123" in a or "DEEPSEEK" in a for a in real_cmd))
check("the recipe names the host its turns open",
      ds["egress_probe"] and all(u.startswith("https://api.deepseek.com/")
                                 for u in ds["egress_probe"]))
check("the recipe says WHERE to re-check the model id",
      "huggingface.co" in tutor_src and "deepseek-recipe" in tutor_src)
check("and does not describe the institute's hostname filter as this "
      "machine's", "from here the TLS handshake" not in tutor_src)
check("and the vision block says whether its model has eyes, since an answer "
      "from a blind route is indistinguishable from a transcription",
      ds["vision"]["sighted"] is True)
check("the vision route is the raw OpenAI-format request, independent of the "
      "harness", ds["vision"]["endpoint"].endswith("/v1/chat/completions"))

# ---- and the refusals, on the surfaces that draw them ----------------------
unkeyed_cfg = {"default_agent": "ghost", "agents": {
    "ghost": {"cmd": ["sh"], "headless": ["sh", "-c", "{prompt}"],
              "needs_key": "NOT_A_KEY"}}}
check("an unkeyed recipe cannot take a turn, in the same words a missing "
      "executable cannot",
      "NOT_A_KEY" in (recipes.agent_unavailable(unkeyed_cfg, "ghost") or ""))
check("and the daemon refuses to start on one rather than listening and "
      "failing every turn into a log",
      "needs the key %s" in tutor_src)

print("%d FAILURES" % len(fails) if fails
      else "a provider is a recipe plus a key, and neither is in the tree")
sys.exit(1 if fails else 0)
