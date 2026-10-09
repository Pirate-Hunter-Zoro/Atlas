#!/usr/bin/env python3
"""The in-process runner: every turn is a fresh provider process the server
starts, one FIFO per session, at most two at once, owed messages survive the
server, and the wrap-up runs only on End.

    python3 test/runner.py

A fake provider (written below) stands in for claude: it reads its prompt and
TUTORBOARD_SESSION, records what it was given, and does what a control file
says -- write a card with `board write`, sleep first, run `board check`, or
write TUTOR.md. A real server (`serve.py --port 0`) runs on a temp Atlas
with its own config directory. Nothing here touches a real session or port.
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
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
ROOT = os.path.dirname(BOARD)
sys.path.insert(0, BOARD)

box = tempfile.mkdtemp(prefix="tutor-runner-")
CONFIG_HOME = os.path.join(box, "config")
os.environ["XDG_CONFIG_HOME"] = CONFIG_HOME
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ["BOARD_NO_TAILNET"] = "1"
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, "trash")
os.environ.pop("TUTORBOARD_SESSION", None)
os.environ.pop("TUTORBOARD_TURN", None)
os.environ.pop("TUTORBOARD_PORT", None)

from tutorboard import mode as session_mode, sessions  # noqa: E402
from tutorboard.course import repo as course_repo  # noqa: E402
from tutorboard.lesson import inbox  # noqa: E402
from tutorboard.runner import daemon, loop, service, turn  # noqa: E402
from tutorboard.server import registry  # noqa: E402

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


def git(*args, cwd):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t"]
                          + list(args), cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)


# ---------------------------------------------------------------------------
# the fake provider
# ---------------------------------------------------------------------------
CTL = os.path.join(box, "ctl")
CALLS = os.path.join(box, "calls.jsonl")
FAKE = os.path.join(box, "bin", "fake-provider")
write(FAKE, r'''#!/usr/bin/env python3
import json, os, subprocess, sys, time
prompt = sys.argv[-1]
session = os.environ.get("TUTORBOARD_SESSION", "")
sid = os.path.basename(session)
ctl = os.path.join(%(ctl)r, sid)
try:
    with open(ctl) as fh:
        mode = fh.read().strip()
except OSError:
    mode = "card"
rec = {"sid": sid, "t": time.time(), "pid": os.getpid(), "pgid": os.getpgid(0),
       "cwd": os.getcwd(), "mode": mode, "prompt": prompt,
       "turn": os.environ.get("TUTORBOARD_TURN"),
       "nogit": os.environ.get("CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS"),
       "port": os.environ.get("TUTORBOARD_PORT")}
def log(**kw):
    rec.update(kw)
    with open(%(calls)r, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
if "This session is ending now" in prompt:
    p = subprocess.run(["board", "memo", "Now"], input="They reached the end. Next: more.\n",
                       universal_newlines=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    log(kind="wrapup", rc=p.returncode, out=p.stdout)
    sys.exit(0)
for word in mode.split(","):
    if word.startswith("sleep:"):
        time.sleep(float(word.split(":")[1]))
    elif word == "check":
        p = subprocess.run(["board", "check"], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
        b = subprocess.run(["board", "brief"], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
        rec.update(check_rc=p.returncode, check_out=p.stdout[-2000:],
                   brief=b.stdout)
first = prompt.split("They just sent this:", 1)[-1].strip().splitlines()
first = first[0] if first else "?"
p = subprocess.run(["board", "write", "lesson", "reply"],
                   input="Answer to %%s\n" %% first[:120], universal_newlines=True,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
log(kind="turn", rc=p.returncode, out=p.stdout)
''' % {"ctl": CTL, "calls": CALLS})
os.chmod(FAKE, 0o755)

write(os.path.join(CONFIG_HOME, "tutor-board", "config.json"), json.dumps({
    "provider": "fake", "vision_agent": "fake", "concurrency": 2,
    "headless_timeout": 120, "doing_timeout": 180, "handoff_timeout": 60,
    "agents": {"fake": {"cmd": [FAKE], "label": "Fake",
                        "headless_first": [FAKE, "{prompt}"],
                        "usage": "none"}},
}))


def ctl(sid, mode):
    write(os.path.join(CTL, sid), mode)


def calls(sid=None, kind=None):
    out = []
    try:
        with open(CALLS) as fh:
            for line in fh:
                r = json.loads(line)
                if (sid is None or r["sid"] == sid) and (kind is None or r.get("kind") == kind):
                    out.append(r)
    except OSError:
        pass
    return out


# ---------------------------------------------------------------------------
# a temp Atlas: a course, and a project whose check is Go's
# ---------------------------------------------------------------------------
atlas = os.path.join(box, "atlas")
write(os.path.join(atlas, "courses", "Demo", "tutorboard.json"),
      json.dumps({"name": "Demo", "phi": False}))
algo = os.path.join(atlas, "projects", "Algo-Solutions")
# Algo-Solutions' own tutorboard.json, wherever the tree keeps it (practice/
# until it moves to projects/).
_algo_cfg = [p for p in (os.path.join(ROOT, d, "Algo-Solutions", "tutorboard.json")
                         for d in ("projects", "practice")) if os.path.isfile(p)]
with open(_algo_cfg[0]) as fh:
    write(os.path.join(algo, "tutorboard.json"), fh.read())
write(os.path.join(algo, "go.mod"), "module algo\n\ngo 1.21\n")
write(os.path.join(algo, "sum", "sum.go"),
      "package sum\n\nfunc Add(a, b int) int { return a + b }\n")
write(os.path.join(algo, "sum", "sum_test.go"),
      'package sum\n\nimport "testing"\n\nfunc TestAdd(t *testing.T) {\n'
      '\tif Add(2, 3) != 5 {\n\t\tt.Fatal("2+3")\n\t}\n}\n')
write(os.path.join(atlas, ".gitignore"), "/sessions/\n")
git("init", "-q", "-b", "main", cwd=atlas)
git("add", "-A", cwd=atlas)
git("commit", "-qm", "fixture", cwd=atlas)


def new_session(subject, title):
    rec = sessions.new(title, base=atlas)
    if subject:
        sessions.bind(rec["id"], subject, base=atlas)
    return rec["id"]


def cards(sid):
    where = os.path.join(atlas, "sessions", sid, "cards")
    try:
        return sorted(n for n in os.listdir(where) if n[:4].isdigit())
    except OSError:
        return []


def agent(sid):
    return daemon.agent_record_at(os.path.join(atlas, "sessions", sid)) or {}


def agent_log(sid):
    try:
        with open(os.path.join(atlas, "sessions", sid, "agent.log")) as fh:
            return fh.read()
    except OSError:
        return ""


def until(cond, timeout=60.0, step=0.1):
    end = time.time() + timeout
    while time.time() < end:
        got = cond()
        if got:
            return got
        time.sleep(step)
    return cond()


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


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
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    def get(self, path):
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (self.port, path),
                                    timeout=30) as r:
            return json.loads(r.read().decode())

    def stop(self, sig=signal.SIGTERM):
        try:
            self.p.send_signal(sig)
        except OSError:
            pass
        try:
            return self.p.wait(30)
        except subprocess.TimeoutExpired:
            self.p.kill()
            return self.p.wait(10)


server = None
try:
    # -----------------------------------------------------------------------
    # the inbox: taken whole, marked in place, nothing appended is lost
    # -----------------------------------------------------------------------
    sid0 = new_session("courses/Demo", "inbox")
    repo0 = sessions.repo(sid0, atlas)
    with open(repo0.messages_path, "a") as fh:
        fh.write(json.dumps({"t": 1, "iso": "a", "text": "one", "read": False}) + "\n")
        fh.write(json.dumps({"t": 2, "iso": "b", "text": "[mode] quiet",
                             "read": False, "wake": False}) + "\n")
    check("a line written wake:false is unread but waits for nothing",
          len(inbox.unread(repo0)) == 2 + 1 and len(inbox.waiting(repo0)) == 1,
          inbox.unread(repo0))   # +1: the [bind] line, itself wake:false
    said = []

    def before(text):
        said.append(text)
        with open(repo0.messages_path, "a") as fh:   # a writer, mid-take
            fh.write(json.dumps({"t": 3, "iso": "c", "text": "late", "read": False}) + "\n")
    text, taken = inbox.take(repo0, before)
    check("a take hands the turn every unread line, the quiet ones too",
          "one" in text and "[mode] quiet" in text and "[bind]" in text
          and len(taken) == 3 and said == [text], text)
    left = inbox.unread(repo0)
    check("and marks them read in place, keeping a line appended meanwhile",
          [m["text"] for m in left] == ["late"], left)
    check("every line still parses", len(inbox.unread(repo0)) + 3
          == sum(1 for _ in open(repo0.messages_path)))

    # -----------------------------------------------------------------------
    # mode and bind lines are written wake:false
    # -----------------------------------------------------------------------
    session_mode.set_mode(repo0, "do")
    lines = [json.loads(l) for l in open(repo0.messages_path)]
    check("a mode change writes its line wake:false and unread",
          lines[-1].get("signal") == "mode" and lines[-1]["wake"] is False
          and lines[-1]["read"] is False)
    inbox.take(repo0)               # nothing left for the server to find

    # -----------------------------------------------------------------------
    # the queue, in process: FIFO per session, two at once, wakes coalesce
    # -----------------------------------------------------------------------
    r = service.Runner(atlas, concurrency=2)
    check("two wakes before the turn starts are one turn",
          r.queue("A", service.TURN) is True and r.queue("A", service.TURN) is False)
    r.queue("A", service.WRAPUP)
    r.queue("B", service.TURN)
    check("a session's jobs keep their order, and sessions theirs",
          list(r.queues["A"]) == [service.TURN, service.WRAPUP]
          and list(r.ready) == ["A", "B"])
    check("concurrency defaults to config.json's, here 2",
          service.configured_concurrency() == 2)
    check("a quiet line in front of the one that woke the turn does not name "
          "the turn", turn.turn_signal("[a] [bind] courses/Demo\n[b] [begin] go") == "begin"
          and turn.turn_signal("[a] [mode] now do\n[b] go on") == "")
    check("a turn never resumes: the recipe is headless_first",
          turn.turn_plan({"headless_first": ["c", "-p", "{prompt}"],
                          "headless": ["c", "-p", "{prompt}", "--continue"]})[0]
          == ["c", "-p", "{prompt}"])

    # -----------------------------------------------------------------------
    # nothing else starts a turn: no daemon, no waiter
    # -----------------------------------------------------------------------
    p = subprocess.run([sys.executable, os.path.join(BOARD, "bin", "tutor"),
                        "headless", "Demo"], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
    check("`tutor headless` is gone: it prints the usage, which no longer names it",
          p.returncode == 2 and "tutor headless" not in p.stdout, p.stdout[:300])
    p = subprocess.run([sys.executable, os.path.join(BOARD, "bin", "board"), "wait"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=60, cwd=atlas)
    check("and so is `board wait`", p.returncode != 0 and "unknown command" in p.stdout,
          p.stdout[:300])
    check("and no daemon is started: `tutor agent start` is refused",
          daemon.agent_start({}, {"dir": "Demo"}, "fake")[0] == 1)

    # -----------------------------------------------------------------------
    # the server: /say to spawn, and the turn's environment
    # -----------------------------------------------------------------------
    server = Server()
    check("serve.py comes up on an ephemeral port with its runner",
          server.port and server.get("/health").get("turns") == {"running": [], "queued": {}},
          "".join(server.lines))
    sa = new_session("courses/Demo", "A")
    server.post("/s/%s/say" % sa, {"text": "what is a field?"})
    until(lambda: calls(sa, "turn"), 30)
    got = cards(sa)
    check("/say is answered with one card", len(got) == 1, (got, agent_log(sa)))
    one = (calls(sa, "turn") or [{}])[0]
    check("the turn ran in the Atlas root, on its session, flagged as a turn",
          os.path.realpath(one.get("cwd", "")) == os.path.realpath(atlas)
          and one.get("turn") == "1" and one.get("nogit") == "1"
          and one.get("port") == str(server.port), one)
    check("its prompt carries the message, and names no live/ path",
          "what is a field?" in one.get("prompt", "")
          and "live/" not in one.get("prompt", "") and "--continue" not in one.get("prompt", ""))
    check("and board write landed the card in that session", one.get("rc") == 0, one)
    import re
    m = re.search(r"spawned ([0-9.]+) s after the message landed", agent_log(sa))
    check("/say to provider spawn is under 300 ms, and logged",
          m and float(m.group(1)) < 0.3, agent_log(sa))
    print("     (spawned %s s after /say)" % (m.group(1) if m else "?"))
    rec = agent(sa)
    check("the record says listening, owes nothing, and names the server",
          until(lambda: agent(sa).get("state") == "listening", 10)
          and not agent(sa).get("owed") and agent(sa).get("pid") == server.p.pid, rec)

    # A quiet line queues nothing; the next turn reads it.
    before_n = len(calls(sa))
    server.post("/s/%s/mode" % sa, {"mode": "do"})
    time.sleep(1.5)
    check("a mode change wakes no turn", len(calls(sa)) == before_n)
    server.post("/s/%s/say" % sa, {"text": "go on"})
    until(lambda: len(calls(sa, "turn")) == 2, 30)
    last = calls(sa, "turn")[-1]
    check("and the next turn's prompt carries the quiet line", "[mode]" in last["prompt"]
          and "go on" in last["prompt"],
          agent_log(sa)[-1500:])

    # -----------------------------------------------------------------------
    # two sessions at once are both answered; a third queues
    # -----------------------------------------------------------------------
    until(lambda: not server.get("/health")["turns"]["running"], 20)
    trio = [new_session("courses/Demo", t) for t in ("B", "C", "D")]
    for s in trio:
        ctl(s, "sleep:3")
    for s in trio:
        server.post("/s/%s/say" % s, {"text": "hello %s" % s})
    state = until(lambda: (lambda st: st if len(st["running"]) == 2 else None)(
        server.get("/health")["turns"]), 10)
    check("two sessions sending at once run at once", state and len(state["running"]) == 2,
          state)
    check("and the third queues behind them",
          state and len(state["queued"]) == 1
          and set(state["running"]) | set(state["queued"]) == set(trio), state)
    until(lambda: all(len(calls(s, "turn")) == 1 for s in trio), 40)
    check("all three are answered, one card each",
          [len(cards(s)) for s in trio] == [1, 1, 1], [cards(s) for s in trio])

    # -----------------------------------------------------------------------
    # a do turn in Algo-Solutions runs `board check`
    # -----------------------------------------------------------------------
    sd = new_session("projects/Algo-Solutions", "algo")
    session_mode.set_mode(sessions.repo(sd, atlas), "do")
    ctl(sd, "check")
    server.post("/s/%s/say" % sd, {"text": "make it pass"})
    until(lambda: calls(sd, "turn"), 120)
    run = (calls(sd, "turn") or [{}])[0]
    check("a do turn's `board check` runs the subject's go test and passes",
          run.get("check_rc") == 0 and "ok" in run.get("check_out", ""), run.get("check_out"))
    check("and the brief tells it to run `board check`",
          "check: `board check`" in run.get("brief", "") and "go test ./..." in run.get("brief", ""))
    allow = os.path.join(ROOT, "ai-config", "workspaces", "tutors.allow")
    if os.path.isfile(allow):
        pats = [l.split(None, 1)[1].strip() for l in open(allow)
                if l.startswith("run ")]
        check("`board check` is inside the unattended allowlist (`board *`)",
              "board *" in pats)
    else:
        print("skip the allowlist: ai-config is not here")

    # -----------------------------------------------------------------------
    # TERM mid-turn, then restart: answered once, no wrap-up
    # -----------------------------------------------------------------------
    st_ = new_session("courses/Demo", "term")
    ctl(st_, "sleep:60")
    server.post("/s/%s/say" % st_, {"text": "a long one"})
    rec = until(lambda: agent(st_) if agent(st_).get("turn_pid") else None, 20)
    pgid = (rec or {}).get("turn_pid")
    check("a turn's process group is on the record while it runs",
          pgid and agent(st_).get("state") == "working" and agent(st_).get("owed"), rec)
    code = server.stop(signal.SIGTERM)
    check("TERM stops the server cleanly", code == 0, code)
    check("and the turn in flight goes with it", until(lambda: not alive(pgid), 10))
    check("its message is still owed on disk", "a long one" in (agent(st_).get("owed") or ""))
    ctl(st_, "card")
    server = Server()
    until(lambda: calls(st_, "turn"), 30)
    time.sleep(1.5)
    check("after a restart the owed message is answered once",
          len(cards(st_)) == 1 and len(calls(st_, "turn")) == 1, cards(st_))
    check("with nothing left owed", not agent(st_).get("owed"))
    check("and no wrap-up turn ran", "wrap-up ===" not in agent_log(st_)
          and not calls(st_, "wrapup"))

    # A server KILLED mid-turn leaves the group running: the next start kills
    # it and answers the message once.
    sk = new_session("courses/Demo", "kill")
    ctl(sk, "sleep:60")
    server.post("/s/%s/say" % sk, {"text": "another long one"})
    rec = until(lambda: agent(sk) if agent(sk).get("turn_pid") else None, 20)
    pgid = (rec or {}).get("turn_pid")
    server.stop(signal.SIGKILL)
    check("a KILLed server leaves its turn behind", pgid and alive(pgid))
    ctl(sk, "card")
    server = Server()
    check("the next start kills that surviving group", until(lambda: not alive(pgid), 15))
    until(lambda: calls(sk, "turn"), 30)
    time.sleep(1.5)
    check("and answers its owed message once, with no wrap-up",
          len(cards(sk)) == 1 and "wrap-up ===" not in agent_log(sk), cards(sk))

    # A turn cut AFTER its card is not answered twice.
    sc = new_session("courses/Demo", "cut")
    repo_c = sessions.repo(sc, atlas)
    write(os.path.join(repo_c.cards, "0001-done.md"), "---\nkind: lesson\n---\nDone.\n")
    daemon.agent_state(repo_c.live, state="working", owed="[x] answered already",
                       turn_started=time.time() - 60, turn_pid=None)
    server.stop(signal.SIGKILL)
    server = Server()
    time.sleep(2)
    check("a turn cut after it wrote its card is not run again",
          len(cards(sc)) == 1 and not calls(sc) and not agent(sc).get("owed"),
          (cards(sc), agent(sc)))

    # -----------------------------------------------------------------------
    # End: the wrap-up, and only there
    # -----------------------------------------------------------------------
    got = server.post("/s/%s/end" % sa)
    check("End sets ended and queues the wrap-up",
          got.get("ok") and got["session"].get("ended") and got.get("wrapup"), got)
    until(lambda: "TUTOR.md written" in agent_log(sa), 30)
    check("the wrap-up turn brings TUTOR.md up to date with `board memo`",
          "TUTOR.md written" in agent_log(sa)
          and "They reached the end." in open(os.path.join(
              atlas, "courses", "Demo", "TUTOR.md"), encoding="utf-8").read(),
          agent_log(sa)[-600:])
    su = new_session(None, "unbound")
    write(os.path.join(sessions.path(su, atlas), "cards", "0001-x.md"), "x\n")
    got = server.post("/s/%s/end" % su)
    time.sleep(1.5)
    check("an unbound session ends with no wrap-up, so nothing writes a TUTOR.md "
          "at the Atlas root", got.get("ok") and not calls(su)
          and not os.path.exists(os.path.join(atlas, "TUTOR.md")))

    # -----------------------------------------------------------------------
    # runner_route: a subject with no open session gets one, and its turn
    # -----------------------------------------------------------------------
    server.stop()
    server = None
    write(os.path.join(atlas, "projects", "Lonely", "tutorboard.json"),
          json.dumps({"name": "Lonely", "phi": False}))
    r = service.install(service.Runner(atlas, concurrency=2)).start()
    got = registry.runner_route("projects/Lonely", "[writeup] a deck please",
                                base=atlas, ask="a deck")
    check("runner_route opens a session bound to the subject, titled by the ask",
          sessions.get(got["session"], atlas)["title"] == "Lonely: a deck"
          and sessions.get(got["session"], atlas)["subject"] == "projects/Lonely")
    until(lambda: calls(got["session"], "turn"), 30)
    check("and the runner answers it", len(cards(got["session"])) == 1)
    again = registry.runner_route("projects/Lonely", "and another", base=atlas)
    check("the next ask goes to the newest open session on it",
          again["session"] == got["session"])
    until(lambda: len(calls(got["session"], "turn")) == 2, 30)
    check("and the runner answers that too", len(cards(got["session"])) == 2)
    r.shutdown()
    service.install(None)

finally:
    if server is not None:
        server.stop()
    # Any fake provider still running belongs to this test.
    for c in calls():
        try:
            os.killpg(c.get("pgid"), signal.SIGKILL)
        except (OSError, TypeError):
            pass
    shutil.rmtree(box, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails else
      "every turn is a fresh process the server queues, and nothing owed is lost")
sys.exit(1 if fails else 0)
