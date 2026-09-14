#!/usr/bin/env python3
"""Putting a machine right does not take somebody's afternoon with it.

`scripts/catch-up.sh` brings a machine onto what was pushed from elsewhere.
Until 2026-09-03 it did that by resetting each of eleven course repositories
onto its origin, on one condition -- diverged OR dirty -- and the dirty half was
a bug with teeth. A repository sitting exactly on origin with uncommitted work
in the tree took the reset branch: the tag it wrote first was placed at HEAD,
which already was origin, so it preserved nothing, and the reset then threw the
work away to move the repository nowhere. It did that to two research
repositories in one afternoon, four times, before anybody worked out what was
doing it.

**The eleven are one now, and the reset is gone with them.** There is one
working tree, and one `--ff-only` pull that cannot rewrite history, cannot move
a dirty tree and cannot lose a commit -- the worst it does is decline. So the
stash and the tag are not guards that were removed; they were rails on a cliff,
and this file is now the proof that the cliff is not there.

What is still guarded, and each of these still costs an afternoon when it goes
wrong:

* work that was never pushed is still in the working tree afterwards;
* commits origin does not have are still commits;
* a repository somebody is part-way through an operation in is not touched, and
  says which operation;
* a detached HEAD is not walked onto a branch;
* the board's own scratch is not mistaken for somebody's work.

Exercised against real git repositories in a temporary tree, through the real
script, because the value of this file is that it runs what ships rather than a
description of it.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, "scripts", "catch-up.sh")

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def git(root, *args, **kw):
    """Run one git command in a repository and return its stdout.

    Args:
        root (str): Repository working tree.
        *args (str): Arguments after `git`.

    Returns:
        str: Standard output, stripped.
    """
    p = subprocess.run(["git", "-C", root] + list(args), capture_output=True,
                       text=True, **kw)
    return p.stdout.strip()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def make_atlas(work, name):
    """One repository with an origin, and workspaces in three families.

    The shape the real one has: `atlas.json` at the root, a family directory,
    and workspaces inside it that are directories rather than repositories.
    Each case gets a private remote, because sharing one made the outcome of a
    case depend on which case ran before it -- a test that passes for the wrong
    reason.

    Returns:
        tuple[str, str]: The working tree, and a seed clone of the same origin
            standing in for the other machine.
    """
    origin = os.path.join(work, ".remotes", name + ".git")
    os.makedirs(os.path.dirname(origin), exist_ok=True)
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin], check=True)

    seed = os.path.join(work, ".seeds", name)
    write(os.path.join(seed, "atlas.json"), json.dumps({"families": [
        {"id": "courses", "name": "Courses"},
        {"id": "research", "name": "Research"},
        {"id": "vendor", "name": "Vendor", "vendor": True},
    ]}))
    for rel in ("courses/Galois-Theory", "courses/Probability",
                "research/PSYCH-ASR"):
        write(os.path.join(seed, rel, "tutorboard.json"),
              json.dumps({"name": os.path.basename(rel)}))
        write(os.path.join(seed, rel, "README.md"), "seed\n")
    # Somebody else's repository, and a directory that is not a workspace at
    # all. Neither may turn up in the report.
    write(os.path.join(seed, "vendor", "colibri", "README.md"), "not mine\n")
    write(os.path.join(seed, "notes", "scratch.txt"), "not a workspace\n")

    subprocess.run(["git", "init", "-q", "-b", "main", seed], check=True)
    git(seed, "config", "user.email", "t@t")
    git(seed, "config", "user.name", "t")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "seed")
    git(seed, "remote", "add", "origin", origin)
    git(seed, "push", "-q", "origin", "main")

    root = os.path.join(work, name)
    subprocess.run(["git", "clone", "-q", origin, root], check=True)
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    return root, seed


def run(root):
    """Run the real script against one temporary repository.

    `--courses-only` is the repository and the workspaces and nothing that
    touches a process: no restarts and no machine report.
    """
    env = dict(os.environ, TUTORBOARD_COURSES=root,
               TUTORBOARD_CATCHUP_LOG=os.path.join(root, "catch-up.log"))
    p = subprocess.run(["bash", SCRIPT, "--courses-only"], capture_output=True,
                       text=True, env=env)
    return p.stdout + p.stderr


check("the command ships with the tool", os.path.isfile(SCRIPT))
src = open(SCRIPT, encoding="utf-8").read() if os.path.isfile(SCRIPT) else ""

check("it cannot reset, force or stash, because a --ff-only pull cannot need to",
      "reset --hard" not in src and "stash push" not in src
      and "--force" not in src)
check("and the board's own scratch does not count as somebody's work",
      "grep -v '/live/'" in src)
check("nothing is done to a repository part-way through an operation",
      "rebase-merge" in src and "HEAD is detached" in src)
check("what ran it is recorded, because working that out took longer than "
      "fixing what it did",
      "CATCHUP_LOG" in src and "ps -o args=" in src)

work = tempfile.mkdtemp(prefix="catchup-")
try:
    # ---- CASE 1: current, and dirty. The one that used to destroy work. ----
    current, _ = make_atlas(work, "Current")
    write(os.path.join(current, "courses", "Galois-Theory", "afternoon.md"),
          "hours of it\n")
    with open(os.path.join(current, "research", "PSYCH-ASR", "README.md"), "a") as fh:
        fh.write("edited\n")
    out = run(current)

    check("a repository already on origin is left alone, uncommitted work and all",
          os.path.isfile(os.path.join(current, "courses", "Galois-Theory",
                                      "afternoon.md"))
          and "edited" in open(os.path.join(current, "research", "PSYCH-ASR",
                                            "README.md")).read())
    check("nothing was stashed from it either, because nothing touched it",
          git(current, "stash", "list") == "")
    check("and it names the workspace the uncommitted work is in, not just a count",
          "courses/Galois-Theory: 1 uncommitted file" in out
          and "research/PSYCH-ASR: 1 uncommitted file" in out)
    check("a workspace with nothing outstanding says so too, so the report is "
          "the whole list rather than only the bad news",
          "courses/Probability: current" in out)
    check("somebody else's repository is not a workspace and is not reported on",
          "vendor/colibri" not in out)
    check("and neither is a directory that is simply a directory",
          "notes/scratch" not in out)

    # ---- CASE 2: behind. It fast-forwards, and the work in the tree stays. --
    behind, behind_seed = make_atlas(work, "Behind")
    write(os.path.join(behind_seed, "courses", "Probability", "landed.md"),
          "from the other machine\n")
    git(behind_seed, "add", "-A")
    git(behind_seed, "commit", "-qm", "landed elsewhere")
    git(behind_seed, "push", "-q", "origin", "main")
    write(os.path.join(behind, "courses", "Galois-Theory", "afternoon.md"),
          "hours of it\n")
    out = run(behind)

    check("a repository that is behind is fast-forwarded",
          os.path.isfile(os.path.join(behind, "courses", "Probability",
                                      "landed.md")))
    check("and the uncommitted work is still in the tree, not in a stash",
          os.path.isfile(os.path.join(behind, "courses", "Galois-Theory",
                                      "afternoon.md"))
          and git(behind, "stash", "list") == "")
    check("and it says how far it moved", "pulled 1 commit(s)" in out)

    # ---- CASE 3: holding commits origin does not have. -------------------
    # This is the case the tag was invented for. There is nothing to tag now,
    # because nothing resets: the pull declines and the commits are simply
    # still there.
    ahead, _ = make_atlas(work, "Ahead")
    write(os.path.join(ahead, "courses", "Galois-Theory", "local.md"),
          "never pushed\n")
    git(ahead, "add", "-A")
    git(ahead, "commit", "-qm", "only here")
    ahead_head = git(ahead, "rev-parse", "HEAD")
    out = run(ahead)

    check("a repository holding commits origin lacks keeps them, with no tag "
          "needed, because nothing was ever going to reset it",
          git(ahead, "rev-parse", "HEAD") == ahead_head)
    check("and the file those commits added is still there",
          os.path.isfile(os.path.join(ahead, "courses", "Galois-Theory",
                                      "local.md")))

    # ---- MID-OPERATION ---------------------------------------------------
    # Stashing under a rebase is not a rescue: it can succeed and leave the
    # operation half-applied. Nothing is touched and the operation is named.
    rebasing, rebasing_seed = make_atlas(work, "Rebasing")
    write(os.path.join(rebasing_seed, "courses", "Probability", "landed.md"), "x\n")
    git(rebasing_seed, "add", "-A")
    git(rebasing_seed, "commit", "-qm", "landed elsewhere")
    git(rebasing_seed, "push", "-q", "origin", "main")
    git(rebasing, "checkout", "-q", "-b", "side")
    write(os.path.join(rebasing, "courses", "Galois-Theory", "README.md"), "mine\n")
    git(rebasing, "add", "-A")
    git(rebasing, "commit", "-qm", "mine")
    git(rebasing, "checkout", "-q", "main")
    write(os.path.join(rebasing, "courses", "Galois-Theory", "README.md"), "theirs\n")
    git(rebasing, "add", "-A")
    git(rebasing, "commit", "-qm", "theirs")
    git(rebasing, "checkout", "-q", "side")
    git(rebasing, "rebase", "main")          # conflicts, and stops
    rebasing_head = git(rebasing, "rev-parse", "HEAD")
    out = run(rebasing)

    check("a repository part-way through a rebase is left exactly as it is",
          git(rebasing, "rev-parse", "HEAD") == rebasing_head)
    check("and it says which operation is outstanding",
          "rebase-merge is outstanding" in out or "rebase-apply is outstanding" in out)

    # ---- DETACHED --------------------------------------------------------
    # `origin/HEAD` exists in most clones, so without a guard `rev-parse
    # --abbrev-ref HEAD` returning "HEAD" was read as a branch name and the
    # repository was reset onto the remote's default branch under them.
    detached, _ = make_atlas(work, "Detached")
    write(os.path.join(detached, "courses", "Probability", "second.md"), "x\n")
    git(detached, "add", "-A")
    git(detached, "commit", "-qm", "second")
    git(detached, "push", "-q", "origin", "main")
    detached_head = git(detached, "rev-parse", "HEAD~1")
    git(detached, "checkout", "-q", "HEAD~1")
    out = run(detached)

    check("a detached HEAD is not walked onto a branch",
          git(detached, "rev-parse", "HEAD") == detached_head)
    check("and it says so", "HEAD is detached" in out)

    # ---- THE BOARD'S OWN SCRATCH -----------------------------------------
    scratch, _ = make_atlas(work, "Scratch")
    write(os.path.join(scratch, "courses", "Probability", "live", "board.json"),
          "{}\n")
    out = run(scratch)
    check("a board churning in live/ is not somebody's uncommitted work",
          "courses/Probability: current" in out)

    # ---- THE LOG ---------------------------------------------------------
    check("and every run leaves a record of what invoked it",
          os.path.isfile(os.path.join(scratch, "catch-up.log")))
finally:
    shutil.rmtree(work, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("putting a machine right cannot take an afternoon with it")
