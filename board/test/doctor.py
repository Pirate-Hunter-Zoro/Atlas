#!/usr/bin/env python3
"""`tutor doctor` proves a built-in recipe, and says so one line a check.

    python3 test/doctor.py

The provider is faked: an `opencode` on PATH that speaks OpenCode's
`--format json` event stream, and an OpenAI-format endpoint on 127.0.0.1 for
the `vision` route. The rules underneath:

  - THE BUILT-IN RECIPE IS WHAT IS PROVED, and a machine copy that shadows it
    is named rather than tested.
  - A TURN REACHES THE HARNESS THE WAY THE DAEMON SENDS IT: the model on the
    command line, the key from `keys.env` through the environment, `PWD` equal
    to the directory the turn runs in.
  - WHAT RAN IS READ FROM THE SESSION, not the argv: `opencode export` names
    every answer's provider, and one that is not deepseek-flash fails. A
    resume with no session id is not the same session, and a check.py the
    turn rewrote is not doctor's check.
  - THE INTERACTIVE SITTING IS PINNED LIKE A TURN: the TUI with `--pure`,
    `-m`, the opener as `--prompt`, and the recipe's env.
  - AN IMAGE READ PROVES NOTHING IF ANOTHER TOOL COULD HAVE READ IT. Check 4a
    fails a turn that shelled out, whatever digits it brought back.
  - ONE FAILURE IS EXIT 1, with the provider's own sentence on the line, and
    the workspace is kept for reading.
"""

import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

os.environ.setdefault("BOARD_STATE_DIR", tempfile.mkdtemp(prefix="doctor-state-"))
os.environ.setdefault("BOARD_NODE_NAME", "test-node")
os.environ.setdefault("BOARD_NO_TAILNET", "1")

from tutorboard import keys, paths, seeing                     # noqa: E402

loader = importlib.machinery.SourceFileLoader("tutor", os.path.join(ROOT, "bin", "tutor"))
spec = importlib.util.spec_from_loader("tutor", loader)
tutor = importlib.util.module_from_spec(spec)
loader.exec_module(tutor)
from tutorboard.agents import doctor as agentdoctor  # noqa: E402
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


box = tempfile.mkdtemp(prefix="doctor-test-")

