#!/usr/bin/env python3
"""`board code`: a coding session held at the cluster, on code/<session>.

A two-clone fixture: a bare origin standing in for GitHub, a `cluster` clone
where the owner writes and the loop runs, and a `mac` clone that pushes a vibe
commit to the same ref. Two subjects, one `"phi": false` and one `"phi":
true`, each with a check that prints a plain line and a `RELAY:` line.

Proved here: an edit is one snapshot on code/S and nothing on main; check
output is in the message only where phi is literally false; a commit pushed to
code/S elsewhere lands in the cluster's working tree; --end is one commit on
main and no ref; --abandon drops the ref; a relay pass with a dirty held file
does not skip, and an upstream change to one is reported, not pulled; a
request pinned to code/S is accepted; `board code --help` imports no server
or runner module. Stdlib only.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def git(root, *args):
    p = subprocess.run(["git", "-C", root] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    return p.stdout.strip()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


CHECK = ("#!/bin/bash\necho 'plain output: 3 tests ran'\n"
         "echo 'RELAY: tests 3'\nexit 0\n")
POLICY = ("import re\n\ndef names_phi(text):\n"
          "    return bool(re.search(r'SESSION-\\d+', str(text)))\n")
SID = "20261008-120000"


class Clock(object):
    """A clock the test moves. Starts an hour ahead of the files' mtimes."""

    def __init__(self):
        import time
        self.t = time.time() + 3600

    def __call__(self):
        return self.t


