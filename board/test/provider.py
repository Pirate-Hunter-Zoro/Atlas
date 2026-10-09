#!/usr/bin/env python3
"""One provider setting: the provider, one fallback, and a tap that sets it.

    python3 test/provider.py

A real server (`serve.py --port 0`) on a temp Atlas, with its own config
directory and state directory, and fake providers named claude, codex and
deepseek (one script, told its name on the command line). Each answers a turn
with `board write`, or, when its control file says so, fails the way a provider
out of allowance does. Nothing here spends a cent or touches a real session.

  - A LIMITED CLAUDE FALLS BACK TO CODEX AND THE CARD NAMES IT: the turn that
    hit the limit is answered again at once by codex, the card says `by codex`,
    and the session's record says why.
  - `/default-agent` CHANGES THE PROVIDER FOR THE NEXT TURN WITHOUT A RESTART:
    it writes `provider` into the machine's config and nothing else, and the
    same server process answers the next message with the new one.
  - It refuses an unknown name, a recipe this machine cannot run, and an
    in-fence model: only it reads phi, and it never takes a turn here.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
sys.path.insert(0, BOARD)

box = tempfile.mkdtemp(prefix="tutor-provider-")
CONFIG_HOME = os.path.join(box, "config")
os.environ["XDG_CONFIG_HOME"] = CONFIG_HOME
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ["BOARD_NO_TAILNET"] = "1"
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, "trash")
for k in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "TUTORBOARD_PORT",
          "TUTORBOARD_FALLBACK"):
    os.environ.pop(k, None)

from tutorboard import assistants, sessions                   # noqa: E402
from tutorboard.agents import recipes                         # noqa: E402
from tutorboard.lesson import cards as lesson_cards           # noqa: E402
from tutorboard.runner import daemon                          # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# ---------------------------------------------------------------------------
# the fake providers: one script, its name on the command line
# ---------------------------------------------------------------------------
CTL = os.path.join(box, "ctl")
FAKE = os.path.join(box, "bin", "fake-provider")
write(FAKE, r'''#!/usr/bin/env python3
import os, subprocess, sys
name, prompt = sys.argv[1], sys.argv[-1]
if os.path.exists(os.path.join(%(ctl)r, "limited-" + name)):
    print("API Error: Claude AI usage limit reached")
    sys.exit(1)
first = prompt.split("They just sent this:", 1)[-1].strip().splitlines()
p = subprocess.run(["board", "write", "lesson", "reply"],
                   input="Answer from %%s to %%s\n" %% (name, (first or ["?"])[0][:80]),
                   universal_newlines=True, stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT)
sys.exit(p.returncode)
''' % {"ctl": CTL})
os.chmod(FAKE, 0o755)
os.makedirs(CTL)


def fake(name, **kw):
    spec = {"replace": True, "cmd": [FAKE], "label": name.title(),
            "headless_first": [FAKE, name, "{prompt}"], "usage": "none"}
    spec.update(kw)
    return spec


CONFIG = os.path.join(CONFIG_HOME, "tutor-board", "config.json")
write(CONFIG, json.dumps({
    "provider": "claude", "fallback": "codex", "vision_agent": "claude",
    "concurrency": 2, "headless_timeout": 60, "handoff_timeout": 30,
    "quota_tokens": 28000000,
    "agents": {"claude": fake("claude"), "codex": fake("codex"),
               "deepseek": fake("deepseek"),
               "gone": fake("gone", cmd=["a-command-no-machine-has"]),
               "nokey": fake("nokey", needs_key="A_KEY_NOBODY_HAS"),
               "colibri": fake("colibri", private="it reads phi")}}))


def on_disk():
    with open(CONFIG, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# a temp Atlas with one course
# ---------------------------------------------------------------------------
atlas = os.path.join(box, "atlas")
write(os.path.join(atlas, "courses", "Demo", "tutorboard.json"),
      json.dumps({"name": "Demo", "phi": False, "agent": "deepseek"}))
write(os.path.join(atlas, ".gitignore"), "/sessions/\n")
for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-qm", "fixture"]):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t"] + args,
                   cwd=atlas, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

SID = sessions.new("provider", base=atlas)["id"]
sessions.bind(SID, "courses/Demo", base=atlas)
LIVE = sessions.path(SID, atlas)


def newest():
    """`(text, parsed card)` of the session's newest card."""
    path, _meta = lesson_cards.newest(os.path.join(LIVE, "cards"))
    if not path:
        return "", {}
    text = open(path, encoding="utf-8").read()
    meta, body = lesson_cards.parse_front_matter(text)
    return text, dict(meta, body=body)


def n_cards():
    try:
        return len([n for n in os.listdir(os.path.join(LIVE, "cards")) if n[:4].isdigit()])
    except OSError:
        return 0


def record():
    return daemon.agent_record_at(LIVE) or {}


def until(cond, timeout=60.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.1)
    return bool(cond())


class Server(object):
    def __init__(self):
        self.p = subprocess.Popen(
            [sys.executable, os.path.join(BOARD, "serve.py"), "--port", "0",
             "--atlas", atlas], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            universal_newlines=True, start_new_session=True)
        self.port = None
        self.lines = []
        for line in self.p.stderr:
            self.lines.append(line)
            if "listening on http://" in line:
                self.port = int(line.split("http://", 1)[1].split("/")[0].split(":")[1])
                break
        threading.Thread(target=self._drain, daemon=True).start()

    def _drain(self):
        for line in self.p.stderr:
            self.lines.append(line)

    def post(self, path, body=None):
        req = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (self.port, path),
            data=json.dumps(body or {}).encode(), method="POST",
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode())

    def stop(self):
        try:
            self.p.send_signal(signal.SIGTERM)
            self.p.wait(30)
        except (OSError, subprocess.TimeoutExpired):
            self.p.kill()


