#!/usr/bin/env python3
"""The Mac hears laptops without the cluster, and nothing diverges.

What the checks are about:

  * ONE MAIN. A Mac clone holding a local End commit (its push failed), and a
    laptop clone's `board code --end` (`code.end`), end on one main after one
    `sync.Sync` pass: the Mac merges origin's main and pushes, around
    uncommitted work it leaves as it was.
  * END PUSHES. `sessions.end` commits and pushes.
  * ONLY THE BOARD'S. Origin is public: neither `sessions.end` nor the sync
    thread publishes an unpushed commit of the owner's, merges over one, or
    pushes a branch other than main. A board push sends the sha it checked,
    and the ledger never notes a commit of the owner's landing beside its
    own. A main not tracking origin's is never merged.
  * NOTHING LOST. A staged file: no merge, `skipped: staged changes` in
    pull.json and in the sync health, the staged file still staged. A dirty
    file the merge would overwrite: git refuses, no merge is left standing,
    the working change is intact. A real conflict: refused, nothing moves.
    An ignored file the other side force-added: git refuses, the file is
    intact, on the merge and the fast-forward alike. Passes refused the same
    way reuse one merge commit. `gitops.push` merges with a dirty tree under
    the same rules.
  * THE MOVE. `sync` holds what `cluster` re-exports, `cluster.Ear` is
    `sync.Sync`, and `Sync.hear` asks jobs only while jobs.py exists.

Synthetic repositories only: a bare origin per case, a "mac" clone (a board
checkout: `sessions/` is there) and a "laptop" clone. Stdlib only.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

box = tempfile.mkdtemp(prefix="tutor-sync-box-")
saved = dict(os.environ)
os.environ["TUTOR_SLURM"] = "0"
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ["XDG_CONFIG_HOME"] = os.path.join(box, "config")
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, "trash")
os.environ["BOARD_NO_TAILNET"] = "1"
# This machine's git config is not the test's: no signing, no push.default.
_gitconfig = os.path.join(box, "gitconfig")
with open(_gitconfig, "w") as _fh:
    _fh.write("[init]\n\tdefaultBranch = main\n")
os.environ["GIT_CONFIG_GLOBAL"] = _gitconfig
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
for name in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "TUTORBOARD_PORT",
             "TUTORBOARD_SYNC", "TUTORBOARD_CLUSTER", "TUTORBOARD_FRESH",
             "BOARD_CODE_END"):
    os.environ.pop(name, None)

from tutorboard import cluster, code, gitops, relay, sessions, sync  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)[:1500]) if detail
                                else ""))


def git(cwd, *args):
    """git's output; a fixture command that fails stops the test there."""
    p = subprocess.run(["git", "-C", cwd] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    if p.returncode != 0:
        raise RuntimeError("git %s in %s failed:\n%s"
                           % (" ".join(args), cwd, p.stdout))
    return p.stdout.strip()


def ok_git(cwd, *args):
    return subprocess.run(["git", "-C", cwd] + list(args),
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def head(where):
    return git(where, "rev-parse", "HEAD")


def merging(where):
    """Is a merge standing in `where`?"""
    return ok_git(where, "rev-parse", "-q", "--verify", "MERGE_HEAD")


class World(object):
    """A bare origin, a seeded main, and the clones made from it."""

    def __init__(self, name):
        self.dir = os.path.join(box, name)
        os.makedirs(self.dir)
        self.origin = os.path.join(self.dir, "origin.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main",
                        self.origin], check=True)
        seed = os.path.join(self.dir, "seed")
        os.makedirs(seed)
        git(seed, "init", "-q", "-b", "main")
        write(os.path.join(seed, ".gitignore"), "/sessions/\nai-config/\nign/\n")
        subj = os.path.join(seed, "projects", "P")
        write(os.path.join(subj, "tutorboard.json"),
              json.dumps({"name": "P", "phi": False}))
        write(os.path.join(subj, "TUTOR.md"), "# P\n")
        write(os.path.join(subj, "src", "a.py"), "a = 1\n")
        write(os.path.join(subj, "notes.md"), "notes\n")
        write(os.path.join(subj, "shared.md"), "shared\n")
        write(os.path.join(subj, "build", "out.txt"), "built 0\n")
        git(seed, "add", "-A")
        git(seed, "-c", "user.email=s@s", "-c", "user.name=s", "commit", "-qm",
            "seed")
        git(seed, "remote", "add", "origin", self.origin)
        git(seed, "push", "-q", "-u", "origin", "main")
        self.state = os.path.join(self.dir, "state")

    def clone(self, name):
        where = os.path.join(self.dir, name)
        git(self.dir, "clone", "-q", self.origin, where)
        git(where, "config", "user.email", "%s@example.com" % name)
        git(where, "config", "user.name", name)
        return where

    def main(self):
        return git(self.origin, "rev-parse", "main")

    def sync(self, mac):
        return sync.Sync(mac, state_dir=self.state, say=lambda m: None)

    def pulled(self):
        try:
            with open(os.path.join(self.state, sync.PULL_STATE)) as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}