work = tempfile.mkdtemp(prefix="board-code-")
saved = dict(os.environ)
try:
    os.environ["BOARD_STATE_DIR"] = os.path.join(work, "state")
    os.environ["TUTORBOARD_COURSES"] = os.path.join(work, "cluster")
    os.environ["SLURM_JOB_ID"] = "999"
    os.environ["COLI_QUEUE_ROOT"] = os.path.join(work, "queue")
    os.makedirs(os.environ["COLI_QUEUE_ROOT"])
    from tutorboard import code, jobs, relay  # noqa: E402

    origin = os.path.join(work, "origin.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin],
                   check=True)
    seed = os.path.join(work, "seed")
    os.makedirs(seed)
    git(seed, "init", "-q", "-b", "main")
    write(os.path.join(seed, ".gitignore"),
          "ai-config/\n**/relay/state/\n/relay/state.json\n/relay/.lock*\n")
    for name, phi in (("Open", False), ("Shut", True)):
        subj = os.path.join(seed, "projects", name)
        write(os.path.join(subj, "tutorboard.json"), json.dumps(
            {"name": name, "phi": phi, "check": {"all": ["bash", "check.sh"]}}))
        write(os.path.join(subj, "check.sh"), CHECK)
        write(os.path.join(subj, "src", "a.py"), "x = 1\n")
        write(os.path.join(subj, "notes.md"), "notes\n")
    git(seed, "add", "-A")
    git(seed, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm",
        "seed")
    git(seed, "remote", "add", "origin", origin)
    git(seed, "push", "-q", "-u", "origin", "main")

    def clone(name):
        where = os.path.join(work, name)
        git(work, "clone", "-q", origin, where)
        git(where, "config", "user.email", "%s@example.com" % name)
        git(where, "config", "user.name", name)
        return where

    cluster, mac = clone("cluster"), clone("mac")
    write(os.path.join(cluster, "ai-config", "policy", "phi.py"), POLICY)
    said = []
    say = said.append

    def tip(sid=SID):
        out = git(origin, "for-each-ref", "--format=%(objectname)",
                  "refs/heads/code/%s" % sid)
        return out

    # --- what may be held ---------------------------------------------------
    _, _, probs = code.resolve(cluster, [])
    check("no paths is refused", probs and "no paths" in probs[0])
    os.makedirs(os.path.join(cluster, "projects", "Open", "phi"))
    _, _, probs = code.resolve(cluster, ["projects/Open/phi"])
    check("a fenced path is refused", probs and "fenced" in probs[0])
    _, _, probs = code.resolve(cluster, ["projects/Open/data/x.csv"])
    check("a fenced path is refused even where it is not there",
          probs and "fenced" in probs[0])
    os.rmdir(os.path.join(cluster, "projects", "Open", "phi"))
    _, _, probs = code.resolve(cluster, ["projects/Open/src",
                                         "projects/Shut/src"])
    check("paths in two subjects are refused",
          any("2 subjects" in p for p in probs))
    _, _, probs = code.resolve(cluster, ["projects/Open"])
    check("the whole subject is refused", probs and "whole subject" in probs[0])
    _, _, probs = code.resolve(cluster, ["projects/Open/relay"])
    check("the relay's channel is refused",
          probs and ("channel" in probs[0] or "not there" in probs[0]))

    rec, probs = code.start(cluster, SID, ["projects/Open/src"], cwd=cluster)
    check("a session registers", not probs and rec is not None)
    reg = os.path.join(os.environ["BOARD_STATE_DIR"], "code", SID + ".json")
    got = json.loads(read(reg))
    check("the registration has session, subject, paths, base, last and step",
          all(k in got for k in ("session", "subject", "paths", "base", "last",
                                 "step"))
          and got["subject"] == "projects/Open"
          and got["paths"] == ["projects/Open/src"] and got["step"] == 0
          and got["base"] == git(cluster, "rev-parse", "HEAD"))
    check("and the relay sees its paths held",
          relay.coding(cluster) == ["projects/Open/src"])
    _, probs = code.start(cluster, "other", ["projects/Open/src/a.py"],
                          cwd=cluster)
    check("a path another session holds is refused",
          any("already held" in p for p in probs))

    # --- an edit is one snapshot on code/S, and nothing on main --------------
    clock = Clock()
    loop = code.Loop(cluster, rec, say=say, clock=clock)
    main_before = git(origin, "rev-parse", "main")
    loop.tick()
    check("no edit, no snapshot", tip() == "")
    write(os.path.join(cluster, "projects", "Open", "src", "a.py"), "x = 2\n")
    pushed = []
    for _ in range(int(code.QUIET / code.POLL) + 1):
        clock.t += code.POLL
        pushed.append(loop.tick())
    check("an edit makes one snapshot within one tick after the quiet",
          pushed.count(True) == 1 and pushed[-1] is True)
    first = tip()
    check("it is on code/S at origin", first != ""
          and git(cluster, "rev-list", "--count", "%s..%s" % (main_before, first))
          == "1")
    check("and main did not move, here or at origin",
          git(origin, "rev-parse", "main") == main_before
          and git(cluster, "rev-parse", "HEAD") == main_before)
    check("the real index did not move",
          git(cluster, "diff", "--cached", "--name-only") == "")
    msg = git(origin, "log", "-1", "--format=%B", first)
    check("the message says Step 1 and check: pass",
          "Step 1" in msg and "check: pass" in msg)
    check("and carries ran_at, the cluster's HEAD",
          "ran_at: %s" % git(cluster, "rev-parse", "--short", "HEAD") in msg)
    check("an open subject's check output is in the message",
          "plain output: 3 tests ran" in msg and "RELAY: tests 3" in msg)
    check("the snapshot carries only the held change",
          git(origin, "diff-tree", "-r", "--name-only", "--no-commit-id",
              first) == "projects/Open/src/a.py")
    for _ in range(3):
        clock.t += code.QUIET
        loop.tick()
    check("no further edit, no further step", tip() == first)

    # --- a relay pass with a dirty held file does not skip --------------------
    class Slurm(object):
        def __call__(self, argv, **kw):
            return subprocess.CompletedProcess(argv, 0, "", "")

    got = relay.run_pass(cluster, run=Slurm())
    check("a relay pass with a dirty held file does not skip",
          not got.get("skipped") and "held" not in (got.get("error") or ""))
    check("and leaves the held file as it was",
          read(os.path.join(cluster, "projects", "Open", "src", "a.py"))
          == "x = 2\n")

    # --- a commit pushed to code/S from the other clone lands here -------------
    git(mac, "fetch", "-q", "origin", "code/%s" % SID)
    git(mac, "checkout", "-q", "-b", "vibe", "FETCH_HEAD")
    write(os.path.join(mac, "projects", "Open", "src", "b.py"), "y = 1\n")
    write(os.path.join(mac, "projects", "Open", "src", "a.py"), "x = 3\n")
    git(mac, "add", "-A")
    git(mac, "commit", "-qm", "vibe: b.py")
    git(mac, "push", "-q", "origin", "HEAD:refs/heads/code/%s" % SID)
    vibe = git(mac, "rev-parse", "HEAD")
    clock.t += code.POLL
    loop.tick(fetch=True)
    check("a commit pushed to code/S from the other clone lands in the "
          "working tree",
          read(os.path.join(cluster, "projects", "Open", "src", "a.py"))
          == "x = 3\n"
          and read(os.path.join(cluster, "projects", "Open", "src", "b.py"))
          == "y = 1\n")
    check("and is the session's last commit",
          code.read(SID)["last"] == vibe)
    for _ in range(int(code.QUIET / code.POLL) + 2):
        clock.t += code.POLL
        loop.tick()
    check("applying it makes no step of its own", tip() == vibe)

    # Both sides change: the loop says so and waits.
    write(os.path.join(cluster, "projects", "Open", "src", "a.py"), "x = 4\n")
    write(os.path.join(mac, "projects", "Open", "src", "a.py"), "x = 5\n")
    git(mac, "commit", "-qam", "vibe: a.py again")
    git(mac, "push", "-q", "origin", "HEAD:refs/heads/code/%s" % SID)
    del said[:]
    loop.tick(fetch=True)
    check("both sides changed: it says so and waits",
          any("both sides changed" in s and "projects/Open/src/a.py" in s
              for s in said)
          and read(os.path.join(cluster, "projects", "Open", "src", "a.py"))
          == "x = 4\n")
    # The owner takes the Mac's version by hand; the loop then moves on.
    write(os.path.join(cluster, "projects", "Open", "src", "a.py"), "x = 5\n")
    loop.tick(fetch=True)
    check("matching it settles it", code.read(SID)["last"] == tip()
          and loop.waiting is None)

    # --- a request pinned to code/S is accepted ---------------------------------
    cws = os.path.join(cluster, "projects", "Open")
    req = {"id": "r1", "kind": "recipe", "session": SID, "commit": tip()}
    check("a request pinned to code/S, with the held paths as the commit has "
          "them, passes the pin", jobs.pin_problems(cws, req) == [])
    check("from another session it is refused",
          jobs.pin_problems(cws, dict(req, session="20261008-130000")) != [])
    write(os.path.join(cluster, "projects", "Open", "src", "a.py"), "x = 6\n")
    check("and with the held paths changed since, it is refused",
          jobs.pin_problems(cws, req) != [])
    write(os.path.join(cluster, "projects", "Open", "src", "a.py"), "x = 5\n")

    # --- an upstream change to a held path is reported, not pulled -------------
    git(mac, "checkout", "-q", "main")
    git(mac, "pull", "-q", "--ff-only", "origin", "main")
    write(os.path.join(mac, "projects", "Open", "src", "a.py"), "x = 99\n")
    write(os.path.join(mac, "projects", "Open", "notes.md"), "more notes\n")
    git(mac, "commit", "-qam", "main moves a held file")
    git(mac, "push", "-q", "origin", "main")
    got = relay.run_pass(cluster, run=Slurm())
    check("an upstream change to a held path is reported",
          relay.HELD_UPSTREAM in (got.get("error") or "")
          and not got.get("skipped"))
    check("and not pulled over the owner's file",
          read(os.path.join(cluster, "projects", "Open", "src", "a.py"))
          == "x = 5\n")
    rc = code.end(cluster, SID, say=say, wait=1)
    check("--end refuses a held file main changed too, naming it",
          rc == 1 and any("projects/Open/src/a.py" in s for s in said[-3:])
          and code.read(SID) is not None)
    # The owner merges by hand: main's commit is reverted on origin.
    git(mac, "revert", "--no-edit", "HEAD")
    git(mac, "push", "-q", "origin", "main")

    # --- --end: one new commit on main, and no code/S ----------------------------
    before = git(origin, "rev-parse", "main")
    del said[:]
    rc = code.end(cluster, SID, title="the a.py rewrite", say=say, wait=1)
    after = git(origin, "rev-parse", "main")
    check("--end succeeds", rc == 0)
    check("--end leaves exactly one new main commit",
          git(origin, "rev-list", "--count", "%s..%s" % (before, after)) == "1")
    check("titled <subject>: <title>",
          git(origin, "log", "-1", "--format=%s", after)
          == "projects/Open: the a.py rewrite")
    check("holding exactly the held paths",
          sorted(git(origin, "diff-tree", "-r", "--name-only", "--no-commit-id",
                     after).splitlines())
          == ["projects/Open/src/a.py", "projects/Open/src/b.py"])
    check("and no code/S ref", tip() == "")
    check("and no registration", code.read(SID) is None
          and relay.coding(cluster) == [])

    # --- the closed subject: RELAY lines only ----------------------------------
    S2 = "20261008-140000"
    rec2, probs = code.start(cluster, S2, ["projects/Shut/src"], cwd=cluster)
    check("a session in the phi: true subject registers", not probs)
    loop2 = code.Loop(cluster, rec2, say=say, clock=clock)
    loop2.tick()
    write(os.path.join(cluster, "projects", "Shut", "src", "a.py"), "z = 1\n")
    for _ in range(int(code.QUIET / code.POLL) + 1):
        clock.t += code.POLL
        loop2.tick()
    msg = git(origin, "log", "-1", "--format=%B", tip(S2))
    check("a phi: true subject's step is pushed", "Step 1" in msg)
    check("its check output is absent from the message",
          "plain output" not in msg and "RELAY: tests 3" in msg)

    # --- --abandon ---------------------------------------------------------------
    rc = code.abandon(cluster, S2, say=say)
    check("--abandon drops the ref and the registration",
          rc == 0 and tip(S2) == "" and code.read(S2) is None
          and read(os.path.join(cluster, "projects", "Shut", "src", "a.py"))
          == "z = 1\n")

    # --- the gate refuses a step --------------------------------------------------
    S3 = "20261008-150000"
    rec3, probs = code.start(cluster, S3, ["projects/Open/src"], cwd=cluster)
    loop3 = code.Loop(cluster, rec3, say=say, clock=clock)
    loop3.tick()
    write(os.path.join(cluster, "projects", "Open", "src", "model.pkl"), "x")
    del said[:]
    for _ in range(int(code.QUIET / code.POLL) + 1):
        clock.t += code.POLL
        loop3.tick()
    check("a step the commit-time gate refuses is not pushed",
          tip(S3) == "" and any("gate refuses" in s for s in said))
    code.abandon(cluster, S3, say=say)

    # --- `board code --help` imports no server or runner module ---------------
    p = subprocess.run([sys.executable, "-X", "importtime",
                        os.path.join(ROOT, "bin", "board"), "code", "--help"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
    mods = set(line.split("|")[-1].strip() for line in p.stderr.splitlines()
               if "|" in line)
    ours = sorted(m for m in mods if m.startswith("tutorboard"))
    check("board code --help prints its usage",
          p.returncode == 0 and "--end" in p.stdout and "--abandon" in p.stdout)
    check("and imports no server or runner module (%s)" % ", ".join(ours),
          "tutorboard.code" in ours and not any(
              m.startswith(("tutorboard.server", "tutorboard.runner",
                            "tutorboard.holds", "tutorboard.agents"))
              for m in ours))
finally:
    os.environ.clear()
    os.environ.update(saved)
    shutil.rmtree(work, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a coding session at the cluster: snapshots on code/<session>, vibe "
      "commits applied, --end as one main commit")