# ---- the fake harness -------------------------------------------------------
FAKE = r'''#!/usr/bin/env python3
import json, os, re, sys, time
argv = sys.argv[1:]
mode = os.environ.get("FAKE_MODE", "good")
state = os.environ["FAKE_STATE"]
cwd = os.getcwd()
with open(os.path.join(state, "argv.jsonl"), "a") as fh:
    fh.write(json.dumps(argv) + "\n")

# `opencode export <session>`: what the session's own record says answered.
if "export" in argv:
    sid = argv[argv.index("export") + 1]
    if not os.path.isfile(os.path.join(state, "answered-" + sid)):
        sys.exit("Session not found: " + sid)
    who = open(os.path.join(state, "answered-" + sid)).read().split()
    print(json.dumps({"info": {"id": sid}, "messages": [
        {"info": {"role": "user", "model": {"providerID": "deepseek",
                                             "modelID": "deepseek-flash"}}}] + [
        {"info": {"role": "assistant", "providerID": w.split("/")[0],
                  "modelID": w.split("/")[1]}} for w in who]}))
    sys.exit(0)

def emit(kind, sid, **kw):
    kw.update({"type": kind, "timestamp": int(time.time() * 1000),
               "sessionID": sid})
    print(json.dumps(kw))
    sys.stdout.flush()

wrong = []
if os.path.realpath(os.environ.get("PWD", "")) != os.path.realpath(cwd):
    wrong.append("PWD is not the turn's directory")
if "-m" not in argv or argv[argv.index("-m") + 1] != "deepseek/deepseek-flash":
    wrong.append("no -m deepseek/deepseek-flash")
if argv[-2:] != ["--format", "json"]:
    wrong.append("no --format json")
if os.environ.get("DEEPSEEK_API_KEY") != os.environ.get("FAKE_KEY"):
    wrong.append("the key is not keys.env's")
if "{env:DEEPSEEK_API_KEY}" not in os.environ.get("OPENCODE_CONFIG_CONTENT", ""):
    wrong.append("no config overlay")
if mode == "noauth":
    wrong.append("Authentication Fails, Your api key: ****fake is invalid")
if wrong:
    emit("error", "ses_bad", error={"name": "APIError",
                                    "data": {"message": "; ".join(wrong)}})
    sys.exit(1)

prompt = [a for a in argv if " " in a][0]
last = os.path.join(state, "last-session")
if "--continue" in argv:
    sid = open(last).read().strip()
else:
    sid = "ses_%d" % len(os.listdir(state))
    open(last, "w").write(sid)
# What the session's record will say answered this turn. `astray` puts one
# answer on another provider, as a default model in opencode.jsonc would.
with open(os.path.join(state, "answered-" + sid), "a") as fh:
    fh.write("deepseek/deepseek-flash\n")
    if mode == "astray" and "coding tools" in [a for a in argv if " " in a][0]:
        fh.write("openrouter/some-free-model\n")
real = sid
if mode == "nosid" and "--continue" in argv:
    sid = ""

def step():
    emit("step_finish", sid, part={"type": "step-finish", "cost": 0.5,
         "tokens": {"total": 1060, "input": 1000, "output": 40,
                    "reasoning": 20, "cache": {"read": 0, "write": 0}}})

def tool(name, **inp):
    emit("tool_use", sid, part={"type": "tool", "tool": name,
         "state": {"status": "completed", "input": inp, "output": "ok"}})

def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w").write(text)

if "code word for later" in prompt:
    word = re.search(r"conversation: (\S+?)\.", prompt).group(1)
    open(os.path.join(state, "word-" + sid), "w").write(word)
    write("live/cards/001.md", "Hello.\n")
    tool("write", filePath=os.path.join(cwd, "live/cards/001.md"))
    step()
    emit("text", sid, part={"type": "text", "text": "Done."})
elif "What code word" in prompt:
    word = open(os.path.join(state, "word-" + real)).read()
    emit("text", sid, part={"type": "text",
                            "text": word if mode != "forget" else "no idea"})
elif "coding tools" in prompt:
    n = int(re.search(r"sum.py to (\d+)", prompt).group(1))
    write("sum.py", "print(sum(range(1, 11)))\n")
    tool("write", filePath="sum.py")
    tool("bash", command="python3 sum.py")
    write("sum.py", "print(sum(range(1, %d)))\n" % (n + 1))
    tool("edit", filePath="sum.py")
    write("out.txt", "%d\n" % (n * (n + 1) // 2 if mode != "cheat" else 0))
    tool("bash", command="python3 sum.py > out.txt")
    if mode == "cheat":
        write("check.py", "print('PASS')\n")
        tool("write", filePath="check.py")
    step()
elif "image reading" in prompt:
    if mode == "shellout":
        tool("bash", command="curl https://elsewhere.example/v1/vision")
    else:
        if mode == "looks":
            tool("glob", pattern="*.png")
        tool("read", filePath=os.path.join(cwd, "slate.png"))
    write("seen.txt", os.environ["FAKE_SLATE"] if mode != "blind" else "CANNOT")
    tool("write", filePath="seen.txt")
    step()
step()
'''
fake_bin = os.path.join(box, "bin")
os.makedirs(fake_bin)
with open(os.path.join(fake_bin, "opencode"), "w", encoding="utf-8") as fh:
    fh.write(FAKE.replace("#!/usr/bin/env python3", "#!" + sys.executable, 1))
os.chmod(os.path.join(fake_bin, "opencode"), 0o755)
os.environ["PATH"] = fake_bin + os.pathsep + os.environ.get("PATH", "")

# ---- the fake endpoint: answers the witness with the codes the test drew ----
CODES = {}


class Mock(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(n)
        CODES["auth"] = self.headers.get("Authorization")
        try:
            CODES["text"] = json.loads(body)["messages"][0]["content"][0]["text"]
        except (ValueError, KeyError, IndexError, TypeError):
            pass
        out = json.dumps({"choices": [{"message": {"content": "CODE: %s\n%s" % (
            CODES.get("strip"), CODES.get("page"))}}]}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), Mock)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = "http://127.0.0.1:%d" % srv.server_address[1]

ds = recipes.DEFAULT_CONFIG["agents"]["deepseek"]
ds["egress_probe"] = [url + "/chat/completions"]
ds["vision"]["endpoint"] = url + "/v1/chat/completions"

paths.KEYS = os.path.join(box, "keys.env")
with open(paths.KEYS, "w", encoding="utf-8") as fh:
    fh.write("DEEPSEEK_API_KEY=sk-fake\n")
os.chmod(paths.KEYS, 0o600)
keys.forget()
os.environ["FAKE_KEY"] = "sk-fake"

# A machine copy that shadows the built-in, as this Mac's config does.
recipes.CONFIG_DIR = os.path.join(box, "config")
recipes.CONFIG = os.path.join(recipes.CONFIG_DIR, "config.json")
os.makedirs(recipes.CONFIG_DIR)
with open(recipes.CONFIG, "w", encoding="utf-8") as fh:
    json.dump({"agents": {"deepseek": {"cmd": ["claude"]}}}, fh)
cfg = recipes.load_config()

real_code = seeing._code


