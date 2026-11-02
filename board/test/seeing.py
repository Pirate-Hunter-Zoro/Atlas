#!/usr/bin/env python3
"""`board see` -- what is in this image, in words, through DeepSeek's eyes.

    python3 test/seeing.py

Every tutor on this board is told on its first turn to open whatever the student
sent: handwriting is a PNG and a problem sheet a PDF. `board see` sends it to
the DeepSeek recipe's `vision` block, one chat-completions call.

What DeepSeek says back is DeepSeek's business. Everything on this side of the
wire is checked, against a socket on this machine: the key on the header rather
than in the body, the model the recipe names, and the image arriving as the
bytes that were on disk.
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

from tutorboard import keys, paths, seeing                    # noqa: E402
from tutorboard.agents import recipes                        # noqa: E402
from tutorboard.net import egress                            # noqa: E402

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


box = tempfile.mkdtemp(prefix="see-ws-")
for d in ("live/inbox/uploads", "live/slate"):
    os.makedirs(os.path.join(box, d), exist_ok=True)


def put(rel):
    p = os.path.join(box, rel)
    with open(p, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
    return p


# ---- what it will and will not open ----------------------------------------
check("a path that is not there says so",
      "no file at" in refusal(path=os.path.join(box, "nope.png")))
check("and a file that is neither an image nor a PDF is refused by kind",
      "neither an image nor a PDF"
      in refusal(path=put("live/slate/notes.txt")))

# ---- where the image goes is the recipe's vision block ---------------------
got = seeing.route()
check("the route is DeepSeek's chat-completions endpoint and its sighted model",
      got["endpoint"] == recipes.DEEPSEEK["vision"]["endpoint"]
      and got["model"] == "deepseek-flash"
      and got["needs_key"] == "DEEPSEEK_API_KEY" and got["agent"] == "deepseek")
check("and there is one: no chain, no command routes, no routing scrub",
      not any(hasattr(seeing, n) for n in ("routes", "registry", "ROUTING",
                                           "_ask_command", "_run_command")))

# ---- an unkeyed machine says which line to add -----------------------------
paths.KEYS = os.path.join(box, "no-such-keys.env")
os.environ.pop("DEEPSEEK_API_KEY", None)  # it comes before both files
paths.DEEPSEEK_KEY = os.path.join(box, "no-such-deepseek_key")
keys.forget()
said = refusal(path=put("live/slate/page.png"))
check("with no key there is nothing to authenticate with, and the message "
      "names the key and both files rather than failing at the endpoint",
      "DEEPSEEK_API_KEY" in said and "no-such-keys.env" in said
      and "no-such-deepseek_key" in said)

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
        # `/text-only` refuses an image outright, `/blind` answers 200 with
        # the placeholder for an image it dropped, and `/nocode` answers
        # fluently without having looked.
        if self.path.endswith("/text-only"):
            return self.answer(400, b'{"error": {"message": "image_url is not supported"}}')
        if self.path.endswith("/blind"):
            return self.say("CODE: %s\n[Unsupported Image] I see no image." % CODE)
        if self.path.endswith("/nocode"):
            return self.say("A worked solution to problem 3, in blue ink.")
        # It answers with the code because the test pinned it, which is the
        # one thing a socket on 127.0.0.1 cannot read off a PNG.
        return self.say("CODE: %s\n a page of handwriting " % CODE)

    def say(self, text):
        self.answer(200, json.dumps({"choices": [{"message": {
            "content": text}}]}).encode())

    def answer(self, status, out):
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


paths.KEYS = os.path.join(box, "keys.env")
with open(paths.KEYS, "w", encoding="utf-8") as fh:
    fh.write("DEEPSEEK_API_KEY=sk-test\n")
os.chmod(paths.KEYS, 0o600)
keys.forget()

srv = HTTPServer(("127.0.0.1", 0), Mock)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = "http://127.0.0.1:%d/v1" % srv.server_address[1]


def endpoint(path):
    recipes.DEEPSEEK["vision"]["endpoint"] = base + path


page = put("live/slate/handwriting.png")
try:
    endpoint("/chat/completions")
    said, settings = seeing.describe(page)
    check("the answer comes back as text a card can be written from, with the "
          "code line taken off the front",
          said == "a page of handwriting")
    check("THE KEY IS ON THE HEADER, never in the body and never on a command "
          "line", seen["auth"] == "Bearer sk-test"
          and "sk-test" not in json.dumps(seen["body"]))
    check("the model is the one the recipe names, not the endpoint's default",
          seen["body"]["model"] == "deepseek-flash")
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

    # ---- AN ANSWER IS NOT BELIEVED BECAUSE IT ARRIVED -----------------------
    # The worst failure this file has is a confident paragraph about a page
    # nobody looked at. So every request carries a code that is in the IMAGE
    # and nowhere else.
    endpoint("/nocode")
    said = refusal(path=page)
    check("AN ANSWER WITHOUT THE CODE IS REFUSED, however certain it sounds -- "
          "it did not read the page", "without the code" in said)
    check("and the refusal says what it did say, so the cause is findable "
          "rather than guessed at", "worked solution" in said)
    endpoint("/blind")
    said = refusal(path=page)
    check("and DeepSeek's own words for a model that cannot see are read as the "
          "failure they are, rather than transcribed onto a card",
          "[Unsupported Image]" in said and "does not take image input" in said)
    endpoint("/text-only")
    said = refusal(path=page)
    check("an HTTP error is a sentence with the status in it",
          "400" in said and "image_url is not supported" in said)
    check("and none of those stands DeepSeek down: it answered",
          not egress.stood_down())

    # ---- an endpoint that cannot be reached ---------------------------------
    recipes.DEEPSEEK["vision"]["endpoint"] = "http://127.0.0.1:1/v1/chat"
    said = refusal(path=page)
    check("an endpoint that cannot be reached is a sentence, not a traceback",
          "could not be reached" in said and said.count("could not be reached") == 1)
    check("and the board is told DeepSeek does not answer from here",
          (egress.stood_down() or {}).get("host") == "127.0.0.1")
    egress.clear_unreachable()
    check("which a turn that goes through clears", not egress.stood_down())
finally:
    srv.shutdown()

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

# ---- and the promise the briefs make is now a thing that exists ------------
# The daemon and every prompt it gives a turn.
_prompts = os.path.join(ROOT, "tutorboard", "runner", "prompts")
tutor_src = "".join(
    open(p, encoding="utf-8").read()
    for p in [os.path.join(ROOT, "tutorboard", "runner", "loop.py")]
    + [os.path.join(_prompts, f) for f in sorted(os.listdir(_prompts))])
board_src = open(os.path.join(ROOT, "bin", "board"), encoding="utf-8").read()
check("no prompt on this board tells a model to call a tool that does not exist",
      "describe_image" not in tutor_src)
check("they name `board see` instead", "board see" in tutor_src)
check("and `board see` is a command", '"see": cmd_see' in board_src)

# ---- the page that never arrived, on the path a sighted tutor actually takes -
#
# `board see` refuses a placeholder answer, but a model that can see is told to
# open the PNG itself and never goes through it. So the TURN's output is scanned
# for the same wording, and the two scanners read one list: a second copy of
# the placeholder is a table that goes stale where nobody is looking.
check("a tutor's own turn is scanned for the placeholder, not just `board see`",
      "seeing.blind_answer(usage.turn_text(said))" in tutor_src)
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
      else "DeepSeek reads the page, and an answer that did not look is refused")
sys.exit(1 if fails else 0)
