#!/usr/bin/env python3
"""The DeepSeek key: where it is read from, and how a turn spends it.

    python3 test/keys.py

keys.env holds it (and Azure's), outside the tree; the shared
`~/.config/api-keys/deepseek_key` file is read when keys.env has none. Three
rules underneath, and each one is here because getting it wrong is silent:

  - A KEY NEVER REACHES ARGV. `ps` output is readable by anything on the
    machine, which is why `ai-config/policy/credentials.txt` exists at all.
    `turn_environment` puts secrets in the environment; the argv carries none.
  - A MACHINE WITH NO KEY CANNOT TAKE A TURN, and says which key and where
    (`recipes.ready`), rather than dying in a log file.
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
paths.DEEPSEEK_KEY = os.path.join(box, "api-keys", "deepseek_key")


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
      keys.unkeyed({"cmd": ["opencode"]}) is None)
check("one whose key is here is not either",
      keys.unkeyed({"needs_key": "DEEPSEEK_API_KEY"}) is None)
check("and one whose key is absent reports the key's NAME, so the refusal "
      "can say which line to add",
      keys.unkeyed({"needs_key": "NOT_A_KEY"}) == "NOT_A_KEY")

# ---- the shared deepseek_key file -------------------------------------------
put("AZURE_SPEECH_KEY=az\n")
os.makedirs(os.path.dirname(paths.DEEPSEEK_KEY))
with open(paths.DEEPSEEK_KEY, "w") as fh:
    fh.write("sk-shared\n")
os.chmod(paths.DEEPSEEK_KEY, 0o600)
keys.forget()
check("with no DeepSeek key in keys.env the shared file is read, stripped",
      keys.get("DEEPSEEK_API_KEY") == "sk-shared" and keys.get("AZURE_SPEECH_KEY") == "az")
put("DEEPSEEK_API_KEY=sk-abc123\n")
check("and keys.env wins when it has one", keys.get("DEEPSEEK_API_KEY") == "sk-abc123")
put("")
os.chmod(paths.DEEPSEEK_KEY, 0o644)
keys.forget()
check("a world-readable shared file is refused like keys.env",
      keys.get("DEEPSEEK_API_KEY") is None)
os.remove(paths.DEEPSEEK_KEY)

# ---- env on a recipe -------------------------------------------------------
plain = {"cmd": ["opencode"]}
check("a recipe with no env leaves the turn's environment as it was, and "
      "marks it a turn so the pre-commit hook guards it",
      runturn.turn_environment(plain, {"A": "1"}) == {"A": "1", "TUTORBOARD_TURN": "1"}
      and runturn.turn_environment(plain).get("TUTORBOARD_TURN") == "1"
      and runturn.turn_environment(plain).get("PATH") == os.environ.get("PATH"))

put("DEEPSEEK_API_KEY=sk-abc123\n")
routed = {"env": {"BASE_URL": "https://example.test",
                  "AUTH_TOKEN": "{DEEPSEEK_API_KEY}"}}
env = runturn.turn_environment(routed, {"COLI_SESSION_ID": "s1"})
check("env reaches the subprocess", env["BASE_URL"] == "https://example.test")
check("with {KEY} substituted", env["AUTH_TOKEN"] == "sk-abc123")
check("and a mission's own variable lands in the SAME dict rather than "
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
check("the reason is written beside the function rather than in a commit "
      "message", "must not reach argv" in tutor_src
      and "credentials.txt" in tutor_src)

# ---- the recipe's half ------------------------------------------------------
ds = recipes.DEEPSEEK
check("deepseek runs through opencode, its own harness",
      ds["headless_first"][0] == "opencode")
check("and the model it reads images with is the model it teaches with, so a "
      "rename is one id in two places that a test holds together",
      ds["headless_first"][ds["headless_first"].index("-m") + 1]
      == "deepseek/" + ds["vision"]["model"])
check("no external plugin and no permission prompt: --pure and --auto",
      "--pure" in ds["headless_first"] and "--auto" in ds["headless_first"])
check("it names the key it needs", ds["needs_key"] == "DEEPSEEK_API_KEY")
check("and no ANTHROPIC_* or CLAUDE_* variable is left anywhere in the recipe",
      not any(k.startswith(("ANTHROPIC_", "CLAUDE_CODE_")) for k in ds["env"]))
check("the credential is named rather than written, so the tree holds no key",
      ds["env"]["DEEPSEEK_API_KEY"] == "{DEEPSEEK_API_KEY}")
overlay = __import__("json").loads(ds["env"]["OPENCODE_CONFIG_CONTENT"])
check("the overlay makes the board's key the one OpenCode uses, over a saved "
      "login", overlay["provider"]["deepseek"]["options"]["apiKey"]
      == "{env:DEEPSEEK_API_KEY}")
check("titles go to deepseek-flash too, not to the machine's small model",
      overlay["small_model"] == "deepseek/deepseek-flash")
check("and skills are off: a turn carries its own brief",
      overlay["permission"]["skill"] == "deny")

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
real_cmd = recipes.argv("hello", ds)
check("and nothing of it reaches the command line",
      not any("sk-abc123" in a or "DEEPSEEK" in a for a in real_cmd))
check("the recipe names the host its turns open",
      ds["egress_probe"] and all(u.startswith("https://api.deepseek.com/")
                                 for u in ds["egress_probe"]))
check("the vision route is the raw OpenAI-format request, independent of the "
      "harness", ds["vision"]["endpoint"].endswith("/chat/completions"))

# ---- and the refusal ----------------------------------------------------------
put("")
os.environ["TUTORBOARD_OPENCODE"] = "sh"
check("a machine with no key cannot take a turn, and says which key and both "
      "places it looked", "DEEPSEEK_API_KEY" in (recipes.ready() or "")
      and paths.KEYS in recipes.ready() and paths.DEEPSEEK_KEY in recipes.ready())
os.environ.pop("TUTORBOARD_OPENCODE", None)

print("%d FAILURES" % len(fails) if fails
      else "the DeepSeek key is read from outside the tree, and never reaches argv")
sys.exit(1 if fails else 0)
