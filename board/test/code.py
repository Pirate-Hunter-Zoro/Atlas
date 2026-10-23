#!/usr/bin/env python3
"""`board code`: a coding session, on code/<session>.

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
or runner module.

A local branch made from origin's code/S (`git checkout code/S`) does not
make the session local: --abandon still drops origin's ref, `board push` still
asks origin, and the ear does not hear it as a local ref.

Mac-local mode, in the `mac` clone made a board checkout (`sessions/<id>/`):
a step lands on the local code ref and never on origin; a linked worktree and
a branch other than main are refused; the ear lists the local ref with origin
unreachable, records it without moving a file and never releases it; the
loop waits while a turn is answering, and not for an owed message no turn is
answering; in do mode what the turn changed is one step marked `by: tutor`,
taken as it ends, which the ear records with a non-waking `[stepped]` line,
while the owner's next edit wakes as before; in teach mode an edit made under
a turn is the owner's step, after the quiet, and wakes; `board push` there sends nothing;
--end commits on main past its own hold, pushes to the bare origin, deletes
the local ref and clears `code`; --abandon drops the ref and leaves the files.
The real pre-commit hook refuses a held file on main, for a registration and
for session.json `code`, and lets `BOARD_CODE_END` lift its own session's
hold and no other. Stdlib only.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HOOKS = os.path.join(os.path.dirname(ROOT), ".githooks")
sys.path.insert(0, ROOT)

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       %s" % (detail,)) if detail else ""))


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


def commit_by_hand(root, rel, end=None):
    """`git commit` of one staged file through the hooks, as the owner would.
    `(committed, output)`; a refusal leaves nothing staged, a commit is undone
    with its change kept in the working tree."""
    env = dict(os.environ)
    env.pop("BOARD_CODE_END", None)
    if end:
        env["BOARD_CODE_END"] = end
    git(root, "add", "--", rel)
    p = subprocess.run(["git", "-C", root, "commit", "-qm", "by hand"],
                       env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    if p.returncode == 0:
        git(root, "reset", "-q", "HEAD~1")
    else:
        git(root, "reset", "-q")
    return p.returncode == 0, p.stdout


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
    # The real hook, so --end's commit goes through it.
    git(cluster, "config", "core.hooksPath", HOOKS)
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

    # --- a branch made from origin's code/S is not a local session -------------
    from tutorboard import sync as ear_mod  # noqa: E402
    S6 = "20261008-145000"
    rec6, probs = code.start(cluster, S6, ["projects/Shut/src"], cwd=cluster)
    loop6 = code.Loop(cluster, rec6, say=say, clock=clock)
    loop6.tick()
    write(os.path.join(cluster, "projects", "Shut", "src", "a.py"), "z = 3\n")
    for _ in range(int(code.QUIET / code.POLL) + 1):
        clock.t += code.POLL
        loop6.tick()
    pushed6 = tip(S6)
    # What `git checkout code/S` leaves behind: a local branch tracking origin.
    git(cluster, "branch", "-q", "--track", "code/%s" % S6,
        "origin/code/%s" % S6)
    check("a local branch of origin's code/S does not make the session local",
          pushed6 != "" and code.keeps_local(cluster, S6) is False)
    sha, what = code.vibe(cluster, S6, ["projects/Shut/src"], pushed6, "a vibe")
    check("so `board push` still asks origin",
          sha == "" and "codes in this checkout" not in what
          and "as code/%s has them" % S6 in what, what)
    git(mac, "fetch", "-q", "origin",
        "refs/heads/code/%s:refs/heads/code/%s" % (S6, S6))
    ear6 = ear_mod.Sync(mac, state_dir=os.path.join(work, "ear6"),
                       say=lambda m: None)
    check("and the ear does not hear such a branch as a local ref",
          ear6.local_refs() == {}, ear6.local_refs())
    git(mac, "branch", "-q", "-D", "code/%s" % S6)
    rc = code.abandon(cluster, S6, say=say)
    check("--abandon drops origin's ref, not only the local branch",
          rc == 0 and tip(S6) == "" and code.read(S6) is None)
    git(cluster, "branch", "-q", "-D", "code/%s" % S6)
    git(cluster, "checkout", "-q", "--", "projects/Shut/src/a.py")

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

    # --- the pre-commit hook: a registration's held files ----------------------
    S4 = "20261008-155000"
    rec4, probs = code.start(cluster, S4, ["projects/Shut/src"], cwd=cluster)
    write(os.path.join(cluster, "projects", "Shut", "src", "a.py"), "z = 2\n")
    ok_, out = commit_by_hand(cluster, "projects/Shut/src/a.py")
    check("the pre-commit hook refuses a file a registration holds, on main",
          not ok_ and "held by coding session %s" % S4 in out
          and "board code %s --end" % S4 in out, out)
    ok_, out = commit_by_hand(cluster, "projects/Shut/src/a.py", end="other")
    check("BOARD_CODE_END for another session lifts nothing",
          not ok_ and "held by coding session %s" % S4 in out, out)
    ok_, out = commit_by_hand(cluster, "projects/Shut/src/a.py", end=S4)
    check("BOARD_CODE_END=<its session> lets it through", ok_, out)
    ok_, out = commit_by_hand(cluster, "projects/Shut/notes.md")
    check("and a file nobody holds commits on main",
          ok_ or "nothing to commit" in out or "no changes" in out, out)
    write(os.path.join(cluster, "projects", "Shut", "notes.md"), "shut notes\n")
    ok_, out = commit_by_hand(cluster, "projects/Shut/notes.md")
    check("(a changed one too)", ok_, out)
    git(cluster, "checkout", "-q", "--", "projects/Shut/notes.md")
    git(cluster, "checkout", "-q", "-b", "side")
    ok_, out = commit_by_hand(cluster, "projects/Shut/src/a.py")
    check("off main the hold is not the hook's business", ok_, out)
    git(cluster, "checkout", "-q", "main")
    git(cluster, "branch", "-q", "-D", "side")
    code.abandon(cluster, S4, say=say)
    git(cluster, "checkout", "-q", "--", "projects/Shut/src/a.py")

    # --- Mac-local mode: the board's own checkout --------------------------------
    from tutorboard import gitops, sessions, sync as ear_mod  # noqa: E402
    git(mac, "checkout", "-q", "main")
    git(mac, "pull", "-q", "--ff-only", "origin", "main")
    git(mac, "config", "core.hooksPath", HOOKS)
    with open(os.path.join(mac, ".git", "info", "exclude"), "a") as fh:
        fh.write("sessions/\n")
    write(os.path.join(mac, "ai-config", "policy", "phi.py"), POLICY)
    SL = sessions.new("coding here", base=mac, now=clock.t - 7200)["id"]
    sessions.bind(SL, "projects/Open", base=mac)
    agent = os.path.join(mac, "sessions", SL, "agent.json")

    def local_tip(sid=SL):
        return git(mac, "for-each-ref", "--format=%(objectname)",
                   "refs/heads/code/%s" % sid)

    def inbox(sid=SL):
        try:
            text = read(os.path.join(mac, "sessions", sid, "inbox",
                                     "messages.jsonl"))
        except OSError:
            return []
        return [json.loads(l) for l in text.splitlines() if l.strip()]

    check("a session of this board's checkout is Mac-local",
          code.mode(mac, SL) == (True, "")
          and code.mode(cluster, SL) == (False, ""))

    linked = os.path.join(work, "linked")
    git(mac, "worktree", "add", "-q", "-b", "wt", linked)
    _, probs = code.start(linked, SL, ["projects/Open/src"], cwd=linked)
    check("a linked worktree of it is refused",
          probs and "linked worktree" in probs[0], probs)
    git(mac, "worktree", "remove", "--force", linked)
    git(mac, "branch", "-q", "-D", "wt")
    git(mac, "checkout", "-q", "-b", "other")
    _, probs = code.start(mac, SL, ["projects/Open/src"], cwd=mac)
    check("a branch other than main is refused",
          probs and "not main" in probs[0] and code.read(SL) is None, probs)
    git(mac, "checkout", "-q", "main")
    git(mac, "branch", "-q", "-D", "other")

    recl, probs = code.start(mac, SL, ["projects/Open/src"], cwd=mac)
    check("on main it registers, local", not probs and recl.get("local") is True)
    mac_main = git(mac, "rev-parse", "HEAD")
    loopl = code.Loop(mac, recl, say=say, clock=clock)
    loopl.tick()
    write(os.path.join(mac, "projects", "Open", "src", "c.py"), "c = 1\n")
    del said[:]
    for _ in range(int(code.QUIET / code.POLL) + 1):
        clock.t += code.POLL
        loopl.tick()
    step1 = local_tip()
    check("a Mac-local step lands on the local code ref",
          step1 != "" and "Step 1" in git(mac, "log", "-1", "--format=%B", step1)
          and any("step 1 on code/%s" % SL in s for s in said), said)
    check("and never on origin", tip(SL) == ""
          and git(mac, "ls-remote", "origin", "refs/heads/code/*") == "")
    check("and main, HEAD and the index did not move",
          git(mac, "rev-parse", "HEAD") == mac_main
          and git(origin, "rev-parse", "main") == mac_main
          and git(mac, "diff", "--cached", "--name-only") == "")

    # The ear, with origin unreachable: the local ref is heard anyway.
    url = git(mac, "remote", "get-url", "origin")
    git(mac, "remote", "set-url", "origin", os.path.join(work, "nowhere.git"))
    ear = ear_mod.Sync(mac, state_dir=os.path.join(work, "ear"),
                      say=lambda m: None)
    # The owner took the step back out: the ear must not bring it again.
    os.remove(os.path.join(mac, "projects", "Open", "src", "c.py"))
    got = ear.once()
    rec_code = sessions.get(SL, mac).get("code") or {}
    check("the ear lists the local ref with origin unreachable",
          got["pulled"] is None and ear.local == {
              "refs/heads/code/%s" % SL: step1})
    check("and records it in session.json, local, at the step",
          rec_code.get("sha") == step1 and rec_code.get("local") is True
          and rec_code.get("step") == 1
          and rec_code.get("paths") == ["projects/Open/src"])
    check("and wakes the session with [code] step 1",
          any(m.get("signal") == "code" and m["text"].startswith("[code] step 1")
              for m in inbox()))
    check("and moves no file: the working tree is the owner's",
          not os.path.exists(os.path.join(mac, "projects", "Open", "src",
                                          "c.py")))
    write(os.path.join(mac, "projects", "Open", "src", "c.py"), "c = 11\n")
    git(mac, "remote", "set-url", "origin", url)
    del said[:]
    got = ear.once()
    check("with origin back, which has no code/<id>, it is not released",
          (sessions.get(SL, mac).get("code") or {}).get("sha") == step1
          and not any(m.get("signal") == "unheld" for m in inbox())
          and read(os.path.join(mac, "projects", "Open", "src", "c.py"))
          == "c = 11\n")

    # The tutor owes an answer: no step until its turn ends.
    write(agent, json.dumps({"state": "working", "owed": "[code] step 1",
                             "last_seen": time.time()}))
    del said[:]
    for _ in range(int(code.QUIET / code.POLL) + 3):
        clock.t += code.POLL
        loopl.tick()
    check("while agent.json has owed set, the loop takes no step",
          local_tip() == step1
          and sum("the tutor is answering" in s for s in said) == 1, said)
    write(agent, json.dumps({"state": "idle", "owed": None}))
    for _ in range(int(code.QUIET / code.POLL) + 1):
        clock.t += code.POLL
        loopl.tick()
    step2 = local_tip()
    check("once it is answered, the waiting edit is the next step",
          step2 != step1 and "Step 2" in git(mac, "log", "-1", "--format=%B",
                                             step2))
    sha, what = code.vibe(mac, SL, ["projects/Open/src"], step1, "a vibe")
    check("`board push` in a Mac-local session sends nothing",
          sha == "" and what.startswith("nothing to push") and tip(SL) == "",
          what)
    ear.once()
    check("the ear follows the local ref", (sessions.get(SL, mac).get("code")
                                            or {}).get("sha") == step2)

    def woken(n):
        return [m for m in inbox() if m.get("signal") == "code"
                and m["text"].startswith("[code] step %d" % n)]

    # An owed message no turn is answering (nobody could take it) stops no
    # step: only a step would wake the turn that answers it.
    write(agent, json.dumps({"state": "working", "owed": "[code] step 2",
                             "last_seen": time.time() - code.TURN_STALE - 5}))
    check("a working state whose heartbeat stopped is no turn",
          not code.answering(mac, SL))
    write(agent, json.dumps({"state": "listening", "owed": "[code] step 2",
                             "last_seen": time.time()}))
    check("nor is owed with no turn running", not code.answering(mac, SL))
    write(os.path.join(mac, "projects", "Open", "src", "c.py"), "c = 13\n")
    del said[:]
    for _ in range(int(code.QUIET / code.POLL) + 1):
        clock.t += code.POLL
        loopl.tick()
    step3 = local_tip()
    check("so a failed turn's owed message never stops the steps",
          step3 != step2 and "Step 3" in git(mac, "log", "-1", "--format=%B",
                                             step3)
          and not any("the tutor is answering" in s for s in said), said)
    ear.once()
    check("and the owner's step wakes the session", len(woken(3)) == 1)

    def set_mode(m):
        where = os.path.join(mac, "sessions", SL, "session.json")
        got = json.loads(read(where))
        got["mode"] = m
        write(where, json.dumps(got))

    # In teach mode the tutor writes no held file: the owner's edit made
    # while a turn runs (a [code] turn, or a deck rework routed here) is the
    # owner's step, taken after the quiet, and it wakes the session.
    write(agent, json.dumps({"state": "working", "owed": "[code] step 3",
                             "last_seen": time.time()}))
    clock.t += code.POLL
    loopl.tick()
    write(os.path.join(mac, "projects", "Open", "src", "c.py"), "c = 14\n")
    for _ in range(int(code.QUIET / code.POLL) + 1):
        clock.t += code.POLL
        loopl.tick()
    check("in teach mode, the owner's edit under a turn is no step while it "
          "runs", local_tip() == step3)
    write(agent, json.dumps({"state": "listening", "owed": None,
                             "last_seen": time.time()}))
    clock.t += code.POLL
    loopl.tick()
    check("nor at once as the turn ends: it waits out the quiet",
          local_tip() == step3)
    for _ in range(int(code.QUIET / code.POLL) + 1):
        clock.t += code.POLL
        loopl.tick()
    step4 = local_tip()
    msg4 = git(mac, "log", "-1", "--format=%B", step4)
    n_lines = len(inbox())
    ear.once()
    check("then it is the owner's step, not marked by: tutor, and it wakes",
          step4 != step3 and "Step 4" in msg4
          and code.BY_TUTOR not in msg4.splitlines()
          and code.step_of(mac, step4)["tutor"] is False
          and len(woken(4)) == 1
          and not any(m.get("signal") == "stepped"
                      for m in inbox()[n_lines:]), msg4)

    # The tutor's own edit in do mode: a step of its own, waking nothing.
    set_mode("do")
    write(agent, json.dumps({"state": "working", "owed": "[code] step 4",
                             "last_seen": time.time()}))
    clock.t += code.POLL
    loopl.tick()
    write(os.path.join(mac, "projects", "Open", "src", "c.py"), "c = 16\n")
    for _ in range(int(code.QUIET / code.POLL) + 1):
        clock.t += code.POLL
        loopl.tick()
    check("the turn's edit is no step while it runs", local_tip() == step4)
    write(agent, json.dumps({"state": "listening", "owed": None,
                             "last_seen": time.time()}))
    clock.t += code.POLL
    loopl.tick()
    step5 = local_tip()
    msg5 = git(mac, "log", "-1", "--format=%B", step5)
    check("as the turn ends, its edit is one step at once, marked by: tutor",
          step5 != step4 and "Step 5" in msg5
          and code.BY_TUTOR in msg5.splitlines()
          and code.step_of(mac, step5)["tutor"] is True, msg5)
    n_lines = len(inbox())
    ear.once()
    stepped = [m for m in inbox()[n_lines:] if m.get("signal") == "stepped"]
    check("the ear records it and wakes no turn: one quiet [stepped] line",
          (sessions.get(SL, mac).get("code") or {}).get("sha") == step5
          and not woken(5) and len(stepped) == 1
          and stepped[0].get("wake") is False
          and stepped[0]["text"].startswith("[stepped] step 5"),
          inbox()[n_lines:])
    from tutorboard.runner import turn as turn_mod  # noqa: E402
    check("and the next turn's signal reads past it",
          turn_mod.turn_signal("[t] %s\n[t] [code] step 6: x"
                               % stepped[0]["text"]) == "code")
    write(os.path.join(mac, "projects", "Open", "src", "c.py"), "c = 17\n")
    for _ in range(int(code.QUIET / code.POLL) + 1):
        clock.t += code.POLL
        loopl.tick()
    step6 = local_tip()
    ear.once()
    check("the owner's next edit is theirs, and wakes the session",
          step6 != step5 and code.step_of(mac, step6)["tutor"] is False
          and len(woken(6)) == 1)
    set_mode("teach")

    # The board's own save, and the hook, refuse the held file on main.
    ok_, what = gitops.commit(mac, ["projects/Open/src"], "by the board")
    check("gitops.commit on main refuses the held paths",
          not ok_ and "held by coding session %s" % SL in what, what)
    ok_, out = commit_by_hand(mac, "projects/Open/src/c.py")
    check("and so does the pre-commit hook, for session.json `code`",
          not ok_ and "held by coding session %s" % SL in out, out)

    git(mac, "checkout", "-q", "-b", "other")
    rc = code.end(mac, SL, say=say, wait=1)
    check("--end on a branch other than main is refused",
          rc == 1 and any("not main" in s for s in said[-2:])
          and local_tip() == step6, said[-2:])
    git(mac, "checkout", "-q", "main")
    git(mac, "branch", "-q", "-D", "other")

    before = git(origin, "rev-parse", "main")
    del said[:]
    rc = code.end(mac, SL, title="c.py here", say=say, wait=1)
    after = git(origin, "rev-parse", "main")
    check("Mac-local --end succeeds, through its own hold and the hook",
          rc == 0, "\n".join(said))
    check("one new main commit, pushed to origin, with the held files",
          git(origin, "rev-list", "--count", "%s..%s" % (before, after)) == "1"
          and git(origin, "log", "-1", "--format=%s", after)
          == "projects/Open: c.py here"
          and git(origin, "diff-tree", "-r", "--name-only", "--no-commit-id",
                  after) == "projects/Open/src/c.py"
          and git(mac, "rev-parse", "HEAD") == after)
    check("the local ref is deleted, and origin never had one",
          local_tip() == "" and tip(SL) == "")
    check("the registration and session.json `code` are gone",
          code.read(SL) is None and sessions.get(SL, mac).get("code") is None)
    check("and an [unheld] line says so, waking nothing",
          any(m.get("signal") == "unheld" and m.get("wake") is False
              for m in inbox()))
    ear.once()
    check("the ear then has nothing to hear or release",
          sessions.get(SL, mac).get("code") is None
          and git(mac, "status", "--porcelain", "--", "projects") == "")

    # A local record whose ref is gone is dropped, and no file moves.
    sessions.set_code(SL, {"ref": "refs/heads/code/%s" % SL, "sha": step2,
                           "paths": ["projects/Open/src"], "local": True},
                      base=mac)
    write(os.path.join(mac, "projects", "Open", "src", "c.py"), "c = 12\n")
    n_lines = len(inbox())
    ear.once()
    check("the ear drops a local record whose ref is gone, moving nothing",
          sessions.get(SL, mac).get("code") is None
          and read(os.path.join(mac, "projects", "Open", "src", "c.py"))
          == "c = 12\n" and len(inbox()) == n_lines)
    git(mac, "checkout", "-q", "--", "projects/Open/src/c.py")

    # --abandon, Mac-local.
    SL2 = sessions.new("abandoned here", base=mac, now=clock.t - 3600)["id"]
    rec5, probs = code.start(mac, SL2, ["projects/Open/notes.md"], cwd=mac)
    loop5 = code.Loop(mac, rec5, say=say, clock=clock)
    loop5.tick()
    write(os.path.join(mac, "projects", "Open", "notes.md"), "mine\n")
    for _ in range(int(code.QUIET / code.POLL) + 1):
        clock.t += code.POLL
        loop5.tick()
    had = local_tip(SL2)
    ear.once()
    rc = code.abandon(mac, SL2, say=say)
    check("Mac-local --abandon drops the local ref, the registration and "
          "`code`, and leaves the file",
          had != "" and rc == 0 and local_tip(SL2) == ""
          and code.read(SL2) is None
          and sessions.get(SL2, mac).get("code") is None
          and read(os.path.join(mac, "projects", "Open", "notes.md"))
          == "mine\n")
    git(mac, "checkout", "-q", "--", "projects/Open/notes.md")

    # --- --end's lock: board-code.lock in the git common dir, the relay's too ---
    import fcntl  # noqa: E402
    lock = code.lock_path(cluster)
    check("--end's lock is board-code.lock in `git rev-parse --git-common-dir`",
          lock is not None and os.path.realpath(lock) == os.path.join(
              os.path.realpath(cluster), ".git", "board-code.lock"), lock)
    held_fh = open(lock, "a+")
    fcntl.flock(held_fh.fileno(), fcntl.LOCK_EX)
    got = relay.run_pass(cluster, run=Slurm())
    check("a relay pass takes the same lock: while --end holds it, it skips",
          "board code --end" in str(got.get("skipped") or ""), got)
    S9 = "20261008-175000"
    rec9, _ = code.start(cluster, S9, ["projects/Open/notes.md"], cwd=cluster)
    del said[:]
    rc = code.end(cluster, S9, say=say, wait=1)
    check("and --end waits on it, ending nothing",
          rc == 1 and code.read(S9) is not None
          and any("board-code.lock" in s for s in said), said)
    held_fh.close()
    code.abandon(cluster, S9, say=say)

    # --- code.py imports neither relay nor exports ---------------------------
    import ast  # noqa: E402
    tree = ast.parse(read(os.path.join(ROOT, "tutorboard", "code.py")))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(a.name for a in node.names)
            names.add(node.module or "")
        elif isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
    check("code.py imports neither relay nor exports",
          not names & {"relay", "exports", "tutorboard.relay",
                       "tutorboard.exports"}, sorted(names))

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
                            "tutorboard.agents"))
              for m in ours))
finally:
    os.environ.clear()
    os.environ.update(saved)
    shutil.rmtree(work, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a coding session: snapshots on code/<session>, vibe commits applied, "
      "Mac-local steps kept local, --end as one main commit")