server = None
try:
    server = Server()
    pid = server.p.pid
    check("serve.py comes up on an ephemeral port", bool(server.port),
          "".join(server.lines))

    # ---- the provider takes the turn -------------------------------------
    server.post("/s/%s/say" % SID, {"text": "first"})
    until(lambda: n_cards() == 1 and record().get("state") == "listening", 30)
    text, card = newest()
    check("the provider answers, and a subject naming another is not asked",
          "Answer from claude" in text and record().get("agent") == "claude",
          (text, record()))
    check("and a card the provider wrote carries no by-line", not card.get("by"))

    # ---- a limited claude falls back to codex, and the card names it ------
    write(os.path.join(CTL, "limited-claude"), "")
    server.post("/s/%s/say" % SID, {"text": "second"})
    until(lambda: n_cards() == 2 and record().get("state") == "listening", 30)
    text, card = newest()
    rec = record()
    check("a limited claude falls back to codex, which answers the same message",
          "Answer from codex" in text and "second" in text, (text, rec))
    check("and the card names it", card.get("by") == "codex", text)
    check("and the record says who and why, for the strip",
          rec.get("agent") == "codex"
          and "'claude'" in (rec.get("agent_why") or "")
          and "allowance" in (rec.get("agent_why") or ""), rec)
    parsed = lesson_cards.load_cards(sessions.repo(SID, atlas), {})
    check("the card the board draws carries `by`",
          parsed and parsed[-1].get("by") == "codex", parsed[-1:] if parsed else None)
    log = open(os.path.join(LIVE, "agent.log"), encoding="utf-8").read()
    check("and the log says the next turn goes to the fallback",
          "the next turn goes to 'codex'" in log, log[-800:])

    # ---- /default-agent: the next turn, no restart ------------------------
    status, got = server.post("/default-agent", {"agent": "deepseek"})
    check("the tap sets the provider", status == 200 and got.get("ok")
          and got.get("default") == "deepseek", got)
    cfg = on_disk()
    check("and the file says `provider`, with nothing else in it moved",
          cfg.get("provider") == "deepseek" and cfg.get("fallback") == "codex"
          and cfg.get("quota_tokens") == 28000000 and "default_agent" not in cfg
          and set(cfg["agents"]) == {"claude", "codex", "deepseek", "gone",
                                     "nokey", "colibri"}, cfg)
    check("and the answer carries who takes the next turn",
          got.get("machine") == "deepseek" and (got.get("assistants") or {})
          .get("default") == "deepseek", got)
    server.post("/s/%s/say" % SID, {"text": "third"})
    until(lambda: n_cards() == 3 and record().get("state") == "listening", 30)
    text, card = newest()
    check("the next turn is the new provider's, from the same server process",
          "Answer from deepseek" in text and server.p.pid == pid
          and server.p.poll() is None, text)
    check("and it is not a fallback, so the card has no by-line",
          not card.get("by") and not record().get("agent_why"), record())

    # ---- the refusals -------------------------------------------------------
    for name, why, word in (("nonesuch", "an unknown name", "not an assistant"),
                            ("gone", "a recipe whose binary is missing",
                             "not installed"),
                            ("nokey", "a recipe whose key is missing",
                             "A_KEY_NOBODY_HAS"),
                            ("colibri", "an in-fence model", "in-fence")):
        status, got = server.post("/default-agent", {"agent": name})
        check("%s is refused, in words" % why,
              status == 400 and not got.get("ok") and word in (got.get("detail") or ""),
              got)
    status, got = server.post("/default-agent", {})
    check("a request naming nobody is refused rather than a crash", status == 400)
    check("and no refusal changed the file", on_disk().get("provider") == "deepseek")

    # ---- `default_agent` chooses nothing; a tap drops a leftover one ------
    legacy = dict(on_disk())
    legacy.pop("provider")
    legacy["default_agent"] = "codex"
    write(CONFIG, json.dumps(legacy))
    check("a config naming only `default_agent` gets the built-in provider",
          recipes.load_config()["provider"] == "claude")
    status, got = server.post("/default-agent", {"agent": "deepseek"})
    check("and the next tap writes `provider` and drops the leftover key",
          status == 200 and on_disk().get("provider") == "deepseek"
          and "default_agent" not in on_disk(), on_disk())

    js = open(os.path.join(BOARD, "web", "board.js"), encoding="utf-8").read()
    check("the board draws a card's by-line", "card-by" in js and "c.by" in js)
    who = open(os.path.join(BOARD, "web", "who.js"), encoding="utf-8").read()
    # The board's per-sitting chooser is gone (D27: no per-session provider
    # override); the home screen draws the machine's default with the rules.
    home = open(os.path.join(BOARD, "web", "home.js"), encoding="utf-8").read()
    check("home.js draws the chooser through the shared rules", "WhoChoice" in home)
    check("an unkeyed recipe is drawn dimmed with the key and the file in its "
          "title", "a.unkeyed" in who and "keys" in who)
finally:
    if server:
        server.stop()
    shutil.rmtree(box, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "one provider, one fallback that names itself, and a tap that lands on the next turn")
sys.exit(1 if fails else 0)
