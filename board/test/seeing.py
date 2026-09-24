#!/usr/bin/env python3
"""`board see` -- what is in this image, for a model with no eyes.

    python3 test/seeing.py

Every tutor on this board is told on its first turn to open whatever the student
sent: handwriting is a PNG and a problem sheet a PDF. A model without vision
cannot, and this is what it calls instead.

THE FIRST ASSERTION IS THE FENCE AND IT IS THE ONLY ONE THAT MATTERS MORE THAN
THE FEATURE. This command sends a file to a hosted provider, and a board
subcommand does not go through any assistant's pre-tool hook -- so the refusal
lives in the command, before a byte is read. Get it wrong and the tool has grown
a documented route for sending session content to a third party.

The second is the one that made it useful rather than theoretical: the slate
pages this exists to read live in the board's own `live/inbox/`, and the
any-depth fence rule refused every one of them. A fence is a top-level directory
of the workspace that holds it; `phi` alone is refused wherever it appears.

What a provider says back is the provider's business. Everything on this side of
the wire is checked, against a socket on this machine: the key on the header
rather than in the body, the model the recipe names, and the image arriving as
the bytes that were on disk.
"""

import base64
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

os.environ.setdefault("BOARD_STATE_DIR", tempfile.mkdtemp(prefix="see-state-"))
os.environ.setdefault("BOARD_NODE_NAME", "test-node")
os.environ.setdefault("BOARD_NO_TAILNET", "1")

from tutorboard import fenced, keys, paths, seeing            # noqa: E402

# THE WITNESS CODE IS PINNED HERE, and this is the only place it is. `ask`
# draws six digits into the image and requires them back, which is exactly the
# thing a stub route cannot do by accident -- so the stubs are told what to say
# and the guard itself is tested by giving the wrong answer on purpose.
CODE = "424-242"
seeing._code = lambda: CODE

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def refusal(**kw):
    """What `describe` refused with, or "" if it did not refuse."""
    try:
        seeing.describe(**kw)
        return ""
    except seeing.Refused as exc:
        return str(exc)


# ---- the fence, first -------------------------------------------------------
box = tempfile.mkdtemp(prefix="see-ws-")
for d in ("live/inbox/uploads", "live/slate", "phi", "inbox", "chapters/ch07/build"):
    os.makedirs(os.path.join(box, d), exist_ok=True)