def commit(where, rel, text, msg):
    write(os.path.join(where, rel), text)
    git(where, "add", "--", rel)
    git(where, "commit", "-qm", msg)


def board_commit(where, rel, text, msg):
    """A commit the board makes (`gitops.commit`), so a board push may
    publish it."""
    if text is not None:
        write(os.path.join(where, rel), text)
    ok, said = gitops.commit(where, [rel], msg)
    if not ok or not said.startswith("committed"):
        raise RuntimeError("gitops.commit of %s failed: %s" % (rel, said))


def unreachable(where):
    """How many commits in `where` nothing reaches."""
    out = git(where, "fsck", "--unreachable", "--no-reflogs")
    return sum(1 for l in out.splitlines() if l.startswith("unreachable commit"))


class Meddle(object):
    """Run `act` once, just before (or just after, `after`) the first git
    command `gitops` runs whose first words are `words`."""

    def __init__(self, words, act, after=False):
        self.words, self.act, self.after, self.done = words, act, after, False

    def __enter__(self):
        real = self.real = gitops._git

        def meddled(root, *args, **kw):
            hit = not self.done and args[:len(self.words)] == self.words
            if hit and not self.after:
                self.done = True
                self.act()
            got = real(root, *args, **kw)
            if hit and self.after:
                self.done = True
                self.act()
            return got
        gitops._git = meddled
        return self

    def __exit__(self, *exc):
        gitops._git = self.real


def laptop_end(w, laptop, sid, rel, text):
    """`board code <sid> <rel>` then `--end` on the laptop, as the command
    runs them. The exit code and what it said."""
    said = []
    rec, probs = code.start(laptop, sid, [rel], cwd=laptop)
    if probs:
        return 1, probs
    write(os.path.join(laptop, rel), text)
    rc = code.end(laptop, sid, title="the laptop's edit", say=said.append,
                  wait=1)
    return rc, said


