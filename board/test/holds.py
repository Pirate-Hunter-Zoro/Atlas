#!/usr/bin/env python3
"""A sitting held at the cluster: the owner writes there, the coach answers here.

What the checks are about:

  * A HOLD IS CHECKED WHOLE. Refused on a thread already held, one with no
    files, one whose check is missing or untracked, and a file another hold
    has -- every problem at once.
  * WHILE IT LASTS, THE MAC DOES NOT WRITE THE FILES. `board push` refuses a
    commit touching one, and says which.
  * THE CLUSTER'S PULL LEAVES THE OWNER'S EDITS ALONE. Rebase with autostash
    under uncommitted edits to a held file while the Mac pushes elsewhere; and
    nothing moves at all when the Mac has touched that file.
  * A REPORT CARRIES ONLY `RELAY:` LINES. Whatever else the check prints stays
    in the terminal.
  * ONE ROUND TRIP. `board send` on the cluster, a `[coach]` wake on the Mac,
    `board coach` back, and `board send` prints the reply.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
from tutorboard import holds, jobs                                     # noqa: E402
from tutorboard.course import threads                                  # noqa: E402

BOARD = os.path.join(ROOT, "bin", "board")
fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def git(cwd, *args):
    p = subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL, check=False)
    return p.stdout.decode("utf-8", "replace")


SPINE = {
    "version": 1,
    "deliverables": [{"id": "paper2", "title": "Paper 2", "doc": ""}],
    "threads": [
        {"id": "aipw", "deliverable": "paper2", "title": "The AIPW rung",
         "files": ["src/aipw"], "check": "checks/aipw.sh"},
        {"id": "other", "deliverable": "paper2", "title": "Other",
         "files": ["src/aipw/shared.py", "src/other.py"]},
        {"id": "bare", "deliverable": "paper2", "title": "Bare"},
    ],
}

# --- the thread's check, and the validator ----------------------------------
clean, problems = threads.validate(SPINE)
check("a thread names its check, and one that names none has \"\"",
      not problems and threads.thread(clean, "aipw")["check"] == "checks/aipw.sh"
      and threads.thread(clean, "bare")["check"] == "")
bad = json.loads(json.dumps(SPINE))
bad["threads"][0]["check"] = "../outside.sh"
check("a check outside the workspace is refused",
      any("check" in p for p in threads.validate(bad)[1]))

tracked = {"checks/aipw.sh", "src/aipw/est.py"}
rec, problems = holds.validate_hold(clean, "aipw", {}, tracked)
check("a thread with files and a tracked check may be held",
      not problems and rec == {"thread": "aipw", "files": ["src/aipw"],
                               "check": "checks/aipw.sh"})
_, problems = holds.validate_hold(clean, "aipw", {"aipw": {"held": 0}}, set())
check("held already AND an untracked check: both said at once",
      len(problems) == 2 and "already held" in problems[0]
      and "not tracked" in problems[1])
_, problems = holds.validate_hold(clean, "bare", {}, tracked)
check("no files and no check: both said",
      len(problems) == 2 and "no files" in problems[0] and "no check" in problems[1])
_, problems = holds.validate_hold(
    clean, "other", {"aipw": {"thread": "aipw", "files": ["src/aipw"]}}, tracked)
check("a file another hold covers is refused, by name",
      any("src/aipw/shared.py is already held, by thread aipw" in p
          for p in problems))
check("an unknown thread is refused",
      holds.validate_hold(clean, "nope", {}, tracked)[0] is None)

req = {"id": "check-aipw-1", "kind": "turn", "thread": "aipw", "brief": "x"}
_, problems = jobs.validate(req, clean, tracked, {}, (), True)
check("a request is refused an id a step's check report would share",
      any("check-" in p for p in problems) and holds.is_check(req["id"]))

standing = {"aipw": {"thread": "aipw", "files": ["src/aipw"], "held": 0}}
said =holds.refused_writes(["src/aipw/est.py", "notes.md", "src/aipwx.py"],
                            clean, standing)
check("a write under a held directory is refused, and only that one",
      len(said) == 1 and said[0].startswith("src/aipw/est.py belongs to "
                                            "thread aipw"))
grown = json.loads(json.dumps(SPINE))
grown["threads"][0]["files"].append("src/new.py")
check("a file added to the thread mid-hold is held too",
      holds.refused_writes(["src/new.py"], threads.validate(grown)[0], standing))

# --- RELAY: lines --------------------------------------------------------------
lines, withheld = holds.relay_lines(
    "loading\nRELAY: n=120 mean=0.42\nrow 17: 0.9\nRELAY:ate=0.03\n"
    "RELAY: phi/session_01\n", names_phi=lambda s: "phi/" in s)
check("only RELAY: lines are kept, prefix dropped, a flagged one withheld",
      lines == ["n=120 mean=0.42", "ate=0.03"] and withheld == 1)
check("at most MAX_LINES of them",
      len(holds.relay_lines("RELAY: x\n" * 100)[0]) == holds.MAX_LINES)
check("a crash is its exception type, never its message",
      holds.crash_type("Traceback...\n  File x\nValueError: row 17 was 0.9\n")
      == "ValueError" and holds.crash_type("all fine\n") == "")
check("a check report is told apart from a request's",
      holds.is_check("check-aipw-3") and not holds.is_check("2026-10-03-x"))
check("the coach file's header round-trips",
      holds.parse_coach(holds.coach_text("aipw", 3, "Next: the outcome model."))
      == ("aipw", 3, "Next: the outcome model."))

# --- two machines and one origin ---------------------------------------------------
base = tempfile.mkdtemp(prefix="holds-")
try:
    origin = os.path.join(base, "origin.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin],
                   check=True)
    seed = os.path.join(base, "seed")
    os.makedirs(seed)
    git(seed, "init", "-q", "-b", "main")
    git(seed, "config", "user.email", "owner@example.com")
    git(seed, "config", "user.name", "Owner")
    ws = os.path.join(seed, "research", "Proj")
    write(os.path.join(ws, "AI_INSTRUCTIONS.md"), "# contract\n")
    write(os.path.join(ws, ".gitignore"), "live/\nresults/\n")
    write(os.path.join(ws, "src", "aipw", "est.py"), "def est():\n    pass\n")
    write(os.path.join(ws, "notes.md"), "draft\n")
    write(os.path.join(ws, "checks", "aipw.sh"),
          "#!/bin/bash\necho 'RELAY: n=120 ate=0.031'\necho 'row 17 is 0.9'\n"
          "echo 'to stderr' >&2\nexit 0\n")
    write(threads.path(ws), json.dumps(SPINE))
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "start")
    git(seed, "remote", "add", "origin", origin)
    git(seed, "push", "-q", "-u", "origin", "main")

    def clone(name):
        top = os.path.join(base, name)
        subprocess.run(["git", "clone", "-q", origin, top], check=True)
        git(top, "config", "user.email", "owner@example.com")
        git(top, "config", "user.name", "Owner")
        return top, os.path.join(top, "research", "Proj")

    cl_top, cl = clone("cluster")
    mac_top, mac = clone("mac")
    on_cluster = dict(os.environ, TUTOR_SLURM="1")
    on_mac = dict(os.environ, TUTOR_SLURM="0")

    def board(where, env, *args, stdin=None):
        p = subprocess.run([sys.executable, BOARD] + list(args), cwd=where,
                           env=env, input=(stdin or "").encode(),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=240)
        return p.returncode, p.stdout.decode("utf-8", "replace")

    # --- hold -----------------------------------------------------------------
    code, out = board(mac, on_mac, "hold", "aipw")
    check("a hold is refused on the Mac", code == 1 and "no Slurm" in out)
    code, out = board(cl, on_cluster, "hold", "aipw")
    check("`board hold` on the cluster holds and pushes",
          code == 0 and "held at the cluster" in out
          and git(origin, "show", "main:research/Proj/relay/holds/aipw.json"))
    files = git(cl_top, "show", "--name-only", "--format=", "HEAD").split()
    check("in one commit carrying the hold and nothing else",
          files == ["research/Proj/relay/holds/aipw.json"])
    code, out = board(cl, on_cluster, "hold", "aipw")
    check("a second hold on the same thread is refused",
          code == 1 and "already held" in out)

    # --- the Mac refuses the held files ---------------------------------------
    git(mac_top, "pull", "-q", "--ff-only")
    write(os.path.join(mac, "src", "aipw", "est.py"), "def est():\n    return 1\n")
    code, out = board(mac, on_mac, "push", "a turn's edit")
    check("on the Mac, `board push` refuses a commit touching a held file",
          code == 1 and "src/aipw/est.py belongs to thread aipw" in out)
    check("and nothing was committed",
          "est.py" in git(mac_top, "status", "--porcelain"))
    os.environ["TUTOR_SLURM"] = "0"
    check("a push narrowed to a path no hold covers passes the check",
          holds.refusal(mac, [os.path.join(mac, "notes.md")]) == ""
          and holds.refusal(mac).startswith("nothing was committed"))
    os.environ.pop("TUTOR_SLURM", None)
    git(mac_top, "checkout", "--", "research/Proj/src/aipw/est.py")

    # --- the cluster's pull, under the owner's edits ---------------------------
    write(os.path.join(cl, "src", "aipw", "est.py"),
          "def est(y, a, x):\n    # the owner, mid-step\n    pass\n")
    write(os.path.join(cl, "src", "aipw", "fresh.py"), "x = 1\n")
    write(os.path.join(mac, "notes.md"), "draft, from the Mac\n")
    git(mac_top, "commit", "-q", "-am", "notes")
    git(mac_top, "push", "-q")
    ok, said = holds.sync(cl_top)
    check("the cluster pulls while the owner has uncommitted held edits",
          ok and read(os.path.join(cl, "notes.md")) == "draft, from the Mac\n")
    check("and the edits are exactly where they were, untracked file too",
          "the owner, mid-step" in read(os.path.join(cl, "src", "aipw", "est.py"))
          and os.path.exists(os.path.join(cl, "src", "aipw", "fresh.py"))
          and git(cl_top, "stash", "list").strip() == "")
    head = git(cl_top, "rev-parse", "HEAD")
    write(os.path.join(mac, "src", "aipw", "est.py"), "def est():\n    return 2\n")
    git(mac_top, "commit", "-q", "-am", "a Mac turn that broke the rule")
    git(mac_top, "push", "-q")
    ok, said = holds.sync(cl_top)
    check("origin touching an edited held file stops the pull, naming it",
          not ok and "research/Proj/src/aipw/est.py" in said)
    check("with nothing moved and the owner's edit intact",
          git(cl_top, "rev-parse", "HEAD") == head
          and "the owner, mid-step" in read(os.path.join(cl, "src", "aipw",
                                                          "est.py")))
    # Undo the Mac's rule-breaking commit, the way its owner would.
    git(mac_top, "revert", "--no-edit", "HEAD")
    git(mac_top, "push", "-q")
    ok, _ = holds.sync(cl_top)
    check("once origin leaves the file alone again, the pull goes through",
          ok and "the owner, mid-step" in read(os.path.join(cl, "src", "aipw",
                                                             "est.py")))

    # --- release refuses while held edits are uncommitted -----------------------
    code, out = board(cl, on_cluster, "release", "aipw")
    check("`board release` refuses while a held file has uncommitted edits",
          code == 1 and "board send" in out)

    # --- the round trip ---------------------------------------------------------
    sender = subprocess.Popen(
        [sys.executable, BOARD, "send", "aipw", "--wait", "90"], cwd=cl,
        env=on_cluster, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    rel = "research/Proj/relay/reports/check-aipw-1.json"
    deadline = time.time() + 60
    while time.time() < deadline and not git(origin, "show", "main:" + rel):
        time.sleep(0.5)
    rep = json.loads(git(origin, "show", "main:" + rel) or "{}")
    check("`board send` pushes the check's report",
          rep.get("kind") == "check" and rep.get("step") == 1
          and rep.get("exit") == 0 and rep.get("state") == "completed")
    check("which carries the RELAY: line and nothing else the check printed",
          rep.get("relay") == ["n=120 ate=0.031"]
          and "row 17" not in json.dumps(rep) and "stderr" not in json.dumps(rep))
    check("and names the files the step changed",
          rep.get("files") == ["src/aipw/est.py", "src/aipw/fresh.py"])
    log = git(origin, "log", "-2", "--format=%an|%s", "main").splitlines()
    check("the step is its own commit, `aipw: step`, authored by the owner",
          log == ["Owner|aipw: check 1", "Owner|aipw: step"])

    git(mac_top, "pull", "-q", "--ff-only")
    woke = holds.wake(mac)
    inbox = [json.loads(x) for x in read(os.path.join(
        mac, "live", "inbox", "messages.jsonl")).splitlines() if x.strip()]
    step_sha = git(origin, "rev-parse", "main~1").strip()[:12]
    check("the pull carrying the report wakes one [coach] turn",
          len(woke) == 1 and inbox[-1]["signal"] == "coach"
          and inbox[-1]["text"].startswith("[coach] Step 1 of thread aipw"))
    check("naming the step's commit, the check's exit and its RELAY: lines",
          "git show %s" % step_sha in inbox[-1]["text"]
          and "exit 0" in inbox[-1]["text"]
          and "RELAY: n=120 ate=0.031" in inbox[-1]["text"]
          and "board coach aipw --step 1" in inbox[-1]["text"])
    check("and a second wake on the same report drops nothing",
          holds.wake(mac) == [])

    code, out = board(mac, on_mac, "coach", "aipw", "--step", "1",
                      stdin="The estimate is in. Next: the outcome model.\n")
    check("`board coach` on the Mac commits the reply alone and pushes it",
          code == 0 and git(origin, "show", "--name-only", "--format=",
                            "main").split()
          == ["research/Proj/relay/coach/aipw.md"])
    try:
        out = sender.communicate(timeout=120)[0].decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        sender.kill()
        out = ""
    check("and `board send` prints it in the cluster terminal",
          sender.returncode == 0 and "Next: the outcome model." in out
          and "RELAY: n=120 ate=0.031" in out)
    git(mac_top, "pull", "-q", "--ff-only")
    check("a step already answered wakes nothing",
          holds.wake(mac) == [])

    code, out = board(cl, on_cluster, "release", "aipw")
    check("with the step sent, `board release` ends the hold and pushes it",
          code == 0 and not git(origin, "show",
                                "main:research/Proj/relay/holds/aipw.json"))
finally:
    shutil.rmtree(base, ignore_errors=True)

# --- the real repository ------------------------------------------------------------
for ws in ("research/TRD-EHR", "research/PSYCH-ASR", "projects/libr-local-llm"):
    root = os.path.join(REPO, ws)
    if os.path.isdir(root):
        check("%s: git would see a hold" % ws, holds.visible(root) == "")

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a held thread is written at the cluster and coached from the Mac, "
      "and neither machine's pull walks over the other")
