#!/usr/bin/env python3
"""`board tools`: declarations written, committed and pushed from the board.

    python3 test/tooling.py

A fixture Atlas cloned from a bare origin holds the real board binary and a
root Brewfile. BOARD_TOOLS_NO_KICK keeps the install from starting, and the
state directories are temp dirs. brew, mise and upkeep are shims that only log.

  - add writes exactly one path, the Brewfile line, keeps the header, commits
    with `tools: declare <kind> <name>`, and the commit reaches origin.
  - --subject writes that subject's Brewfile.
  - a duplicate is refused, exit 1, and no commit is made.
  - an unknown subject is refused.
  - list reads the repository and tools.json, and touches no network.
  - an injected brew name or mise version is refused with no commit; --why
    lands as one line; `npm:@scope/pkg[@v]` parses, and its key is quoted.
  - the install is narrow: `brew bundle install --no-upgrade` on Brewfile.all
    for a brew, `mise install --locked -- <name>` for a pin; upkeep never runs.
  - a name shaped like an option (`-y`, `--force`) is refused for every kind,
    and `_tools_kick` passes no such name to mise.
  - mise trusts exactly the configs it reads there, reads none above the
    Atlas root and answers no prompt (MISE_YES=0) even when the caller's env
    says yes; a sibling config with [hooks] refuses the declaration, and
    `_tools_kick` starts no mise when a config in the chain fails, logging why.
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
           XDG_STATE_HOME=os.path.join(home, ".local", "state"),
           BOARD_STATE_DIR=os.path.join(work, "state"),
           TUTORBOARD_COURSES=atlas, BOARD_TOOLS_NO_KICK="1",
           GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           GIT_TERMINAL_PROMPT="0", MISE_YES="1",
           MISE_DEFAULT_TOOL_VERSIONS_FILENAME=".elsewhere")
for k in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "PYTHONPATH",
          "MISE_TRUSTED_CONFIG_PATHS", "MISE_ENV"):
    ENV.pop(k, None)


shims = os.path.join(work, "shims")
kick_marker = os.path.join(work, "kick.log")
for tool in ("mise", "brew", "upkeep"):
    write(os.path.join(shims, tool),
          '#!/bin/sh\nprintf \'%s %s @ %s nau=%s trust=%s yes=%s ceil=%s tvf=%s\\n\' '
          '"$(basename "$0")" "$*" "$PWD" "$HOMEBREW_NO_AUTO_UPDATE" '
          '"$MISE_TRUSTED_CONFIG_PATHS" "$MISE_YES" "$MISE_CEILING_PATHS" '
          '"$MISE_DEFAULT_TOOL_VERSIONS_FILENAME" >>"'
          + kick_marker + '"\n')
    os.chmod(os.path.join(shims, tool), 0o755)
ENV["PATH"] = shims + os.pathsep + ENV.get("PATH", "")
UNION = os.path.join(home, ".local", "state", "atlas-setup", "Brewfile.all")
# What every mise run must see: no auto-yes, no config read above the root,
# no other name for .tool-versions.
SAFE = " yes=0 ceil=%s tvf=" % work


def kicked(start, want=1):
    """The shim lines after the first `start`, once `want` of them start a kick."""
    for _ in range(200):
        lines = read(kick_marker).splitlines()[start:]
        if len([l for l in lines if " lock " not in l]) >= want:
            break
        time.sleep(0.05)
    return read(kick_marker).splitlines()[start:]


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
    before = read(os.path.join(atlas, "Brewfile"))
    code, out = board("tools", "add", "brew", 'jq"; system("touch PWNED"); brew "x')
    check("an injected brew name is refused, exit 1, with no write and no commit",
          code == 1 and "not declared" in out and git(atlas, "rev-parse", "HEAD") == head
          and read(os.path.join(atlas, "Brewfile")) == before, out)
    code, out = board("tools", "add", "cask", "evil/tap/thing")
    check("a tapped name whose tap is not in Brewfile.taps is refused",
          code == 1 and "not in Brewfile.taps" in out
          and git(atlas, "rev-parse", "HEAD") == head, out)
    toml_before = read(os.path.join(atlas, "mise.toml"))
    code, out = board("tools", "add", "mise", 'node@22"\n[hooks]\nenter = "touch PWNED')
    check("an injected mise version is refused, with no write and no commit",
          code == 1 and git(atlas, "rev-parse", "HEAD") == head
          and read(os.path.join(atlas, "mise.toml")) == toml_before, out)
    code, out = board("tools", "add", "brew", "ripgrep", "--why",
                      'search\nsystem("touch PWNED") "q" \\')
    check("--why lands as one comment line with no quote or backslash",
          code == 0 and read(os.path.join(atlas, "Brewfile")).endswith(
              'brew "ripgrep"  # search system(touch PWNED) q\n'),
          (out, read(os.path.join(atlas, "Brewfile"))))
    refused = []
    head = git(atlas, "rev-parse", "HEAD")
    toml_before = read(os.path.join(atlas, "mise.toml"))
    kick_before = read(kick_marker)
    for kind, spec in (("mise", "-y"), ("mise", "--yes"), ("mise", "-C"),
                       ("mise", "--force@1"), ("mise", "npm:-x"), ("brew", "-y"),
                       ("cask", "--force"), ("brew", "--HEAD")):
        code, out = board("tools", "add", kind, spec, env=dict(ENV, BOARD_TOOLS_NO_KICK=""))
        if code != 1 or "not declared" not in out:
            refused.append((kind, spec, code, out))
    check("a name shaped like an option is refused for every kind, with no write, "
          "commit or install",
          not refused and git(atlas, "rev-parse", "HEAD") == head
          and read(os.path.join(atlas, "mise.toml")) == toml_before
          and read(kick_marker) == kick_before, refused)
    code, out = board("tools", "add", "mise", "y-1@2", "--why", "a dash inside is fine")
    check("and a dash inside a name is not refused",
          code == 0 and 'y-1 = "2"  # a dash inside is fine' in read(
              os.path.join(atlas, "mise.toml")), out)
    code, out = board("tools", "add", "mise", "npm:@scope/pkg")
    code2, out2 = board("tools", "add", "mise", "npm:prettier@3.3.0")
    text = read(os.path.join(atlas, "mise.toml"))
    check("a backend spec parses and its key is quoted, @version or not",
          code == 0 and code2 == 0 and '"npm:@scope/pkg" = "latest"\n' in text
          and '"npm:prettier" = "3.3.0"\n' in text
          and git(atlas, "log", "-1", "--format=%s") == "tools: pin npm:prettier 3.3.0",
          (out, out2, text))

    head = git(atlas, "rev-parse", "HEAD")
    env = dict(ENV)
    env.pop("BOARD_TOOLS_NO_KICK", None)
    start = len(read(kick_marker).splitlines())
    code, out = board("tools", "add", "brew", "htop", env=env)
    got = kicked(start)
    check("add installs a brew narrowly: brew bundle --no-upgrade on Brewfile.all, "
          "no brew update",
          code == 0 and got == ["brew bundle install --no-upgrade --file=%s @ %s nau=1 trust= "
                                "yes=1 ceil= tvf=.elsewhere" % (UNION, atlas)]
          and 'brew "htop"' in read(UNION) and 'brew "jq"' in read(UNION)
          and "the install is running in the background" in out
          and git(atlas, "rev-parse", "HEAD") != head, (out, got))
    check("and never runs upkeep", not [l for l in read(kick_marker).splitlines()
                                        if l.startswith("upkeep ")], read(kick_marker))
    start = len(read(kick_marker).splitlines())
    code, out = board("tools", "add", "mise", "python@3.12", env=env)
    got = kicked(start)
    check("add installs a mise pin narrowly: mise install --locked -- <name> in its "
          "directory",
          code == 0 and got[-1:] == ["mise install --locked -- python @ %s nau= trust=%s%s"
                                     % (atlas, os.path.join(atlas, "mise.toml"), SAFE)]
          and not [l for l in got if l.startswith(("brew ", "upkeep "))], (out, got))
    check("and mise lock and install trust that mise.toml alone, read nothing above "
          "the root and answer no prompt, whatever MISE_YES the caller had",
          got == ["mise lock @ %s nau= trust=%s%s" % (atlas, os.path.join(atlas, "mise.toml"),
                                                     SAFE),
                  "mise install --locked -- python @ %s nau= trust=%s%s"
                  % (atlas, os.path.join(atlas, "mise.toml"), SAFE)], got)

    # A config mise would also read there, with [hooks], refuses the pin.
    sibling = os.path.join(atlas, ".mise.toml")
    write(sibling, '[hooks]\npreinstall = "touch PWNED"\n')
    head = git(atlas, "rev-parse", "HEAD")
    toml_before = read(os.path.join(atlas, "mise.toml"))
    start = len(read(kick_marker).splitlines())
    code, out = board("tools", "add", "mise", "ruby@3.3", env=env)
    check("a sibling .mise.toml with [hooks] refuses the pin: exit 1, no write, "
          "no commit, no mise run",
          code == 1 and ".mise.toml" in out and "edit it by hand" in out
          and git(atlas, "rev-parse", "HEAD") == head
          and read(os.path.join(atlas, "mise.toml")) == toml_before
          and read(kick_marker).splitlines()[start:] == [], out)

    # _tools_kick itself re-checks the chain before mise runs.
    import importlib.util
    from importlib.machinery import SourceFileLoader
    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(env)
    try:
        spec = importlib.util.spec_from_loader("board_cli",
                                               SourceFileLoader("board_cli", BOARD))
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        started = cli._tools_kick(atlas, {"kind": "mise", "name": "ruby", "target": atlas})
        log = read(os.path.join(home, ".local", "state", "atlas-setup", "declare.log"))
        time.sleep(0.3)
        check("_tools_kick starts no mise when a config in the chain fails, and logs why",
              started is False and "ruby not installed: .mise.toml has a [hooks] table" in log
              and read(kick_marker).splitlines()[start:] == [], (started, log))
        os.remove(sibling)
        before_kick = read(kick_marker)
        started = cli._tools_kick(atlas, {"kind": "mise", "name": "-y", "target": atlas})
        time.sleep(0.3)
        check("_tools_kick passes no option-shaped name to mise, even one declare never "
              "wrote", started is False and read(kick_marker) == before_kick, started)
        started = cli._tools_kick(atlas, {"kind": "mise", "name": "ruby", "target": atlas})
        got = kicked(start)
        check("and starts it, trusting the checked mise.toml only, once the chain is clean",
              started is True and got == ["mise install --locked -- ruby @ %s nau= trust=%s%s"
                                          % (atlas, os.path.join(atlas, "mise.toml"), SAFE)],
              got)
    finally:
        os.environ.clear()
        os.environ.update(saved)

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