try:
    # ======================================================================
    # the move: sync holds it, cluster re-exports it
    # ======================================================================
    check("cluster re-exports sync until the exit deletes it, Ear an alias",
          cluster.Ear is sync.Sync and cluster.Sync is sync.Sync
          and cluster.wake is sync.wake and cluster.notices is sync.notices
          and cluster.notices_path is sync.notices_path
          and cluster.atlas_of is sync.atlas_of
          and cluster.PULL_STATE == sync.PULL_STATE == "pull.json")
    app_src = read(os.path.join(ROOT, "tutorboard", "server", "app.py"))
    plist = read(os.path.join(ROOT, "scripts", "launchd", "tutor-board.plist"))
    check("app.py starts the thread on TUTORBOARD_SYNC, or the old name until "
          "the plist is re-rendered; the plist says TUTORBOARD_SYNC",
          "TUTORBOARD_SYNC" in app_src and "TUTORBOARD_CLUSTER" in app_src
          and "sync.Sync(atlas).start()" in app_src
          and "<key>TUTORBOARD_SYNC</key>" in plist
          and "TUTORBOARD_CLUSTER" not in plist)

    # ======================================================================
    # one main: a local End commit beside a laptop's --end
    # ======================================================================
    w = World("one-main")
    mac, laptop = w.clone("mac"), w.clone("laptop")
    sid = sessions.new("a lesson", base=mac)["id"]
    sessions.bind(sid, "projects/P", base=mac)

    # End pushes, when origin answers.
    write(os.path.join(mac, "projects", "P", "TUTOR.md"), "# P\n\nlesson one\n")
    _rec, ok, said = sessions.end(sid, base=mac)
    check("sessions.end commits and pushes",
          ok and "pushed main to origin" in said and head(mac) == w.main()
          and git(mac, "log", "-1", "--format=%s").endswith("ended"), said)

    # The next End's push fails: the commit stays here, ahead of origin.
    sid2 = sessions.new("a second lesson", base=mac)["id"]
    sessions.bind(sid2, "projects/P", base=mac)
    write(os.path.join(mac, "projects", "P", "TUTOR.md"),
          "# P\n\nlesson one\n\nlesson two\n")
    git(mac, "remote", "set-url", "origin", os.path.join(w.dir, "gone.git"))
    _rec, ok, said = sessions.end(sid2, base=mac)
    git(mac, "remote", "set-url", "origin", w.origin)
    end_commit = head(mac)
    check("an End whose push fails keeps its commit here, ahead of origin",
          ok and ("nothing was pushed" in said or "push failed" in said),
          said)
    check("(the fixture: the Mac holds a local End commit origin lacks)",
          not ok_git(mac, "merge-base", "--is-ancestor", end_commit,
                     "origin/main") and end_commit != w.main())

    # The owner's uncommitted work on the Mac, which no sync may touch.
    write(os.path.join(mac, "projects", "P", "notes.md"), "notes, being edited\n")
    write(os.path.join(mac, "projects", "P", "scratch.txt"), "untracked\n")

    rc, said = laptop_end(w, laptop, "20261023-090000",
                          "projects/P/src/a.py", "a = 2  # the laptop\n")
    lap = head(laptop)
    check("the laptop's `board code --end` commits and pushes",
          rc == 0 and w.main() == lap, said)

    s = w.sync(mac)
    got = s.once()
    mac_head = head(mac)
    check("one sync pass: the Mac and origin end on one main",
          got["pulled"] is True and mac_head == w.main(),
          git(mac, "log", "--oneline", "--graph", "-6"))
    check("which holds the Mac's End commit and the laptop's --end",
          ok_git(mac, "merge-base", "--is-ancestor", end_commit, mac_head)
          and ok_git(mac, "merge-base", "--is-ancestor", lap, mac_head)
          and read(os.path.join(mac, "projects", "P", "src", "a.py"))
          == "a = 2  # the laptop\n")
    check("as one merge commit over both, never a rewrite",
          git(mac, "rev-list", "--parents", "-1", mac_head).split()[1:]
          == [end_commit, lap])
    git(laptop, "fetch", "-q", "origin")
    check("so the laptop fast-forwards to it",
          ok_git(laptop, "merge-base", "--is-ancestor", lap, "origin/main"))
    check("and the Mac's uncommitted work is exactly as it was",
          read(os.path.join(mac, "projects", "P", "notes.md"))
          == "notes, being edited\n"
          and read(os.path.join(mac, "projects", "P", "scratch.txt"))
          == "untracked\n"
          and git(mac, "diff", "--cached", "--name-only") == ""
          and not merging(mac))
    rec = w.pulled()
    check("pull.json says the merge went through",
          rec.get("ok") is True and rec.get("step") == "merge", rec)
    got = s.once()
    check("and the next pass has nothing to do",
          got["pulled"] is False and head(mac) == w.main() == mac_head)

    # ======================================================================
    # a staged file: skipped, nothing lost
    # ======================================================================
    board_commit(mac, "projects/P/mac.md", "the Mac's\n", "the Mac moves on")
    mine = head(mac)
    git(laptop, "pull", "-q", "--ff-only")
    commit(laptop, "projects/P/laptop.md", "the laptop's\n", "the laptop moves on")
    git(laptop, "push", "-q")
    write(os.path.join(mac, "projects", "P", "staged.md"), "staged\n")
    git(mac, "add", "--", "projects/P/staged.md")
    got = s.once()
    rec = w.pulled()
    check("a Mac with a staged file is not merged: skipped: staged changes",
          got["pulled"] is False and head(mac) == mine
          and rec.get("ok") is False and rec.get("step") == "merge"
          and rec.get("said") == "skipped: staged changes"
          and rec.get("remote") == w.main(), rec)
    check("nothing is lost: the file is still staged, no merge stands",
          git(mac, "diff", "--cached", "--name-only") == "projects/P/staged.md"
          and read(os.path.join(mac, "projects", "P", "staged.md"))
          == "staged\n" and not merging(mac)
          and read(os.path.join(mac, "projects", "P", "notes.md"))
          == "notes, being edited\n")
    told = relay.health(mac, state_dir=w.state, fresh=True)
    check("and the sync health says so",
          told["synced"] is False
          and "not synced: skipped: staged changes" in told["lines"], told)
    board_commit(mac, "projects/P/staged.md", None, "the staged file")
    got = s.once()
    check("committed, the next pass merges and pushes",
          got["pulled"] is True and head(mac) == w.main()
          and os.path.isfile(os.path.join(mac, "projects", "P", "laptop.md"))
          and relay.health(mac, state_dir=w.state, fresh=True)["synced"])

    # ======================================================================
    # a dirty file the merge would overwrite: git refuses, nothing moves
    # ======================================================================
    git(laptop, "pull", "-q", "--ff-only")
    commit(laptop, "projects/P/shared.md", "shared, the laptop's\n",
           "the laptop edits shared.md")
    git(laptop, "push", "-q")
    board_commit(mac, "projects/P/mac2.md", "more\n", "the Mac moves on again")
    mine = head(mac)
    write(os.path.join(mac, "projects", "P", "shared.md"),
          "shared, the owner typing\n")
    got = s.once()
    rec = w.pulled()
    check("a dirty file the merge would bring: git refuses, recorded",
          got["pulled"] is False and rec.get("ok") is False
          and rec.get("step") == "merge" and "git refused" in rec.get("said", ""),
          rec)
    check("no merge is left standing, HEAD and the index are where they were",
          not merging(mac) and head(mac) == mine
          and git(mac, "diff", "--cached", "--name-only") == "")
    left = unreachable(mac)
    for _ in range(3):
        s.once()
    check("passes refused the same way leave no new unreachable commit each",
          unreachable(mac) == left and left <= 1 and head(mac) == mine,
          (left, unreachable(mac)))
    check("and the working change is intact",
          read(os.path.join(mac, "projects", "P", "shared.md"))
          == "shared, the owner typing\n"
          and read(os.path.join(mac, "projects", "P", "notes.md"))
          == "notes, being edited\n")
    # The owner keeps the edit out of the way; the next pass merges.
    os.rename(os.path.join(mac, "projects", "P", "shared.md"),
              os.path.join(w.dir, "shared.md.kept"))
    git(mac, "checkout", "-q", "--", "projects/P/shared.md")
    got = s.once()
    check("with the overlap gone the next pass merges and pushes",
          got["pulled"] is True and head(mac) == w.main()
          and read(os.path.join(mac, "projects", "P", "shared.md"))
          == "shared, the laptop's\n")

    # ======================================================================
    # a real conflict: refused, nothing moves
    # ======================================================================
    git(laptop, "pull", "-q", "--ff-only")
    commit(laptop, "projects/P/notes.md", "notes, the laptop's\n", "laptop notes")
    git(laptop, "push", "-q")
    board_commit(mac, "projects/P/notes.md", "notes, the Mac's\n", "Mac notes")
    write(os.path.join(mac, "projects", "P", "src", "a.py"), "a = 3  # typing\n")
    mine = head(mac)
    got = s.once()
    rec = w.pulled()
    check("a conflict outside build output is not merged, naming the file",
          got["pulled"] is False and rec.get("ok") is False
          and "projects/P/notes.md" in rec.get("said", "")
          and head(mac) == mine and not merging(mac)
          and read(os.path.join(mac, "projects", "P", "src", "a.py"))
          == "a = 3  # typing\n", rec)
    git(mac, "checkout", "-q", "--", "projects/P/src/a.py")

    # ======================================================================
    # only the board's: the owner's unpushed commits and branches stay here
    # ======================================================================
    w3 = World("foreign")
    mac3, lap3 = w3.clone("mac"), w3.clone("laptop")
    commit(mac3, "projects/P/draft.md", "private\n", "WIP do not push")
    owners = head(mac3)
    commit(lap3, "projects/P/lap.md", "lap\n", "lap")
    git(lap3, "push", "-q")
    s3 = w3.sync(mac3)
    got = s3.once()
    rec = w3.pulled()
    check("an unpushed commit of the owner's: the sync merges nothing and "
          "pushes nothing",
          got["pulled"] is False and head(mac3) == owners
          and w3.main() == head(lap3)
          and not ok_git(w3.origin, "cat-file", "-e", owners)
          and rec.get("ok") is False
          and rec.get("said", "").startswith(gitops.FOREIGN)
          and "WIP do not push" in rec.get("said", ""), rec)
    sid3 = sessions.new("a lesson", base=mac3)["id"]
    sessions.bind(sid3, "projects/P", base=mac3)
    write(os.path.join(mac3, "projects", "P", "TUTOR.md"), "# P\n\nthree\n")
    _rec, ok, said = sessions.end(sid3, base=mac3)
    check("and sessions.end commits but does not publish it",
          ok and gitops.FOREIGN in said and "not pushed" in said
          and git(mac3, "log", "-1", "--format=%s").endswith("ended")
          and not ok_git(w3.origin, "cat-file", "-e", owners)
          and w3.main() == head(lap3), said)
    git(mac3, "checkout", "-q", "-b", "secret-feature")
    sid4 = sessions.new("another", base=mac3)["id"]
    sessions.bind(sid4, "projects/P", base=mac3)
    write(os.path.join(mac3, "projects", "P", "TUTOR.md"), "# P\n\nfour\n")
    _rec, ok, said = sessions.end(sid4, base=mac3)
    check("an End on a branch other than main pushes nothing",
          ok and "the board pushes only main" in said
          and "secret-feature" not in git(w3.origin, "branch", "--list")
          and not ok_git(mac3, "config", "--get",
                         "branch.secret-feature.merge"), said)

    git(mac3, "remote", "set-url", "origin", os.path.join(w3.dir, "gone.git"))
    got = s3.once()
    rec = w3.pulled()
    check("an origin that does not answer is named by git's own reason",
          got["pulled"] is None and rec.get("step") == "ls-remote"
          and "gone.git" in rec.get("said", "")
          and "repository exists" not in rec.get("said", ""), rec)

    # ======================================================================
    # the sha checked is the sha published; the ledger notes only its own
    # ======================================================================
    w5 = World("race")
    mac5, lap5 = w5.clone("mac"), w5.clone("laptop")
    board_commit(mac5, "projects/P/board.md", "board\n", "the board's")
    boards = head(mac5)
    commit(lap5, "projects/P/lap.md", "lap\n", "lap")
    git(lap5, "push", "-q")
    with Meddle(("push",), lambda: commit(mac5, "projects/P/owner.md",
                                          "private\n", "OWNER PRIVATE")):
        ok, said = gitops.push(mac5, board=True)
    owner = head(mac5)
    pushed = w5.main()
    check("a commit of the owner's landing just before a board push is not "
          "published: the push sends the sha it checked",
          ok and git(mac5, "log", "-1", "--format=%s", owner) == "OWNER PRIVATE"
          and not ok_git(w5.origin, "cat-file", "-e", owner)
          and ok_git(mac5, "merge-base", "--is-ancestor", boards, pushed)
          and git(w5.origin, "log", "--format=%s", "main").count("OWNER") == 0
          and git(mac5, "rev-parse", "origin/main") == pushed, said)
    ledger = os.path.join(mac5, ".git", gitops.LEDGER)
    write(os.path.join(mac5, "projects", "P", "board2.md"), "board2\n")
    with Meddle(("commit",), lambda: commit(mac5, "projects/P/owner2.md",
                                            "private\n", "OWNER AGAIN"),
                after=True):
        gitops.commit(mac5, ["projects/P/board2.md"], "the board's again")
    owner2 = head(mac5)
    check("and a commit of the owner's landing just after a board commit is "
          "never noted as the board's",
          owner2 not in read(ledger).split()
          and git(mac5, "log", "-1", "--format=%s") == "OWNER AGAIN"
          and gitops.FOREIGN in gitops.push(mac5, board=True)[1]
          and not ok_git(w5.origin, "cat-file", "-e", owner2))

    # ======================================================================
    # a main tracking nothing: no merge the board could never push
    # ======================================================================
    w6 = World("untracked-main")
    mac6, lap6 = w6.clone("mac"), w6.clone("laptop")
    git(mac6, "branch", "--unset-upstream")
    board_commit(mac6, "projects/P/mac.md", "mac\n", "the Mac's")
    mine = head(mac6)
    commit(lap6, "projects/P/lap.md", "lap\n", "lap")
    git(lap6, "push", "-q")
    s6 = w6.sync(mac6)
    for _ in range(3):
        got = s6.once()
    check("a main that does not track origin's is never merged",
          got["pulled"] is False and head(mac6) == mine
          and w6.main() == head(lap6) and w6.pulled().get("ok") is False,
          (git(mac6, "log", "--oneline", "-3"), w6.pulled()))

    # ======================================================================
    # an ignored file the other side force-added: git refuses
    # ======================================================================
    w4 = World("ignored")
    mac4, lap4 = w4.clone("mac"), w4.clone("laptop")
    write(os.path.join(lap4, "projects", "P", "ign", "x.txt"), "theirs\n")
    git(lap4, "add", "-f", "--", "projects/P/ign/x.txt")
    git(lap4, "commit", "-qm", "force-added")
    git(lap4, "push", "-q")
    data = os.path.join(mac4, "projects", "P", "ign", "x.txt")
    write(data, "MINE IGNORED DATA\n")
    s4 = w4.sync(mac4)
    before = head(mac4)
    got = s4.once()
    check("the fast-forward refuses to overwrite an ignored file",
          got["pulled"] is False and head(mac4) == before
          and read(data) == "MINE IGNORED DATA\n", w4.pulled())
    board_commit(mac4, "projects/P/mac.md", "mac\n", "the Mac's")
    before = head(mac4)
    got = s4.once()
    rec = w4.pulled()
    check("and so does the merge, leaving no merge standing",
          got["pulled"] is False and head(mac4) == before
          and read(data) == "MINE IGNORED DATA\n" and not merging(mac4)
          and rec.get("step") == "merge" and "git refused" in rec.get("said", ""),
          rec)

    # ======================================================================
    # gitops.push: merges around a dirty tree under the same rules
    # ======================================================================
    w2 = World("push")
    mac2, lap2 = w2.clone("mac"), w2.clone("laptop")
    commit(lap2, "projects/P/build/out.txt", "built by the laptop\n", "lap build")
    commit(lap2, "projects/P/lap.md", "lap\n", "lap")
    git(lap2, "push", "-q")
    commit(mac2, "projects/P/build/out.txt", "built by the Mac\n", "mac build")
    write(os.path.join(mac2, "projects", "P", "notes.md"), "dirty\n")
    write(os.path.join(mac2, "projects", "P", "TUTOR.md"), "# P\n\nnew\n")
    ok, said = gitops.commit(mac2, ["projects/P/TUTOR.md"], "TUTOR.md")
    ok, said = gitops.push(mac2)
    check("gitops.push merges origin with a dirty tree, keeping this "
          "machine's build output, and pushes",
          ok and "merged origin/main; kept this machine's build output" in said
          and head(mac2) == w2.main()
          and read(os.path.join(mac2, "projects", "P", "build", "out.txt"))
          == "built by the Mac\n"
          and read(os.path.join(mac2, "projects", "P", "notes.md")) == "dirty\n"
          and not merging(mac2), said)
    git(lap2, "pull", "-q", "--ff-only")
    commit(lap2, "projects/P/notes.md", "lap notes\n", "lap notes")
    git(lap2, "push", "-q")
    commit(mac2, "projects/P/mac.md", "mac\n", "mac")
    mine = head(mac2)
    ok, said = gitops.push(mac2)
    check("an overlap with the dirty tree: git refuses, nothing is pushed, "
          "no merge stands, the change is intact",
          not ok and "git refused" in said and head(mac2) == mine
          and not merging(mac2)
          and read(os.path.join(mac2, "projects", "P", "notes.md")) == "dirty\n"
          and w2.main() != mine, said)
    write(os.path.join(mac2, "projects", "P", "extra.md"), "x\n")
    git(mac2, "add", "--", "projects/P/extra.md")
    ok, said = gitops.push(mac2)
    check("and with something staged it is not merged at all",
          not ok and gitops.STAGED in said and head(mac2) == mine
          and git(mac2, "diff", "--cached", "--name-only")
          == "projects/P/extra.md", said)
    src = read(os.path.join(ROOT, "tutorboard", "gitops.py")) \
        + read(os.path.join(ROOT, "tutorboard", "sync.py"))
    check("nothing in gitops or sync aborts a merge, resets, stashes or "
          "checks out over the tree",
          all(('"%s"' % word) not in src
              for word in ("--abort", "reset", "stash", "--hard", "checkout",
                           "restore", "read-tree", "--force", "-f")))

    # ======================================================================
    # Sync.hear asks jobs only while jobs.py exists
    # ======================================================================
    import types
    import tutorboard
    real = importlib.util.find_spec
    asked = []
    fake = types.ModuleType("tutorboard.jobs")
    fake.__spec__ = importlib.util.spec_from_loader("tutorboard.jobs", None)
    fake.hear = lambda root: asked.append(root) or [{"heard": root}]
    had = (sys.modules.get("tutorboard.jobs"),
           getattr(tutorboard, "jobs", None))

    def no_jobs(name, *a, **kw):
        if name == "tutorboard.jobs":
            return None
        return real(name, *a, **kw)

    sys.modules["tutorboard.jobs"] = fake
    tutorboard.jobs = fake
    try:
        with_jobs = s.hear()
        asked_with = list(asked)
        del asked[:]
        importlib.util.find_spec = no_jobs
        try:
            without = s.hear()
        finally:
            importlib.util.find_spec = real
    finally:
        sys.modules.pop("tutorboard.jobs", None)
        tutorboard.__dict__.pop("jobs", None)
        if had[0] is not None:
            sys.modules["tutorboard.jobs"] = had[0]
        if had[1] is not None:
            tutorboard.jobs = had[1]
    check("with jobs.py, Sync.hear asks jobs.hear for every subject",
          len(asked_with) == 1 and with_jobs == [{"heard": asked_with[0]}],
          (asked_with, with_jobs))
    check("without jobs.py, Sync.hear never asks it and hears nothing",
          without == [] and asked == [], (asked, without))
finally:
    os.environ.clear()
    os.environ.update(saved)
    shutil.rmtree(box, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("the Mac hears laptops without the cluster: one main after one pass, "
      "and nothing staged or uncommitted is lost")
