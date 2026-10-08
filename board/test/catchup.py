#!/usr/bin/env python3
"""Putting a machine right does not take somebody's afternoon with it.

`scripts/catch-up.sh` brings a machine onto what was pushed from elsewhere:
Atlas, which holds every course and project, then ai-config, the one private
repository nested inside it, which Atlas ignores and so cannot pull. Every pull is
`--ff-only`, which cannot rewrite history, cannot move a dirty tree and cannot
lose a commit; the worst it does is decline. Nothing resets, stashes or tags. A
reset keyed on DIRTY throws away the afternoon of somebody sitting exactly on
origin, and this file is the proof that no such branch exists.

What is still guarded, and each of these still costs an afternoon when it goes
wrong:

* ai-config is pulled from its OWN origin, on its own line, and Atlas being
  busy never leaves it behind;
* uncommitted work is reported per workspace, a course like any other;
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


def make_repo(origin, seed, files):
    """A bare origin, and a seed repository that has pushed `files` to it.

    Args:
        origin (str): Path of the bare repository to create.
        seed (str): Path of the working repository to create and push from.
        files (dict[str, str]): Relative path -> content, committed as one.
    """
    os.makedirs(os.path.dirname(origin), exist_ok=True)
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin], check=True)
    for rel, text in files.items():
        write(os.path.join(seed, rel), text)
    subprocess.run(["git", "init", "-q", "-b", "main", seed], check=True)
    git(seed, "config", "user.email", "t@t")
    git(seed, "config", "user.name", "t")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "seed")
    git(seed, "remote", "add", "origin", origin)
    git(seed, "push", "-q", "origin", "main")


def clone(origin, root):
    subprocess.run(["git", "clone", "-q", origin, root], check=True)
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")


def make_atlas(work, name):
    """Atlas with an origin, its courses tracked content, and ai-config nested.

    The shape the real one has: family directories, workspaces inside them,
    every course and project a directory of Atlas. ai-config is the one
    repository of its own, cloned into ai-config/ and ignored by Atlas, so
    Atlas's pull does not move it. Each case gets private remotes, because
    sharing one made the outcome of a case depend on which case ran before it
    -- a test that passes for the wrong reason.

    Returns:
        tuple[str, str, str]: The Atlas working tree, a seed clone of Atlas's
            origin standing in for the other machine, and ai-config's seed,
            standing in for the other machine too.
    """
    remotes = os.path.join(work, ".remotes", name)
    seeds = os.path.join(work, ".seeds", name)
    files = {
        ".gitignore": "/ai-config/\n",
        "research/PSYCH-ASR/tutorboard.json": json.dumps({"name": "PSYCH-ASR"}),
        "research/PSYCH-ASR/README.md": "seed\n",
        # Somebody else's repository, and a directory that is not a workspace
        # at all. Neither may turn up in the report.
        "vendor/colibri/README.md": "not mine\n",
        "notes/scratch.txt": "not a workspace\n",
    }
    for course in ("Galois-Theory", "Probability"):
        files["courses/%s/tutorboard.json" % course] = json.dumps(
            {"name": course, "phi": False})
        files["courses/%s/README.md" % course] = "seed\n"
    seed = os.path.join(seeds, "Atlas")
    make_repo(os.path.join(remotes, "Atlas.git"), seed, files)
    root = os.path.join(work, name)
    clone(os.path.join(remotes, "Atlas.git"), root)

    aseed = os.path.join(seeds, "ai-config")
    aorigin = os.path.join(remotes, "ai-config.git")
    make_repo(aorigin, aseed, {"README.md": "seed\n"})
    clone(aorigin, os.path.join(root, "ai-config"))
    return root, seed, aseed


def push_from(seed, rel, text, msg):
    """Commit one file in a seed and push it: work landing from elsewhere."""
    write(os.path.join(seed, rel), text)
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", msg)
    git(seed, "push", "-q", "origin", "main")


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
      "grep -Ev '(^|/)live/'" in src)
check("nothing is done to a repository part-way through an operation",
      "rebase-merge" in src and "HEAD is detached" in src)
check("each workspace's dirt is asked of git under that workspace alone",
      'git -C "$root" status --porcelain -- .' in src)
check("what ran it is recorded, because working that out took longer than "
      "fixing what it did",
      "CATCHUP_LOG" in src and "ps -o args=" in src)

work = tempfile.mkdtemp(prefix="catchup-")
try:
    # ---- CASE 1: current, and dirty. The one that used to destroy work. ----
    current, _, _ = make_atlas(work, "Current")
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
    check("Atlas sees the course: it is Atlas's own content",
          "courses/Galois-Theory/afternoon.md"
          in git(current, "status", "--porcelain", "-uall", "--", "courses"))
    check("and it names the workspace the uncommitted work is in, a course "
          "like any other",
          "courses/Galois-Theory: 1 uncommitted file" in out
          and "research/PSYCH-ASR: 1 uncommitted file" in out)
    check("a workspace with nothing outstanding says so too, so the report is "
          "the whole list rather than only the bad news",
          "courses/Probability: current" in out)
    check("ai-config gets its own line from the pull",
          "ai-config: already current" in out)
    check("and no course is treated as a repository of its own",
          "not its own repository" not in out
          and "courses/Probability: already current" not in out
          and not os.path.exists(os.path.join(current, "courses",
                                              "Probability", ".git")))
    check("somebody else's repository is not a workspace and is not reported on",
          "vendor/colibri" not in out)
    check("and neither is a directory that is simply a directory",
          "notes/scratch" not in out)

    # ---- CASE 2: behind. Atlas and ai-config both fast-forward. ----------
    behind, behind_seed, behind_ai = make_atlas(work, "Behind")
    push_from(behind_seed, "courses/Probability/landed.md",
              "from the other machine\n", "landed elsewhere")
    push_from(behind_ai, "landed.md", "from the other machine\n",
              "landed elsewhere")
    push_from(behind_ai, "landed2.md", "and more\n", "landed again")
    write(os.path.join(behind, "courses", "Galois-Theory", "afternoon.md"),
          "hours of it\n")
    out = run(behind)

    check("Atlas, behind, is fast-forwarded, a course's work with it",
          os.path.isfile(os.path.join(behind, "courses", "Probability",
                                      "landed.md"))
          and "pulled 1 commit(s)" in out)
    check("and ai-config behind ITS origin is fast-forwarded from it",
          os.path.isfile(os.path.join(behind, "ai-config", "landed2.md"))
          and "ai-config: pulled 2 commit(s)" in out)
    check("and the uncommitted work in the other course is still in the tree, "
          "not in a stash",
          os.path.isfile(os.path.join(behind, "courses", "Galois-Theory",
                                      "afternoon.md"))
          and git(behind, "stash", "list") == ""
          and "courses/Galois-Theory: 1 uncommitted file" in out)

    # ---- CASE 3: holding commits origin does not have. -------------------
    # Nothing resets, so there is nothing to tag: the pull is a no-op and the
    # commits are simply still there.
    ahead, _, _ = make_atlas(work, "Ahead")
    write(os.path.join(ahead, "courses", "Galois-Theory", "local.md"),
          "never pushed\n")
    git(ahead, "add", "-A")
    git(ahead, "commit", "-qm", "only here")
    ahead_head = git(ahead, "rev-parse", "HEAD")
    out = run(ahead)

    check("Atlas holding commits its origin lacks keeps them, with no tag "
          "needed, because nothing was ever going to reset it",
          git(ahead, "rev-parse", "HEAD") == ahead_head
          and os.path.isfile(os.path.join(ahead, "courses", "Galois-Theory",
                                          "local.md")))
    check("and, committed, the course is not reported as uncommitted",
          "courses/Galois-Theory: current" in out)

    # ---- MID-OPERATION, in ai-config -------------------------------------
    # Stashing under a rebase is not a rescue: it can succeed and leave the
    # operation half-applied. Nothing is touched and the operation is named,
    # and Atlas is still pulled.
    rebasing, rebasing_seed, rebasing_ai = make_atlas(work, "Rebasing")
    push_from(rebasing_seed, "courses/Probability/landed.md", "x\n",
              "landed elsewhere")
    push_from(rebasing_ai, "landed.md", "x\n", "landed elsewhere")
    ai = os.path.join(rebasing, "ai-config")
    git(ai, "checkout", "-q", "-b", "side")
    write(os.path.join(ai, "README.md"), "mine\n")
    git(ai, "add", "-A")
    git(ai, "commit", "-qm", "mine")
    git(ai, "checkout", "-q", "main")
    write(os.path.join(ai, "README.md"), "theirs\n")
    git(ai, "add", "-A")
    git(ai, "commit", "-qm", "theirs")
    git(ai, "checkout", "-q", "side")
    git(ai, "rebase", "main")          # conflicts, and stops
    rebasing_head = git(ai, "rev-parse", "HEAD")
    out = run(rebasing)

    check("ai-config part-way through a rebase is left exactly as it is",
          git(ai, "rev-parse", "HEAD") == rebasing_head
          and not os.path.isfile(os.path.join(ai, "landed.md")))
    check("and it says which operation is outstanding",
          "ai-config: rebase-merge is outstanding" in out
          or "ai-config: rebase-apply is outstanding" in out)
    check("and Atlas is pulled regardless",
          os.path.isfile(os.path.join(rebasing, "courses", "Probability",
                                      "landed.md")))

    # ---- DETACHED, in Atlas ----------------------------------------------
    # `origin/HEAD` exists in most clones, so without a guard `rev-parse
    # --abbrev-ref HEAD` returning "HEAD" was read as a branch name and the
    # repository was reset onto the remote's default branch under them. A
    # detached Atlas is no reason to leave ai-config behind.
    detached, _, detached_ai = make_atlas(work, "Detached")
    write(os.path.join(detached, "research", "PSYCH-ASR", "second.md"), "x\n")
    git(detached, "add", "-A")
    git(detached, "commit", "-qm", "second")
    git(detached, "push", "-q", "origin", "main")
    detached_head = git(detached, "rev-parse", "HEAD~1")
    git(detached, "checkout", "-q", "HEAD~1")
    push_from(detached_ai, "landed.md", "x\n", "landed elsewhere")
    out = run(detached)

    check("a detached HEAD is not walked onto a branch",
          git(detached, "rev-parse", "HEAD") == detached_head)
    check("and it says so", "HEAD is detached" in out)
    check("and ai-config is still pulled, because Atlas's state is Atlas's",
          "ai-config: pulled 1 commit(s)" in out)

    # ---- THE BOARD'S OWN SCRATCH -----------------------------------------
    scratch, _, _ = make_atlas(work, "Scratch")
    write(os.path.join(scratch, "courses", "Probability", "live", "board.json"),
          "{}\n")
    write(os.path.join(scratch, "research", "PSYCH-ASR", "live", "board.json"),
          "{}\n")
    out = run(scratch)
    check("a board churning in live/ is not somebody's uncommitted work",
          "courses/Probability: current" in out
          and "research/PSYCH-ASR: current" in out)

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
