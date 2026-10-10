#!/usr/bin/env python3
"""The cutover script, on fixtures: every step it can run without this Mac's
real system, and the rollback that undoes them.

    python3 test/cutover.py

A temp Atlas stands in for the main checkout: main tracks research/X and a
tracked practice/Y/live, an `overhaul` branch moves both into projects/ and
folds in a course whose own repository sits ignored under courses/. On it:

  * the drift check passes a course the fold took as it is, flags a change
    made since, and lets the files the fold itself rewrote through;
  * step 2 waits for a fake tutor daemon to come to rest, SIGKILLs it, its
    `board wait` and an orphaned one, SIGTERMs a fake `serve.py --root` board, and records each;
  * steps 3-8 snapshot, import the live/ dirs, archive the course's .git,
    merge and carry the residue (a .env rewritten), leaving git status empty;
  * the rollback puts every file back: a tree comparison against a copy made
    before the cutover is empty, main is at PRE, the course repo is back;
  * a merge that conflicts aborts cleanly and rolls back the same way;
  * the tailscale plan, the 8778-only check and the rsync listing parse.

The full rehearsal on a copy of this Mac (`cutover.sh --rehearse`) is not
run here: it copies every live/ and course directory and loads launchd jobs.
Nothing here touches a real session, label, port or the real Atlas.
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

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(BOARD, "scripts"))

import cutover  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)[:2500]) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def git(root, *args):
    p = subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "-c", "init.defaultBranch=main", "-C", root] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True)
    if p.returncode != 0:
        raise RuntimeError("git %s: %s" % (" ".join(args), p.stdout))
    return p.stdout.strip()


box = os.path.realpath(tempfile.mkdtemp(prefix="tutor-cutover-"))
ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "HOME": os.path.join(box, "home")}
os.makedirs(ENV["HOME"])


def fixture(name, conflict=False):
    """A temp Atlas on main, its `overhaul` branch, a course repo and live/ dirs."""
    G = os.path.join(box, name, "Atlas")
    os.makedirs(G)
    git(G, "init", "-q", "-b", "main")
    write(os.path.join(G, ".gitignore"), "/courses/*/\nlive/\n!/practice/Y/live/\n"
          ".venv/\n.env\n**/relay/state/\n")
    write(os.path.join(G, "research", "X", "a.txt"), "X's work\n")
    write(os.path.join(G, "practice", "Y", "b.txt"), "Y's work\n")
    write(os.path.join(G, "practice", "Y", "live", "cards", "0001-old.md"),
          "---\nkind: lesson\n---\nA card git tracks.\n")
    write(os.path.join(G, "shared.txt"), "one\n")
    git(G, "add", "-A")
    git(G, "commit", "-qm", "main")
    # The course, its own repository, ignored by main.
    C = os.path.join(G, "courses", "C")
    write(os.path.join(C, "notes.tex"), "\\section{One}\n")
    write(os.path.join(C, "tutorboard.json"), '{"name": "C"}\n')
    write(os.path.join(C, "Makefile"), "all:\n")
    git(C, "init", "-q", "-b", "main")
    git(C, "add", "-A")
    git(C, "commit", "-qm", "course")
    snap = git(C, "rev-parse", "HEAD")
    write(os.path.join(C, "build", "notes.pdf"), "%PDF\n")
    write(os.path.join(C, "transcripts", "t1.tex"), "a transcript\n")
    # overhaul: the moves, the fold, and the tools the merge brings.
    git(G, "checkout", "-q", "-b", "overhaul")
    os.makedirs(os.path.join(G, "projects", "Y"))
    git(G, "mv", "research/X", "projects/X")
    git(G, "mv", "practice/Y/b.txt", "projects/Y/b.txt")
    git(G, "rm", "-q", "-r", "practice/Y/live")
    write(os.path.join(G, ".gitignore"), "/sessions/\n**/.ink/\n/research/\n/practice/\n"
          ".venv/\n.env\n**/relay/state/\n**/materials/\n/courses/*/build/\n"
          "/courses/*/transcripts/\n")
    if conflict:
        write(os.path.join(G, "shared.txt"), "two on overhaul\n")
    scripts = os.path.join(G, "board", "scripts")
    os.makedirs(scripts)
    shutil.copy2(os.path.join(BOARD, "scripts", "move-residue.sh"), scripts)
    git(G, "add", "-A", "--", ".", ":!courses")
    git(G, "commit", "-qm", "moves")
    fold = os.path.join(box, name, "fold")
    os.makedirs(fold)
    shutil.copy2(os.path.join(C, "notes.tex"), fold)
    write(os.path.join(fold, "tutorboard.json"), '{"name": "C", "phi": false}\n')
    # The fold commit: the course's files under courses/C, tutorboard.json rewritten.
    blob1 = git(G, "hash-object", "-w", os.path.join(fold, "notes.tex"))
    blob2 = git(G, "hash-object", "-w", os.path.join(fold, "tutorboard.json"))
    git(G, "update-index", "--add", "--cacheinfo", "100644,%s,courses/C/notes.tex" % blob1)
    git(G, "update-index", "--add", "--cacheinfo",
        "100644,%s,courses/C/tutorboard.json" % blob2)
    git(G, "commit", "-qm", "courses: C is tracked content, snapshot of %s" % snap[:8])
    git(G, "checkout", "-q", "-f", "main")
    # Leaving overhaul took the fold's files out of the course's tree; on the
    # Mac nothing ever checks overhaul out.
    git(C, "checkout", "-q", "--", ".")
    if conflict:
        write(os.path.join(G, "shared.txt"), "two on main\n")
        git(G, "commit", "-qam", "main moves on")
    # The old system's state, ignored on main.
    live = os.path.join(G, "research", "X", "live")
    write(os.path.join(live, "cards", "0001-hello.md"), "---\nkind: lesson\n---\nHello.\n")
    write(os.path.join(live, "turns.jsonl"), '{"id": 1, "t": 1}\n')
    write(os.path.join(live, "inbox", "messages.jsonl"), '{"text": "hi", "t": 1}\n')
    write(os.path.join(live, "agent.json"), json.dumps(
        {"state": "listening", "owed": None, "pid": 1, "agent": "claude"}))
    write(os.path.join(live, "archive", "old", "0001.md"), "archived\n")
    write(os.path.join(G, "practice", "Y", "live", "state.json"), '{"stance": "teach"}\n')
    write(os.path.join(C, "live", "cards", "0001-c.md"), "---\nkind: lesson\n---\nC.\n")
    write(os.path.join(C, "live", "agent.json"), json.dumps(
        {"state": "listening", "owed": "an old report, still owed", "agent": "claude"}))
    write(os.path.join(C, "live", "inbox", "messages.jsonl"),
          '{"text": "a bind", "t": 1, "wake": false}\n')
    write(os.path.join(G, "research", "X", ".venv", "pyvenv.cfg"), "home = /usr/bin\n")
    write(os.path.join(G, "research", "X", ".env"),
          "X_DATA=%s/research/X/data\nOTHER=/elsewhere\n" % G)
    os.makedirs(os.path.join(G, "live", "cards"))
    return G, snap


def ctx_for(G, name, scope=None):
    ctx = cutover.Ctx(mode="rehearse", atlas=G, archive=os.path.join(box, name, "archive"),
                      ref="overhaul", label="tutor-board-cutover-test-%d" % os.getpid(),
                      old_labels=["tutor-board-cutover-test-none-%d" % os.getpid()],
                      port=0, scope=scope or os.path.join(box, name),
                      agents_dir=os.path.join(box, name, "LaunchAgents"),
                      bin_dir=os.path.join(box, name, "bin"), env=ENV,
                      tailscale="print", fake_capture={
                          "TCP": {"9098": {"TCPForward": "127.0.0.1:9098"}}})
    ctx.begin()
    ctx.put("tools", BOARD)
    return ctx


try:
    # =======================================================================
    # the pure parts
    # =======================================================================
    listing = ("*deleting gone.tex\n>fcsT.... changed.tex\n.f..T.... same.tex\n"
               "cd+++++++ newdir/\n>f+++++++ newdir/new.tex\n.d..T.... ./\n")
    check("an rsync listing yields content changes only, not times or directories",
          cutover.itemized(listing) == [("gone", "gone.tex"), ("changed", "changed.tex"),
                                        ("new", "newdir/new.tex")], cutover.itemized(listing))
    status = {"TCP": {"443": {"HTTPS": True}, "9098": {"TCPForward": "127.0.0.1:9098"},
                      "8808": {"TCPForward": "127.0.0.1:8808", "TerminateTLS": "x"}},
              "Web": {"mac.tail.ts.net:443": {"Handlers": {
                  "/": {"Proxy": "http://127.0.0.1:9098"},
                  "/p": {"Proxy": "http://127.0.0.1:8808"}}}}}
    cmds = [" ".join(c) for c in cutover.ts_restore(status)]
    check("a captured serve config is restored mapping by mapping, after a reset",
          cmds == ["tailscale serve reset",
                   "tailscale serve --bg --yes --tls-terminated-tcp=8808 tcp://127.0.0.1:8808",
                   "tailscale serve --bg --yes --tcp=9098 tcp://127.0.0.1:9098",
                   "tailscale serve --bg --yes --https=443 http://127.0.0.1:9098",
                   "tailscale serve --bg --yes --https=443 --set-path /p http://127.0.0.1:8808"],
          cmds)
    check("publishing is every old mapping off, then HTTPS to 8778",
          [" ".join(c) for c in cutover.ts_publish(8778)]
          == ["tailscale serve reset",
              "tailscale serve --bg --yes --https=443 http://127.0.0.1:8778"])
    only = {"TCP": {"443": {"HTTPS": True}}, "Web": {"m.ts.net:443": {"Handlers": {
        "/": {"Proxy": "http://127.0.0.1:8778"}}}}}
    check("a config that serves only 8778 passes; the old one and an empty one do not",
          cutover.ts_only(only, 8778) == [] and len(cutover.ts_only(status, 8778)) == 4
          and cutover.ts_only({}, 8778) == ["nothing is published"])
    fakebin = os.path.join(box, "fakebin")
    cutover.write_exec(os.path.join(fakebin, "tailscale"),
                       "#!/bin/sh\necho 'Warning: client version \"1.104.1\" != tailscaled "
                       "server version \"1.102.4\"' >&2\n"
                       "echo '%s'\n" % json.dumps(only))
    path_was = os.environ["PATH"]
    os.environ["PATH"] = fakebin + os.pathsep + path_was
    try:
        got, why = cutover.ts_status()
        rc, merged = cutover.run(["tailscale", "serve", "status", "--json"])
        cutover.write_exec(os.path.join(fakebin, "tailscale"), "#!/bin/sh\necho not json\n")
        bad, bad_why = cutover.ts_status()
        cutover.write_exec(os.path.join(fakebin, "tailscale"),
                           "#!/bin/sh\necho 'no daemon' >&2\nexit 1\n")
        down, down_why = cutover.ts_status()
    finally:
        os.environ["PATH"] = path_was
    check("`tailscale serve status --json` is parsed from stdout alone: a version "
          "warning on stderr does not break it",
          why is None and got == only and cutover.ts_only(got, 8778) == []
          and "Warning" in merged, (why, got, merged))
    check("and a status that is not JSON, or that fails, is a reason, never a capture",
          bad is None and "no JSON" in bad_why and down is None
          and "rc 1" in down_why and "no daemon" in down_why, (bad_why, down_why))
    check("a workspace's post-merge subject",
          [cutover.post_merge(r) for r in ("courses/C", "research/X", "practice/Y",
                                           "projects/Z")]
          == ["courses/C", "projects/X", "projects/Y", "projects/Z"])
    check("ship.sh kickstarts the label TUTORBOARD_LABEL names, tutor-board by default",
          '"gui/$(id -u)/${TUTORBOARD_LABEL:-tutor-board}"'
          in open(os.path.join(BOARD, "scripts", "ship.sh")).read())

    # =======================================================================
    # a cutover and its rollback, on a fixture
    # =======================================================================
    G, snap = fixture("one")
    excludes = os.path.join(BOARD, "scripts", "fold-excludes.txt")
    drift_box = tempfile.mkdtemp(dir=box)
    got = cutover.course_drift(G, "overhaul", "C", excludes, drift_box)
    check("the course as the fold took it is no drift; the rewritten "
          "tutorboard.json and the excluded Makefile, build/ and transcripts/ pass", got == [], got)
    write(os.path.join(G, "courses", "C", "notes.tex"), "\\section{Changed}\n")
    write(os.path.join(G, "courses", "C", "extra.tex"), "new\n")
    got = cutover.course_drift(G, "overhaul", "C", excludes, tempfile.mkdtemp(dir=box))
    check("a file changed since the fold, and one added, are drift",
          any("notes.tex changed" in g for g in got) and any("extra.tex new" in g for g in got),
          got)
    git(os.path.join(G, "courses", "C"), "checkout", "-q", "--", "notes.tex")
    os.remove(os.path.join(G, "courses", "C", "extra.tex"))
    # A commit since the fold: the old board's live/ is not drift, a carried file is.
    Cr = os.path.join(G, "courses", "C")
    write(os.path.join(Cr, "live", "turns.jsonl"), '{"id": 0}\n')
    git(Cr, "add", "-f", "live/turns.jsonl")
    git(Cr, "commit", "-qm", "lesson transcript")
    got = cutover.course_drift(G, "overhaul", "C", excludes, tempfile.mkdtemp(dir=box))
    check("a commit of the old board's live/ since the fold is no drift", got == [], got)
    write(os.path.join(Cr, "notes.tex"), "\\section{Committed}\n")
    git(Cr, "commit", "-qam", "edit")
    got = cutover.course_drift(G, "overhaul", "C", excludes, tempfile.mkdtemp(dir=box))
    check("a commit of a file the fold carried is", len(got) == 1
          and "notes.tex committed since the fold" in got[0], got)
    git(Cr, "reset", "-q", "--hard", "HEAD~2")

    pristine = os.path.join(box, "one", "pristine")
    subprocess.run(["cp", "-Rp", G, pristine], check=True)
    ctx = ctx_for(G, "one")
    ctx.put("pre", git(G, "rev-parse", "HEAD"))
    ctx.put("ref_sha", git(G, "rev-parse", "overhaul"))

    # ---- step 2 on fake daemons ----------------------------------------------
    fake = os.path.join(box, "one", "fake")
    cutover.write_exec(os.path.join(fake, "serve.py"), cutover.FAKE_BOARD)
    cutover.write_exec(os.path.join(fake, "bin", "tutor"), cutover.FAKE_TUTOR)
    cutover.write_exec(os.path.join(fake, "bin", "board"), cutover.FAKE_WAIT)
    agent = os.path.join(G, "research", "X", "live", "agent.json")
    port = cutover.free_port()
    cutover.launch_detached([sys.executable, os.path.join(fake, "bin", "tutor"),
                             "headless", "X"])
    cutover.launch_detached([sys.executable, os.path.join(fake, "serve.py"), "--root",
                             os.path.join(G, "research", "X"), "--port", str(port)])
    daemon = cutover.until(lambda: cutover.matching(r"tutor headless", ctx.scope), 20, 0.2)
    cutover.until(lambda: cutover.matching(r"board wait", ctx.scope), 20, 0.2)
    # A waiter the daemon replaced just before the kill: nobody's child.
    cutover.launch_detached([sys.executable, os.path.join(fake, "bin", "board"), "wait",
                             "--timeout", "300"])
    cutover.until(lambda: len(cutover.matching(r"board wait", ctx.scope)) == 2, 20, 0.2)
    cutover.until(lambda: cutover.http(port, "/health", timeout=2)[0] == 200, 20, 0.2)
    with open(agent) as fh:
        before_agent = fh.read()
    rec = json.loads(before_agent)
    rec.update({"pid": daemon[0].pid, "state": "thinking", "owed": "m1"})
    cutover.write_json(agent, rec)
    shutil.copy2(agent, os.path.join(pristine, "research", "X", "live", "agent.json"))
    rested = {}

    def come_to_rest():
        time.sleep(2.5)
        rec.update({"state": "listening", "owed": None})
        cutover.write_json(agent, rec)
        shutil.copy2(agent, os.path.join(pristine, "research", "X", "live", "agent.json"))
        rested["at"] = time.time()
    threading.Thread(target=come_to_rest, daemon=True).start()
    cutover.step_stop(ctx)
    killed = ctx.m["killed"]
    check("step 2 waits for the tutor to come to rest before it kills it",
          rested.get("at") and killed and killed[0]["at"] >= rested["at"], (rested, killed))
    check("the daemon and its `board wait` are killed and recorded, with their workspace",
          len(killed) == 2 and killed[0]["workspace"] == "research/X"
          and len(killed[0]["children"]) == 1
          and not cutover.matching(r"tutor headless|board wait", ctx.scope), killed)
    check("an orphaned `board wait` is killed and recorded too",
          len(killed) == 2 and killed[1]["workspace"] is None
          and "board wait" in killed[1]["cmd"], killed)
    check("the --root board is stopped, its root and port recorded for the rollback",
          [b["port"] for b in ctx.m["old_boards"]] == [port]
          and cutover.http(port, "/health", timeout=2)[0] == 0, ctx.m["old_boards"])

    # ---- steps 3-8 -------------------------------------------------------------
    for n, fn in ((3, cutover.step_snapshot), (4, cutover.step_exclude),
                  (5, cutover.step_import), (6, cutover.step_courses),
                  (7, cutover.step_merge), (8, cutover.step_residue)):
        try:
            fn(ctx)
        except cutover.Abort as exc:
            check("step %d passes on the fixture" % n, False, exc)
            raise
    m = ctx.m
    check("step 3 bundles the Atlas and the course, and tars live/archive, "
          "transcripts and the course (and step 5 the sessions as imported)",
          len(m["bundles"]) == 2 and sorted(m["tars"]) == [
              "courses/C", "courses/C/transcripts", "research/X/live/archive", "sessions"],
          m["tars"])
    check("and keeps the tailscale capture", m["tailscale"] == {
        "TCP": {"9098": {"TCPForward": "127.0.0.1:9098"}}})
    check("step 4 appends /sessions/ and .ink/ to info/exclude",
          m["exclude_added"] == ["/sessions/", ".ink/"])
    sessions = [r["session"] for r in m["imports"]]
    check("step 5 imports each live/ into a session bound to its post-merge subject",
          sorted(r["subject"] for r in m["imports"])
          == ["courses/C", "projects/X", "projects/Y"] and all(sessions), m["imports"])
    marked = m.get("marked_read") or []
    sid_of = dict((r["subject"], r["session"]) for r in m["imports"])
    check("step 5 marks the line that would wake a turn read, and clears the owed "
          "message, with no turn; a quiet line stays for the next turn",
          sorted((r["session"], r["what"], r["text"]) for r in marked)
          == sorted([(sid_of["projects/X"], "line", "hi"),
                     (sid_of["courses/C"], "owed", "an old report, still owed")]), marked)
    rd = {}
    for subj, sid in sid_of.items():
        rd[subj] = [json.loads(l) for l in open(os.path.join(
            G, "sessions", sid, "inbox", "messages.jsonl")) if l.strip()] if os.path.isfile(
            os.path.join(G, "sessions", sid, "inbox", "messages.jsonl")) else []
    check("so nothing in the imported sessions waits for a turn",
          [x.get("read") for x in rd["projects/X"]] == [True]
          and [x.get("read") for x in rd["courses/C"]] == [None]
          and cutover.read_json(os.path.join(G, "sessions", sid_of["courses/C"],
                                             "agent.json")).get("owed") is None, rd)
    check("and no live/ is left, the stray one included",
          not cutover.workspaces(G) and not os.path.isdir(os.path.join(G, "live")))
    check("the tracked practice/Y/live the import moved was restored for the merge, "
          "which then deleted it",
          m["restored_tracked"] == ["practice/Y/live/cards/0001-old.md"]
          and not os.path.exists(os.path.join(G, "practice", "Y", "live")), m["restored_tracked"])
    check("step 6 moves the course's .git to the archive and drops transcripts/",
          not os.path.exists(os.path.join(G, "courses", "C", ".git"))
          and os.path.isdir(os.path.join(ctx.archive, "courses-git", "C.git"))
          and not os.path.exists(os.path.join(G, "courses", "C", "transcripts")))
    check("step 7 merges overhaul with the message, no fast-forward",
          git(G, "log", "-1", "--format=%s %p") .startswith(cutover.MERGE_MSG)
          and len(git(G, "log", "-1", "--format=%p").split()) == 2)
    check("step 8 sets the course's untracked leftovers aside in pre-fold/",
          os.path.isfile(os.path.join(ctx.archive, "pre-fold", "courses", "C", "Makefile")))
    env_now = open(os.path.join(G, "projects", "X", ".env")).read()
    check("and carries research/X's residue into projects/X, its .env rewritten",
          os.path.isfile(os.path.join(G, "projects", "X", ".venv", "pyvenv.cfg"))
          and "X_DATA=%s/projects/X/data" % G in env_now and "OTHER=/elsewhere" in env_now
          and not os.path.exists(os.path.join(G, "research")), env_now)
    check("git status is empty after step 8",
          git(G, "status", "--porcelain") == "", git(G, "status", "--porcelain"))
    check("the manifest is on disk after every change",
          cutover.read_json(ctx.manifest_path)["merged"] == m["merged"])

    # ---- the server's own leftovers, then the rollback ---------------------------
    write(os.path.join(G, "sessions", "20991231-000000", "session.json"), "{}\n")
    write(os.path.join(G, "projects", "X", "docs", "a", "a.pdf"), "%PDF\n")
    # The old boards come back through the old watch; here, by hand.
    cutover.launch_detached([sys.executable, os.path.join(fake, "serve.py"), "--root",
                             os.path.join(G, "research", "X"), "--port", str(port)])
    problems = cutover.rollback(cutover.Ctx(manifest=cutover.read_json(ctx.manifest_path),
                                            **cutover.read_json(ctx.manifest_path)["ctx"]))
    check("the rollback reports no problem", problems == [], problems)
    diff = cutover.compare_trees(G, pristine)
    check("the rollback restores the tree: compared with the copy made before, "
          "nothing differs", diff == [], "\n".join(diff[:40]))
    C1, C0 = os.path.join(G, "courses", "C"), os.path.join(pristine, "courses", "C")
    check("main is back at PRE, its status and the course repository's as before",
          git(G, "rev-parse", "HEAD") == m["pre"]
          and git(G, "status", "--porcelain") == git(pristine, "status", "--porcelain")
          and git(C1, "rev-parse", "HEAD") == snap
          and git(C1, "status", "--porcelain") == git(C0, "status", "--porcelain"),
          (git(G, "rev-parse", "HEAD"), m["pre"], git(G, "status", "--porcelain"),
           git(os.path.join(G, "courses", "C"), "rev-parse", "HEAD"), snap,
           git(os.path.join(G, "courses", "C"), "status", "--porcelain")))
    check("info/exclude is as it was",
          open(cutover.exclude_file(G)).read() == open(cutover.exclude_file(pristine)).read())
    left = os.path.join(ctx.archive, "rollback-leftovers")
    moved = [os.path.relpath(os.path.join(d, f), left) for d, _, fs in os.walk(left) for f in fs]
    check("what the new system made is set aside, not deleted",
          any(p.endswith("sessions-served/20991231-000000/session.json") for p in moved)
          and any(p.endswith("projects/X/docs/a/a.pdf") for p in moved), moved)
    check("the rollback waited for the old board to answer",
          cutover.http(port, "/health", timeout=2)[0] == 200)
    pushed = dict(cutover.read_json(ctx.manifest_path), pushed=True)
    try:
        cutover.rollback(cutover.Ctx(manifest=pushed, **pushed["ctx"]))
        refused = False
    except cutover.Abort:
        refused = True
    check("a rollback after the push is refused", refused)

    # =======================================================================
    # a merge that conflicts aborts, and the rollback undoes steps 3-6
    # =======================================================================
    G2, _ = fixture("two", conflict=True)
    pristine2 = os.path.join(box, "two", "pristine")
    subprocess.run(["cp", "-Rp", G2, pristine2], check=True)
    ctx2 = ctx_for(G2, "two")
    ctx2.put("pre", git(G2, "rev-parse", "HEAD"))
    for fn in (cutover.step_snapshot, cutover.step_exclude, cutover.step_import,
               cutover.step_courses):
        fn(ctx2)
    try:
        cutover.step_merge(ctx2)
        aborted = None
    except cutover.Abort as exc:
        aborted = str(exc)
    gitdir = git(G2, "rev-parse", "--absolute-git-dir")
    check("a conflicting merge aborts, leaving no merge in progress",
          aborted and "merge failed" in aborted
          and not os.path.exists(os.path.join(gitdir, "MERGE_HEAD")), aborted)
    problems = cutover.rollback(ctx2)
    diff = cutover.compare_trees(G2, pristine2)
    check("and the rollback restores the tree exactly", problems == [] and diff == [],
          (problems, diff[:40]))

    # =======================================================================
    # --plan changes nothing
    # =======================================================================
    before = git(G2, "status", "--porcelain", "--ignored")
    p = subprocess.run([sys.executable, os.path.join(BOARD, "scripts", "cutover.py"),
                        "--plan", "--atlas", G2], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
    steps = [l.split(".")[0] for l in p.stdout.splitlines() if l[:2].rstrip(".").isdigit()]
    check("--plan lists steps 1 to 12 in order and changes nothing",
          p.returncode == 0 and steps == [str(i) for i in range(1, 13)]
          and git(G2, "status", "--porcelain", "--ignored") == before, p.stdout[-2000:])

    # =======================================================================
    # --run starts only from Terminal, in a clean worktree at the ref
    # =======================================================================
    G3 = os.path.join(box, "three", "Atlas")
    os.makedirs(G3)
    git(G3, "init", "-q", "-b", "main")
    write(os.path.join(G3, "a.txt"), "a\n")
    git(G3, "add", "-A")
    git(G3, "commit", "-qm", "main")
    git(G3, "branch", "overhaul")
    wt = os.path.join(box, "three", "wt")
    git(G3, "worktree", "add", "-q", "--detach", wt, "overhaul")
    wt = os.path.realpath(wt)
    here = os.path.join(wt, "board", "scripts")
    os.makedirs(here)
    ok_env = {"PATH": fakebin}
    G3 = os.path.realpath(G3)

    def refusal(**kw):
        args = dict(here=here, cwd=wt, environ=ok_env, tty=True)
        args.update(kw)
        return cutover.run_refusal(G3, "overhaul", **args)
    check("--run starts from the top of a clean worktree at overhaul, from a terminal",
          refusal() is None, refusal())
    check("--run refuses the main checkout itself",
          "the checkout the cutover changes" in (refusal(here=G3, cwd=G3) or ""), refusal(here=G3, cwd=G3))
    check("--run refuses another directory as the cwd",
          "cd there first" in (refusal(cwd=box) or ""), refusal(cwd=box))
    check("--run refuses without a terminal, and inside a tutor turn",
          "not a terminal" in (refusal(tty=False) or "")
          and "tutor turn" in (refusal(environ=dict(ok_env, TUTORBOARD_TURN="1")) or ""))
    check("--run refuses without tailscale on PATH",
          "no tailscale" in (refusal(environ={"PATH": "/nonexistent"}) or ""))
    write(os.path.join(wt, "a.txt"), "changed\n")
    dirty = refusal()
    git(wt, "checkout", "-q", "--", "a.txt")
    write(os.path.join(G3, "b.txt"), "b\n")
    git(G3, "add", "b.txt")
    git(G3, "commit", "-qm", "b")
    git(G3, "branch", "-f", "overhaul", "main")
    behind = refusal()
    check("--run refuses a worktree with changes, or one not at the ref's tip",
          "uncommitted" in (dirty or "") and "not overhaul" in (behind or ""), (dirty, behind))
finally:
    for proc in cutover.matching(r".", box):
        cutover.kill_group(proc, signal.SIGKILL)
    shutil.rmtree(box, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("the cutover's steps run on a fixture, and the rollback undoes them exactly")
