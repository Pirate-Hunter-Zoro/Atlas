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
            "endpoint": "https://example.test/v1/chat/completions",
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
        out = json.dumps({"choices": [
            {"message": {"content": " a page of handwriting "}}]}).encode()
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
    check("the question and the image go in one message",
          [c["type"] for c in content] == ["text", "image_url"])
    check("and the bytes that arrive are the bytes that were on disk",
          base64.b64decode(content[1]["image_url"]["url"].split(",", 1)[1])
          == open(page, "rb").read())

    seen.clear()
    bad = dict(LOCAL, agents=[{"name": "deepseek", "vision": {
        "endpoint": "http://127.0.0.1:1/v1/chat", "model": "m",
        "needs_key": "A_KEY"}}])
    check("an endpoint that cannot be reached is a sentence, not a traceback",
          "could not be reached" in refusal(path=page, table=bad, root=box,
                                            agent="deepseek"))
finally:
    srv.shutdown()

# ---- and the promise the briefs make is now a thing that exists ------------
tutor_src = open(os.path.join(ROOT, "bin", "tutor"), encoding="utf-8").read()
board_src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
check("no prompt on this board tells a model to call a tool that does not exist",
      "describe_image" not in tutor_src)
check("they name `board see` instead", "board see" in tutor_src)
check("and `board see` is a command", '"see": cmd_see' in board_src)

print("%d FAILURES" % len(fails) if fails
      else "a model with no eyes can read the page, and not the fenced one")
sys.exit(1 if fails else 0)