def doctor(mode="good", args=()):
    """One run against the fake. `(exit, output)`."""
    state = tempfile.mkdtemp(prefix="fake-state-", dir=box)
    os.environ["FAKE_STATE"] = state
    os.environ["FAKE_MODE"] = mode
    drawn = iter(["111-222", "333-444", "555-666"])
    CODES.update(slate="111-222", page="333-444", strip="555-666")
    os.environ["FAKE_SLATE"] = "111222"
    seeing._code = lambda: next(drawn)
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = agentdoctor.cmd_doctor(cfg, list(args))
    finally:
        seeing._code = real_code
    return code, out.getvalue(), state


def kept(text):
    got = re.search(r"workspace kept: (\S+)", text)
    return got.group(1) if got else None


# ---- every check green -------------------------------------------------------
code, said, state = doctor()
lines = [l for l in said.splitlines() if l.startswith(("PASS", "FAIL"))]
check("a good provider passes all six lines and exits 0",
      code == 0 and len(lines) == 6 and all(l.startswith("PASS") for l in lines))
check("the header names what the recipe asks for",
      "which asks for opencode -m deepseek/deepseek-flash" in said)
check("each turn's line names the route its session export recorded, not the "
      "argv", all(re.search(r"opencode -> deepseek/deepseek-flash in ses_\d", l)
                  for l in lines if " 4b " not in l and " 5 " not in l)
      and "seeing.ask -> 127.0.0.1 deepseek-flash" in said)
check("the session was read back with opencode export",
      any(json.loads(l)[1:2] == ["export"]
          for l in open(os.path.join(state, "argv.jsonl"))))
check("the resumed turn says --continue and recalls turn 1's word in turn 1's "
      "session", "--continue: recalled turn 1's code word in session ses_" in said)
check("the coding turn's workspace check passed and its tools are named",
      "workspace check passed; tools write, bash, edit, bash" in said)
check("4a read the slate with its own read tool",
      "read 111-222 off slate.png; tools read, write" in said)
check("4b read the witness off the strip, and the code was not in the prompt",
      "witness 555-666 read back" in said
      and "555666" not in re.sub(r"\D", "", CODES.get("text", "")))
check("and the key reached the endpoint on the header", CODES.get("auth") == "Bearer sk-fake")
check("usage was summed per round trip and priced off the recipe's table, not "
      "OpenCode's own figure", re.search(r"4 turns, [\d.]+k tokens, \$0\.0", said)
      is not None)
check("tutor cost on the workspace is printed beneath", "tutor cost " in said
      and "tokens in total" in said)
check("the machine copy that shadows the built-in is named",
      "holds its own copy of `deepseek` (cmd differ)" in said)
check("and the BUILT-IN recipe ran, not that copy",
      all(json.loads(l)[0] == "--pure"
          for l in open(os.path.join(state, "argv.jsonl"))))
check("a passing run leaves no workspace behind", kept(said) is None
      and "all 6 checks passed" in said)

# ---- looking for the slate first sends nothing anywhere ----------------------
code, said, _ = doctor("looks")
check("a turn that lists files before its own read still passes 4a",
      re.search(r"^PASS  4a ", said, re.M) is not None)
ws = kept(said)
if ws:
    shutil.rmtree(os.path.dirname(ws), ignore_errors=True)

# ---- the image read that proves nothing --------------------------------------
code, said, _ = doctor("shellout")
check("a turn that shells out for the image fails 4a, though its digits are right",
      code == 1 and re.search(r"^FAIL  4a .*used bash besides its own read",
                              said, re.M) is not None)
ws = kept(said)
check("a failing run keeps its workspace and says where", ws and os.path.isdir(ws))
if ws:
    shutil.rmtree(os.path.dirname(ws), ignore_errors=True)

code, said, _ = doctor("forget")
check("a resumed turn that forgot fails 3 and nothing else",
      code == 1 and re.search(r"^FAIL  3 ", said, re.M) is not None
      and said.count("FAIL") == 1)
if kept(said):
    shutil.rmtree(os.path.dirname(kept(said)), ignore_errors=True)

code, said, _ = doctor("astray")
check("a turn whose session holds an answer from another provider fails, "
      "though its work is right",
      code == 1 and re.search(r"^FAIL  2 .*opencode -> deepseek/deepseek-flash, "
                              r"openrouter/some-free-model in ses_\d+: 1 of 2 "
                              r"answers came from openrouter/some-free-model",
                              said, re.M) is not None
      and said.count("FAIL") == 1)
if kept(said):
    shutil.rmtree(os.path.dirname(kept(said)), ignore_errors=True)

code, said, _ = doctor("nosid")
check("a resume that reports no session id fails 3 with a clear line, not as "
      "the same session",
      code == 1 and re.search(r"^FAIL  3 .*cannot tell whether it resumed turn "
                              r"1: turn 3 reported no session id", said, re.M)
      is not None and said.count("FAIL") == 1)
if kept(said):
    shutil.rmtree(os.path.dirname(kept(said)), ignore_errors=True)

