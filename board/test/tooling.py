#!/usr/bin/env python3
"""`board tools`: declarations written, committed and pushed from the board.

    python3 test/tooling.py

A fixture Atlas cloned from a bare origin holds the real board binary and a
root Brewfile. BOARD_TOOLS_NO_KICK keeps the install from starting, and the
state directories are temp dirs.

  - add writes exactly one path, the Brewfile line, keeps the header, commits
    with `tools: declare <kind> <name>`, and the commit reaches origin.
  - --subject writes that subject's Brewfile.
  - a duplicate is refused, exit 1, and no commit is made.
  - an unknown subject is refused.
  - list reads the repository and tools.json, and touches no network.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(os.path.dirname(HERE), "bin", "board")

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)[:2000]) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


work = os.path.realpath(tempfile.mkdtemp(prefix="tooling-"))
home = os.path.join(work, "home")
atlas = os.path.join(work, "atlas")
origin = os.path.join(work, "atlas.git")
ENV = dict(os.environ, HOME=home,
           XDG_CONFIG_HOME=os.path.join(home, ".config"),
           BOARD_STATE_DIR=os.path.join(work, "state"),
           TUTORBOARD_COURSES=atlas, BOARD_TOOLS_NO_KICK="1",
           GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           GIT_TERMINAL_PROMPT="0")
for k in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "PYTHONPATH"):
    ENV.pop(k, None)


shims = os.path.join(work, "shims")
write(os.path.join(shims, "mise"), "#!/bin/sh\nexit 0\n")
os.chmod(os.path.join(shims, "mise"), 0o755)
kick_marker = os.path.join(work, "kick.log")
write(os.path.join(shims, "upkeep"),
      '#!/bin/sh\nprintf \'%s\\n\' "$*" >>"' + kick_marker + '"\n')
os.chmod(os.path.join(shims, "upkeep"), 0o755)
ENV["PATH"] = shims + os.pathsep + ENV.get("PATH", "")


def run(argv, cwd=None, env=None):
    p = subprocess.run(argv, cwd=cwd or work, env=env or ENV, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
    return p.returncode, p.stdout


def git(root, *args):
    return run(["git", "-C", root] + list(args))[1].strip()


def board(*args, **kw):
    return run([sys.executable, BOARD] + list(args), cwd=atlas, env=kw.get("env"))


def commit_paths():
    said = git(atlas, "show", "--pretty=format:", "--name-only", "HEAD")
    return [l for l in said.splitlines() if l.strip()]


try:
    run(["git", "init", "-q", "--bare", "-b", "main", origin])
    run(["git", "init", "-q", "-b", "main", atlas])
    git(atlas, "config", "user.email", "t@t")
    git(atlas, "config", "user.name", "t")
    write(os.path.join(atlas, "Brewfile"), '# the root\nbrew "uv"\n')
    write(os.path.join(atlas, "courses", "C", "tutorboard.json"),
          json.dumps({"check": "true"}))
    write(os.path.join(atlas, "courses", "C", "note.md"), "a note\n")
    run(["git", "-C", atlas, "add", "-A"])
    run(["git", "-C", atlas, "commit", "-qm", "seed"])
    git(atlas, "remote", "add", "origin", origin)
    git(atlas, "push", "-q", "-u", "origin", "main")

    code, out = board("tools", "add", "brew", "jq", "--why", "json")
    text = read(os.path.join(atlas, "Brewfile"))
    check("add writes the root Brewfile line and keeps its header",
          code == 0 and text == '# the root\nbrew "uv"\nbrew "jq"  # json\n',
          (out, text))
    check("add commits exactly one path, with `tools: declare <kind> <name>`",
          git(atlas, "log", "-1", "--format=%s") == "tools: declare brew jq"
          and commit_paths() == ["Brewfile"], (git(atlas, "log", "-1", "--format=%s"),
                                               commit_paths()))
    check("and the commit lands on origin",
          git(origin, "rev-parse", "main") == git(atlas, "rev-parse", "HEAD")
          and not git(atlas, "status", "--porcelain"), out)

    head = git(atlas, "rev-parse", "HEAD")
    before = read(os.path.join(atlas, "Brewfile"))
    code, out = board("tools", "add", "brew", "jq")
    check("a duplicate is refused, exit 1, and makes no commit",
          code == 1 and "already declared" in out
          and git(atlas, "rev-parse", "HEAD") == head
          and read(os.path.join(atlas, "Brewfile")) == before, out)

    code, out = board("tools", "add", "cask", "font-x", "--subject", "courses/C",
                      "--why", "a face")
    check("add --subject writes that subject's Brewfile",
          code == 0
          and read(os.path.join(atlas, "courses", "C", "Brewfile"))
          == 'cask "font-x"  # a face\n'
          and git(atlas, "log", "-1", "--format=%s") == "tools: declare cask font-x"
          and commit_paths() == ["courses/C/Brewfile"], (out, commit_paths()))
    check("and that commit lands on origin too",
          git(origin, "rev-parse", "main") == git(atlas, "rev-parse", "HEAD"), out)

    code, out = board("tools", "add", "mise", "node@22", "--why", "the runtime")
    check("add mise pins a version in the root mise.toml and commits it",
          code == 0
          and read(os.path.join(atlas, "mise.toml"))
          == "# Pinned toolchains, installed by `mise install --locked`.\n"
             '[tools]\nnode = "22"  # the runtime\n'
          and git(atlas, "log", "-1", "--format=%s") == "tools: pin node 22"
          and commit_paths() == ["mise.toml"], (out, read(os.path.join(atlas, "mise.toml")),
                                                commit_paths()))

    head = git(atlas, "rev-parse", "HEAD")
    code, out = board("tools", "add", "brew", "bat", "--subject", "courses/Nope")
    check("an unknown subject is refused and no commit is made",
          code == 1 and "no subject" in out
          and git(atlas, "rev-parse", "HEAD") == head, out)

    code, out = board("tools", "list")
    check("list names each declaration with its kind, path and subject",
          code == 0 and "brew" in out and "jq" in out and "Brewfile" in out
          and "cask" in out and "font-x" in out
          and "mise" in out and "node" in out and "mise.toml" in out
          and "courses/C/Brewfile" in out and "courses/C" in out, out)

    head = git(atlas, "rev-parse", "HEAD")
    env = dict(ENV)
    env.pop("BOARD_TOOLS_NO_KICK", None)
    code, out = board("tools", "add", "brew", "htop", env=env)
    for _ in range(100):
        if os.path.exists(kick_marker) and read(kick_marker).strip():
            break
        time.sleep(0.05)
    check("add starts upkeep with `run --force` when it is on the PATH",
          code == 0 and read(kick_marker).splitlines()[-1:] == ["run --force"]
          and git(atlas, "rev-parse", "HEAD") != head, (out, read(kick_marker)))

    os.makedirs(os.path.join(origin, "hooks"), exist_ok=True)
    hook = os.path.join(origin, "hooks", "pre-receive")
    write(hook, "#!/bin/sh\nexit 1\n")
    os.chmod(hook, 0o755)
    origin_head = git(origin, "rev-parse", "main")
    code, out = board("tools", "add", "brew", "wget")
    check("a rejected push exits 0, keeps the commit local and leaves origin alone",
          code == 0 and git(atlas, "rev-parse", "HEAD") != origin_head
          and git(origin, "rev-parse", "main") == origin_head
          and git(atlas, "log", "-1", "--format=%s") == "tools: declare brew wget"
          and "the commit is local" in out, out)
finally:
    shutil.rmtree(work, ignore_errors=True)

print("%d FAILURES" % len(fails) if fails
      else "board tools declares, commits and pushes what the repository installs")
sys.exit(1 if fails else 0)
