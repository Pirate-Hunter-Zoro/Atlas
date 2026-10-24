#!/usr/bin/env python3
"""gitops against a bare remote: a save pushes, and a pull fast-forwards.

`tutorboard/gitops.py` is every commit, push and pull the board makes. Here it
runs against real repositories in a temp dir: a bare origin standing in for
GitHub, and a second clone standing in for a laptop.
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

from tutorboard import gitops  # noqa: E402

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


def ident(root):
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")


def clone(origin, dest):
    subprocess.run(["git", "clone", "-q", origin, dest], check=True)
    ident(dest)


work = tempfile.mkdtemp(prefix="gitremote-")
try:
    origin = os.path.join(work, "atlas.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin], check=True)
    seed = os.path.join(work, "atlas-seed")
    subprocess.run(["git", "init", "-q", "-b", "main", seed], check=True)
    ident(seed)
    write(os.path.join(seed, "README.md"), "atlas\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "seed")
    git(seed, "remote", "add", "origin", origin)
    git(seed, "push", "-q", "-u", "origin", "main")

    mac = os.path.join(work, "mac")
    laptop = os.path.join(work, "laptop")
    clone(origin, mac)
    clone(origin, laptop)
    check("the fixture: the Mac's clone is clean",
          git(mac, "status", "--porcelain") == "")

    # --- a save pushes ------------------------------------------------------
    write(os.path.join(mac, "courses", "T", "notes.md"), "a proof\n")
    write(os.path.join(mac, "scratch.txt"), "not named\n")
    ok, said = gitops.save(mac, ["courses/T"], "T: a proof")
    check("a save commits the named path", ok and "committed: T: a proof" in said)
    check("and pushes it", git(origin, "rev-parse", "main")
          == git(mac, "rev-parse", "HEAD"))
    check("and carries nothing it was not given",
          git(mac, "show", "--name-only", "--format=", "HEAD") == "courses/T/notes.md"
          and "?? scratch.txt" in git(mac, "status", "--porcelain"))
    check("and the message goes in exactly as given, no trailers",
          git(mac, "log", "-1", "--format=%B") == "T: a proof")
    os.remove(os.path.join(mac, "scratch.txt"))

    # --- the laptop pushes; the Mac's next save merges it and pushes --------
    git(laptop, "pull", "-q", "--ff-only")
    write(os.path.join(laptop, "projects", "P", "src", "a.py"), "x = 1\n")
    git(laptop, "add", "-A")
    git(laptop, "commit", "-qm", "code")
    git(laptop, "push", "-q")
    write(os.path.join(mac, "courses", "T", "notes.md"), "a better proof\n")
    ok, said = gitops.save(mac, ["courses/T"], "T: a better proof")
    check("a save behind origin merges it in and pushes",
          ok and "merged origin/main" in said
          and git(origin, "rev-parse", "main") == git(mac, "rev-parse", "HEAD")
          and os.path.isfile(os.path.join(mac, "projects", "P", "src", "a.py")))
    ok, said = gitops.save(mac, ["courses/T"], "nothing new")
    check("a save with nothing new commits nothing and says so",
          ok and "nothing to commit" in said and "already up to date" in said)

    # --- the refusal hook ---------------------------------------------------
    write(os.path.join(mac, "courses", "T", "held.py"), "x = 1\n")
    head = git(mac, "rev-parse", "HEAD")
    asked = []
    ok, said = gitops.commit(mac, ["courses/T"], "held",
                             refuse=lambda p: asked.append(p) or "held")
    check("refuse(paths) sees the paths and its reason stops the commit",
          not ok and said == "held" and asked == [["courses/T"]]
          and git(mac, "rev-parse", "HEAD") == head)
    os.remove(os.path.join(mac, "courses", "T", "held.py"))

    # --- the laptop pushes; the Mac pulls and stays clean -------------------
    git(laptop, "pull", "-q", "--ff-only")
    write(os.path.join(laptop, "projects", "P", "src", "b.py"), "y = 2\n")
    git(laptop, "add", "-A")
    git(laptop, "commit", "-qm", "more code")
    git(laptop, "push", "-q")

    said = []
    got = gitops.pull(mac, quiet=True, say=said.append)
    check("a pull fast-forwards to origin",
          got is True and git(mac, "rev-parse", "HEAD")
          == git(origin, "rev-parse", "main"))
    check("so git status --porcelain is empty",
          git(mac, "status", "--porcelain") == "")
    check("and it says how many commits came",
          any("pulled 1 commit(s)" in l for l in said))

    # --- the guards ----------------------------------------------------------
    git(mac, "checkout", "-q", "--detach")
    check("a pull on a detached HEAD is refused",
          gitops.pull(mac, quiet=True) is False)
    git(mac, "checkout", "-q", "main")

    src = open(os.path.join(ROOT, "tutorboard", "gitops.py"), encoding="utf-8").read()
    check("a push is never forced",
          "--force" not in src and '"-f"' not in src and "+refs" not in src)
    check("and git never waits on a prompt", 'GIT_TERMINAL_PROMPT": "0"' in src)

    # A repository that carries its own .githooks/ gets them on its first commit.
    hooked = os.path.join(work, "hooked")
    subprocess.run(["git", "init", "-q", "-b", "main", hooked], check=True)
    ident(hooked)
    write(os.path.join(hooked, ".githooks", "commit-msg"), "#!/bin/sh\nexit 0\n")
    write(os.path.join(hooked, "a.md"), "a\n")
    ok, said = gitops.commit(hooked, ["."], "first")
    check("a repository with .githooks/ has them turned on at its first commit",
          ok and git(hooked, "config", "core.hooksPath") == ".githooks")

    # ai-config is its own repository: the ear moves it forward on its own
    # clock, relinks it when it moved, and leaves a diverged copy alone.
    pbase = os.path.join(work, "private-base")
    pstate = os.path.join(work, "private-state")
    os.makedirs(pbase)
    check("no ai-config is nothing to do",
          gitops.sync_private(pbase, pstate, now=1000) is None)
    lone = os.path.join(pbase, gitops.AI_CONFIG)
    subprocess.run(["git", "init", "-q", lone], check=True)
    heard = []
    got = gitops.sync_private(pbase, pstate, now=1000, say=heard.append)
    check("an ai-config with no origin is nothing to pull, not a refusal",
          got == {"pulled": None, "moved": False, "linked": None,
                  "why": "no origin"} and not heard)
    shutil.rmtree(lone)
    os.remove(os.path.join(pstate, gitops.PRIVATE_STAMP))
    porigin = os.path.join(work, "ai-config.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", porigin], check=True)
    pseed = os.path.join(work, "ai-config-seed")
    subprocess.run(["git", "init", "-q", "-b", "main", pseed], check=True)
    ident(pseed)
    write(os.path.join(pseed, "scripts", "install.sh"),
          'touch "$PWD/linked.marker"\n')
    git(pseed, "add", "-A")
    git(pseed, "commit", "-qm", "p1")
    git(pseed, "remote", "add", "origin", porigin)
    git(pseed, "push", "-q", "origin", "main")
    prepo = os.path.join(pbase, gitops.AI_CONFIG)
    subprocess.run(["git", "clone", "-q", porigin, prepo], check=True)
    ident(prepo)
    heard = []
    got = gitops.sync_private(pbase, pstate, now=1000, say=heard.append)
    check("with nothing new it pulls, moves nothing and relinks nothing",
          got == {"pulled": True, "moved": False, "linked": None, "why": ""}
          and not os.path.exists(os.path.join(prepo, "linked.marker"))
          and not heard)
    check("and a second try inside the interval does not run",
          gitops.sync_private(pbase, pstate, now=1000 + gitops.PRIVATE_EVERY - 1)
          is None)
    write(os.path.join(pseed, "INSTRUCTIONS.md"), "new rule\n")
    git(pseed, "add", "-A")
    git(pseed, "commit", "-qm", "p2")
    git(pseed, "push", "-q", "origin", "main")
    got = gitops.sync_private(pbase, pstate, now=1000 + gitops.PRIVATE_EVERY,
                              say=heard.append)
    check("a new commit is pulled, and install.sh relinks it",
          got["moved"] and got["linked"] is True
          and os.path.exists(os.path.join(prepo, "INSTRUCTIONS.md"))
          and os.path.exists(os.path.join(prepo, "linked.marker"))
          and heard and heard[-1].startswith("ai-config: moved to"))
    with open(os.path.join(pstate, gitops.PRIVATE_STAMP), encoding="utf-8") as fh:
        stamped = json.load(fh)
    check("the try is stamped, with the head it left",
          stamped["head"] == git(prepo, "rev-parse", "HEAD"))
    write(os.path.join(pseed, "scripts", "install.sh"), "exit 3\n")
    git(pseed, "commit", "-qam", "p3")
    git(pseed, "push", "-q", "origin", "main")
    got = gitops.sync_private(pbase, pstate, now=1000 + 2 * gitops.PRIVATE_EVERY,
                              say=heard.append)
    check("an install.sh that fails is said, not hidden",
          got["moved"] and got["linked"] is False and "install.sh failed" in heard[-1])
    write(os.path.join(prepo, "local.md"), "mine\n")
    git(prepo, "add", "-A")
    git(prepo, "commit", "-qm", "local")
    write(os.path.join(pseed, "other.md"), "theirs\n")
    git(pseed, "add", "-A")
    git(pseed, "commit", "-qm", "p4")
    git(pseed, "push", "-q", "origin", "main")
    mine = git(prepo, "rev-parse", "HEAD")
    got = gitops.sync_private(pbase, pstate, now=1000 + 3 * gitops.PRIVATE_EVERY,
                              say=heard.append)
    check("a copy with its own commits is refused and left exactly as it was",
          got["pulled"] is False and not got["moved"] and got["linked"] is None
          and git(prepo, "rev-parse", "HEAD") == mine
          and heard[-1].startswith("ai-config: not moved forward"))
finally:
    shutil.rmtree(work, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a save pushes, a pull fast-forwards, and ai-config moves forward on its own")