code, said, _ = doctor("cheat")
check("a coding turn that rewrites check.py fails 2, though the check says PASS",
      code == 1 and re.search(r"^FAIL  2 .*check.py is not the file doctor "
                              r"wrote", said, re.M) is not None
      and said.count("FAIL") == 1)
if kept(said):
    shutil.rmtree(os.path.dirname(kept(said)), ignore_errors=True)

code, said, _ = doctor("noauth")
check("a provider error is the provider's own sentence on the line, not `exit 1`",
      code == 1 and re.search(r"^FAIL  1 .*Authentication Fails", said, re.M)
      is not None)
if kept(said):
    shutil.rmtree(os.path.dirname(kept(said)), ignore_errors=True)

# ---- refused before a turn is spent -----------------------------------------
with open(paths.KEYS, "w", encoding="utf-8") as fh:
    fh.write("OTHER=1\n")
os.chmod(paths.KEYS, 0o600)
keys.forget()
code, said, _ = doctor()
check("an unkeyed recipe fails every check in one line and runs no turn",
      code == 1 and "FAIL  every check: DEEPSEEK_API_KEY is not in" in said
      and "PASS" not in said)
with contextlib.redirect_stderr(io.StringIO()):
    refused = agentdoctor.cmd_doctor(cfg, ["nobody"])
check("an unknown recipe is refused", refused == 2)

# ---- the pieces underneath ---------------------------------------------------
stream = "\n".join([
    "not json",
    json.dumps({"type": "step_finish", "sessionID": "s1", "part": {
        "tokens": {"input": 100, "output": 10, "reasoning": 5,
                   "cache": {"read": 1000, "write": 7}}, "cost": 0.25}}),
    json.dumps({"type": "text", "sessionID": "s1", "part": {"text": "hi"}}),
    json.dumps({"type": "step_finish", "sessionID": "s1", "part": {
        "tokens": {"input": 50, "output": 1, "reasoning": 0,
                   "cache": {"read": 0, "write": 0}}, "cost": 0.25}}),
])
u = usage.read_opencode_usage(stream)
check("the opencode parser sums every round trip and counts reasoning as output",
      u["in"] == 150 and u["out"] == 16 and u["cache_read"] == 1000
      and u["cache_write"] == 7 and u["tokens"] == 1173 and u["requests"] == 2
      and u["session"] == "s1" and u["usd"] == 0.5)
check("and a stream with no step_finish reports nothing", usage.read_opencode_usage("x") == {})
check("turn_text is the model's words, not the tools' output", usage.turn_text(stream) == "hi")
check("an error event is read for the failure reason",
      usage.failure_reason('{"type":"error","sessionID":"s","error":{"data":'
                           '{"message":"Insufficient Balance"}}}', "exit 1")
      == "Insufficient Balance (exit 1)")
check("a turn's PWD is the directory it runs in",
      runturn.at_root("/tmp/x", {"PWD": "/elsewhere"})["PWD"] == "/tmp/x")

check("a row priced at exactly $0.0 is priced",
      agentdoctor.doctor_priced({"rate": {"window": "off"}, "usd": 0.0}))
check("a row with no usd, or a non-number, is not",
      not agentdoctor.doctor_priced({"rate": {"window": "off"}})
      and not agentdoctor.doctor_priced({"rate": {"window": "off"}, "usd": None})
      and not agentdoctor.doctor_priced({"rate": {"window": "off"}, "usd": True})
      and not agentdoctor.doctor_priced({"usd": 0.1}))
check("a turn's session id is read from OpenCode, Claude and Codex output",
      agentdoctor.turn_session('{"type":"text","sessionID":"ses_a"}') == "ses_a"
      and agentdoctor.turn_session('{"type":"result","session_id":"u-1"}') == "u-1"
      and agentdoctor.turn_session('{"type":"thread.started","thread_id":"t"}') == "t"
      and agentdoctor.turn_session('{"type":"text","sessionID":""}') == "")

# `tutor cost` on unpriced turns says so instead of $0.00.
plain = os.path.join(box, "plain")
os.makedirs(os.path.join(plain, "live"))
with open(os.path.join(plain, "live", "cost.jsonl"), "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"tokens": 10, "requests": 1, "usd": 0.0,
                         "agent": "codex"}) + "\n")
out = io.StringIO()
with contextlib.redirect_stdout(out):
    tutor.cmd_cost(cfg, [plain])
check("tutor cost takes a directory, and an unpriced turn is not $0.00",
      "no price table — tokens only" in out.getvalue()
      and "$0.00" not in out.getvalue())

srv.shutdown()
shutil.rmtree(box, ignore_errors=True)
print("%d FAILURES" % len(fails) if fails
      else "the built-in recipe is proved against its provider, one line a check")
sys.exit(1 if fails else 0)