def put(rel):
    p = os.path.join(box, rel)
    with open(p, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
    return p


sent = put("phi/page.png")
said = refusal(path=sent, root=box)
check("A FENCED PATH IS REFUSED BEFORE A BYTE IS READ", bool(said))
check("and the refusal names the directory, so it is something to act on",
      "phi" in said)
check("and says why, because this is the one refusal a person must not route "
      "around", "hosted provider" in said)

check("a fenced directory of the workspace is refused too",
      bool(refusal(path=put("inbox/thing.png"), root=box)))
check("`phi` anywhere at all is refused, whichever workspace is asking",
      fenced.refused_in(box, "/somewhere/else/phi/x.png") == "phi")
check("and a path in another workspace falls back to the any-depth rule, "
      "which is the conservative answer for one nothing here can place",
      fenced.refused_in(box, "/another/box/stage1/x.png") == "stage1")

# ---- and the thing it exists to read ---------------------------------------
check("A SLATE PAGE IS NOT FENCED. Every upload lands in the board's own "
      "`live/inbox/`, and the any-depth rule refused the one kind of file this "
      "command is for",
      fenced.refused_in(box, os.path.join(box, "live/inbox/uploads/p.png")) is None)
check("nor is the slate directory",
      fenced.refused_in(box, os.path.join(box, "live/slate/p.png")) is None)
check("nor a build directory six levels down that happens to be called data",
      fenced.refused_in(box, os.path.join(box, "chapters/ch07/build/data/f.png"))
      is None)

# ---- what it will and will not open ----------------------------------------
check("a path that is not there says so",
      "no file at" in refusal(path=os.path.join(box, "nope.png"), root=box))
check("and a file that is neither an image nor a PDF is refused by kind",
      "neither an image nor a PDF"
      in refusal(path=put("live/slate/notes.txt"), root=box))

# ---- where the image goes is a recipe field --------------------------------
TABLE = {
    "default": "claude", "vision_agent": "deepseek",
    "agents": [
        {"name": "claude", "vision": None},
        {"name": "colibri", "vision": None},
        {"name": "deepseek", "vision": {
            "endpoint": "https://api.deepseek.com/v1/chat/completions",
            "model": "a-model", "needs_key": "A_KEY"}},
    ],
}
got, why = seeing.route("colibri", TABLE)
check("an assistant with no eyes falls through to `vision_agent`",
      got and got["agent"] == "deepseek")
got, why = seeing.route("deepseek", TABLE)
check("and one that names its own route is asked first",
      got and got["agent"] == "deepseek")
none = {"default": "claude", "agents": [{"name": "claude", "vision": None}]}
got, why = seeing.route("claude", none)
check("a machine with no route at all says so rather than tracebacking",
      got is None and "vision" in (why or ""))

# ---- a route through a provider that is stood down is not a route ----------
# The hostname that drops a tutor's turns drops its vision request, and a failed
# turn has already written that down. Sending a page at it to find out again is
# the handwriting fallback failing slowly for a reason already known.
from tutorboard.net import egress                                # noqa: E402
egress.mark_unreachable("deepseek", "api.deepseek.com")
CMD_TABLE = {
    "default": "claude", "vision_agent": "deepseek",
    "agents": [
        {"name": "claude", "vision": {"cmd": ["claude", "-p", "{prompt}"],
                                      "model": "its own"}},
        {"name": "colibri", "vision": None},
        {"name": "deepseek", "vision": {
            "endpoint": "https://api.deepseek.com/v1/chat/completions",
            "model": "a-model", "needs_key": "A_KEY"}},
    ],
}
got, why = seeing.route("colibri", CMD_TABLE)
check("a provider that is stood down is passed over, and the next name on the "
      "list answers", got and got["agent"] == "claude")
got, why = seeing.route("colibri", TABLE)
check("and where that leaves nothing, the refusal names the host that went "
      "dark rather than sending the page at it",
      got is None and "api.deepseek.com" in (why or ""))

# AND THE STAND-DOWN IS ABOUT A HOST, NOT ABOUT A NAME. A command route no
# longer opens the provider's hostname -- `ROUTING` is scrubbed out of its
# environment -- so an agent whose TURNS are stood down still has working eyes,
# and skipping it on the strength of the name would report "no vision route on
# this machine can be used" with one sitting on the path.
OTHER_HOST = {
    "default": "claude", "vision_agent": "deepseek",
    "agents": [
        {"name": "claude", "vision": None},
        {"name": "colibri", "vision": None},
        {"name": "deepseek", "vision": {
            "endpoint": "https://vision.elsewhere.test/v1/chat/completions",
            "model": "a-model", "needs_key": "A_KEY"}},
    ],
}
got, why = seeing.route("colibri", OTHER_HOST)
check("a recipe stood down for one host still routes through an endpoint on a "
      "different one, because the block is on the name that was dropped and not "
      "on the provider's whole recipe",
      got and got["agent"] == "deepseek")
got, why = seeing.route("claude", CMD_TABLE)
check("and a COMMAND route is never skipped for its agent's stand-down: it "
      "runs the binary on this machine with the routing scrubbed, so it is not "
      "the provider that went dark",
      got and got["agent"] == "claude")

# AND A ROUTE THAT SAYS IT CANNOT SEE IS NEVER HANDED A PAGE, because an answer
# from a blind route is indistinguishable from a transcription.
BLIND = {"default": "claude", "agents": [
    {"name": "claude", "vision": {"cmd": ["claude"], "model": "m",
                                  "sighted": False}}]}
got, why = seeing.route("claude", BLIND)
check("a `vision` block that declares its model blind is not a route",
      got is None and "cannot take an image" in (why or ""))

egress.clear_unreachable("deepseek")
got, why = seeing.route("colibri", CMD_TABLE)
check("with nothing stood down the recipe named in `vision_agent` still wins",
      got and got["agent"] == "deepseek")

# ---- and a route may be a command rather than an endpoint ------------------
# A sighted assistant that is already installed needs no second provider, no
# second key and no model name that goes stale.
got, why = seeing.route("claude", CMD_TABLE)
check("a recipe whose eyes are a command is a route like any other",
      got and got["cmd"][0] == "claude" and not got.get("endpoint"))
page = put("live/slate/page.png")
saw = ["sh", "-c", "echo \"$1\" >&2; echo \"CODE: %s\"; echo SAW" % CODE,
       "sh", "{prompt}"]
said = seeing.ask({"agent": "stub", "cmd": saw}, [page], "what is this")
check("the command's stdout is the answer, with the code line taken off the "
      "front because the card is written from what is left", said == "SAW")
try:
    seeing.ask({"agent": "stub", "cmd": ["sh", "-c", "exit 3"]}, [page], "q")
    said = ""
except seeing.Refused as exc:
    said = str(exc)
check("and a command that says nothing about the page is a refusal rather than "
      "an empty description", "exited 3" in said)

# ---- AND AN ANSWER IS NOT BELIEVED BECAUSE IT ARRIVED ----------------------
#
# The worst failure this file has is a confident paragraph about a page nobody
# looked at: exit 0, non-empty stdout, a card written off it. Reproduced on this
# machine with the real binary and its file-reading tools removed -- "I can't
# transcribe it, this session has no file-reading tool" came back exit 0. So
# every request carries a code that is in the IMAGE and nowhere else.
try:
    seeing.ask({"agent": "stub", "cmd": ["sh", "-c",
               "echo 'A worked solution to problem 3, in blue ink.'"]},
               [page], "q")
    said = ""
except seeing.Refused as exc:
    said = str(exc)
check("AN ANSWER WITHOUT THE CODE IS REFUSED, however certain it sounds -- it "
      "did not read the page", "without the code" in said)
check("and the refusal says what it did say, so the cause is findable rather "
      "than guessed at", "worked solution" in said)
try:
    seeing.ask({"agent": "stub", "cmd": ["sh", "-c",
               "echo 'CODE: %s'; echo '[Unsupported Image]'" % CODE]},
               [page], "q")
    said = ""
except seeing.Refused as exc:
    said = str(exc)
check("and the provider's own words for a model that cannot see are read as "
      "the failure they are, rather than transcribed onto a card",
      "[Unsupported Image]" in said and "does not take image input" in said)

# ---- the code is in the image, and the image is what is sent ---------------
shown = []
seeing.ask({"agent": "stub", "cmd": ["sh", "-c",
           "ls >&2; echo \"CODE: %s\"; echo fine" % CODE]}, [page], "q")
strip = seeing._token_png(CODE, os.path.join(box, "strip.png"))
check("the code strip is a real PNG, drawn here with no renderer and no TeX, "
      "so the guard cannot quietly stop being run on a machine without either",
      open(strip, "rb").read(8) == b"\x89PNG\r\n\x1a\n"
      and os.path.getsize(strip) > 100)
check("and the code is nowhere in the prompt, which is the whole of why an "
      "answer carrying it proves something",
      CODE not in seeing.DEFAULT_ASK + seeing.WITNESS_ASK
      and seeing.witnessed("CODE: 424242 and then a page", CODE)
      and not seeing.witnessed("a page of handwriting", CODE))

# ---- a command route runs WITHOUT the sitting's provider routing ------------
#
# `board see` is run by the tutor's own Bash tool, inside a turn whose
# environment the running recipe wrote. Inheriting it pointed claude's vision
# route at api.deepseek.com -- the provider it is the fallback FROM. Measured:
# 14.4 s and a transcription clean, 180 s and a refusal with the variables on.
os.environ["ANTHROPIC_BASE_URL"] = "https://api.deepseek.test/anthropic"
os.environ["ANTHROPIC_MODEL"] = "deepseek-flash"
os.environ["BOARD_SEE_KEEPS_THIS"] = "yes"
said = seeing.ask({"agent": "claude", "cmd": ["sh", "-c",
                   "echo \"CODE: %s\"; echo \"base=[${ANTHROPIC_BASE_URL-unset}] "
                   "keep=[${BOARD_SEE_KEEPS_THIS-unset}]\"" % CODE]},
                  [page], "q")
check("THE ROUTING VARIABLES ARE NOT INHERITED, so the binary the recipe calls "
      "its own eyes is the binary on this machine and not the provider that "
      "just went dark", "base=[unset]" in said)
check("and nothing else about the environment is disturbed, because a scrub "
      "that took the PATH with it would be a worse bug than the one it fixes",
      "keep=[yes]" in said)
said = seeing.ask({"agent": "claude", "cmd": ["sh", "-c",
                   "echo \"CODE: %s\"; echo \"base=[${ANTHROPIC_BASE_URL-unset}]\"" % CODE],
                   "env": {"ANTHROPIC_BASE_URL": "https://on.purpose.test"}},
                  [page], "q")
check("and a recipe that genuinely wants one of them says so on its own vision "
      "block, so the rule lives beside the command",
      "base=[https://on.purpose.test]" in said)
del os.environ["ANTHROPIC_BASE_URL"], os.environ["ANTHROPIC_MODEL"]
del os.environ["BOARD_SEE_KEEPS_THIS"]

# ---- an unkeyed machine says which line to add -----------------------------
paths.KEYS = os.path.join(box, "no-such-keys.env")
keys.forget()
said = refusal(path=put("live/slate/page.png"), root=box, table=TABLE)
check("with no key there is nothing to authenticate with, and the message "
      "names the key and the file rather than failing at the endpoint",
      "A_KEY" in said and "no-such-keys.env" in said)

# ---- the request itself, against a socket on this machine ------------------
#
# The endpoint is somebody else's and is not called here. Everything on THIS
# side of the wire is: the key on the header rather than in the body, the model
# the recipe names, the question and the image in one message, and the bytes
# arriving as the bytes that were on disk. A base64 data URL is the kind of
# thing that is wrong by one encoding step and looks fine.
seen = {}


class Mock(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        seen["body"] = json.loads(self.rfile.read(n))
        seen["auth"] = self.headers.get("Authorization")
        # It answers with the code because the test pinned it, which is the
        # one thing a socket on 127.0.0.1 cannot read off a PNG. Everything
        # else about the witness is exercised against a real command above.
        out = json.dumps({"choices": [
            {"message": {"content": "CODE: %s\n a page of handwriting "
                                    % CODE}}]}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


paths.KEYS = os.path.join(box, "keys.env")
with open(paths.KEYS, "w", encoding="utf-8") as fh:
    fh.write("A_KEY=sk-test\n")
os.chmod(paths.KEYS, 0o600)
keys.forget()

srv = HTTPServer(("127.0.0.1", 0), Mock)
threading.Thread(target=srv.serve_forever, daemon=True).start()
LOCAL = dict(TABLE, agents=[{"name": "deepseek", "vision": {
    "endpoint": "http://127.0.0.1:%d/v1/chat/completions" % srv.server_address[1],
    "model": "a-model", "needs_key": "A_KEY"}}])
page = put("live/slate/handwriting.png")
try:
    said, settings = seeing.describe(page, table=LOCAL, root=box,
                                     agent="deepseek")
    check("the answer comes back as text a card can be written from",
          said == "a page of handwriting")
    check("THE KEY IS ON THE HEADER, never in the body and never on a command "
          "line", seen["auth"] == "Bearer sk-test"
          and "sk-test" not in json.dumps(seen["body"]))
    check("the model is the one the recipe names, not the endpoint's default",
          seen["body"]["model"] == "a-model")
    content = seen["body"]["messages"][0]["content"]
    check("the question, the code strip and the page go in one message, the "
          "strip first because the answer is asked to open with it",
          [c["type"] for c in content] == ["text", "image_url", "image_url"])
    check("and the bytes that arrive are the bytes that were on disk",
          base64.b64decode(content[2]["image_url"]["url"].split(",", 1)[1])
          == open(page, "rb").read())
    check("and the code reaches the model only as pixels -- nothing in the "
          "request text says it",
          CODE not in content[0]["text"]
          and CODE.replace("-", "") not in content[0]["text"])

    seen.clear()
    bad = dict(LOCAL, agents=[{"name": "deepseek", "vision": {
        "endpoint": "http://127.0.0.1:1/v1/chat", "model": "m",
        "needs_key": "A_KEY"}}])
    check("an endpoint that cannot be reached is a sentence, not a traceback",
          "could not be reached" in refusal(path=page, table=bad, root=box,
                                            agent="deepseek"))

    # ---- AND THE ROUTE IS RE-ASKED ONCE, ON THE RECORD THE FAILURE WROTE ----
    #
    # `ask` marks a provider unreachable when its endpoint refuses a
    # connection -- and `describe` used to resolve the route once, BEFORE that
    # record existed. So the first `board see` of a DeepSeek sitting always
    # failed, the tutor was handed "api.deepseek.com could not be reached", and
    # nothing told it a second attempt would differ.
    egress.clear_unreachable("deepseek")
    egress.clear_unreachable("claude")
    TWO = {"default": "claude", "vision_agent": "deepseek", "agents": [
        {"name": "deepseek", "vision": {
            "endpoint": "http://127.0.0.1:1/v1/chat", "model": "m",
            "needs_key": "A_KEY"}},
        {"name": "claude", "vision": {"cmd": ["sh", "-c",
            "echo \"CODE: %s\"; echo \"read it\"" % CODE], "model": "its own"}},
    ]}
    said, settings = seeing.describe(page, table=TWO, root=box,
                                     agent="deepseek")
    check("a dead endpoint stands its provider down and the SAME call falls "
          "through to the next route, rather than handing the tutor a refusal "
          "about a host it has no reason to retry",
          said == "read it" and settings["agent"] == "claude")
    check("and the stand-down the attempt wrote is what made that possible",
          (egress.stood_down("deepseek") or {}).get("host") == "127.0.0.1")
    egress.clear_unreachable("deepseek")

    ONE = {"default": "deepseek", "vision_agent": "deepseek", "agents": [
        {"name": "deepseek", "vision": {
            "endpoint": "http://127.0.0.1:1/v1/chat", "model": "m",
            "needs_key": "A_KEY"}}]}
    said = refusal(path=page, table=ONE, root=box, agent="deepseek")
    check("and where there is no second route it refuses once rather than "
          "looping over the only one there is",
          "could not be reached" in said and said.count("could not be reached") == 1)
    egress.clear_unreachable("deepseek")
finally:
    srv.shutdown()

# ---- and the promise the briefs make is now a thing that exists ------------
tutor_src = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
board_src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
check("no prompt on this board tells a model to call a tool that does not exist",
      "describe_image" not in tutor_src)
check("they name `board see` instead", "board see" in tutor_src)
check("and `board see` is a command", '"see": cmd_see' in board_src)

# ---- the page that never arrived, on the path a sighted tutor actually takes -
#
# `board see` refuses a placeholder answer, but a model that can see is told to
# open the PNG itself and never goes through it. So the TURN's output is scanned
# for the same wording, and the two scanners read one list: a second copy of a
# provider's placeholder is a table that goes stale where nobody is looking.
check("a tutor's own turn is scanned for the placeholder, not just `board see`",
      "seeing.blind_answer(said)" in tutor_src)
check("and it is read off seeing's list rather than a second copy in the daemon",
      "PLACEHOLDERS" not in tutor_src.replace("`PLACEHOLDERS`", ""))

for mark in seeing.PLACEHOLDERS:
    check("`%s` in a turn's output is caught" % mark,
          seeing.blind_answer("I read the page. %s It shows a proof." % mark) == mark)
check("a turn that says nothing of the kind is left alone",
      seeing.blind_answer("The page shows Eisenstein at p=3.") is None)
check("and so is a turn that said nothing at all",
      seeing.blind_answer("") is None and seeing.blind_answer(None) is None)
check("the failure names the page rather than the exit code, because the card "
      "it would otherwise write is fluent",
      "the page never reached the model" in tutor_src
      and "invented" in tutor_src)

print("%d FAILURES" % len(fails) if fails
      else "a model with no eyes can read the page, and not the fenced one")
sys.exit(1 if fails else 0)
