#!/usr/bin/env python3
"""Atlas's upkeep hook: upkeep.d/hook and scripts/brew-upgrade.py (`atlas-brew`).

    python3 test/brew_upgrade.py

A fixture Atlas in a temp dir holds the real scripts/brew-upgrade.py,
scripts/tools.sh and upkeep.d/hook, with board/ a link to this one. HOME, the
XDG directories, the board's state and upkeep's state are temp dirs, and uv,
mise, tailscale, launchctl and brew are shims first on the PATH that log their
argv; the suite refuses to run when one resolves anywhere else. Nothing is
installed or upgraded on this machine.

  - PROTECTED-CASKS: tailscale on the host while it runs as a brew service,
    nothing on a coding laptop or without the service.
  - BREWFILES: the union of the root Brewfile and each subject's, written
    once, its path printed; upkeep.d/hook reaches the same answer.
  - AFTER-BREW: a broken .venv is re-synced with `uv sync --locked --extra
    test`; one uv cannot fix is a problem.
  - TOOLCHAIN: uv's Pythons, `mise install --locked <tools>` in each mise
    directory, `mise prune --tools` of the pinned tools, tools.sh update; a
    failure is tool:<name>; a dry run mutates nothing. `mise lock` runs only
    for a missing lock, a toml unlike HEAD's or a tool the lock lacks: never
    on a clean checkout or a fresh clone whose lock is older by mtime.
  - STATUS: problems, failed tools and tools.json lines but pins, exit 0;
    the host's board agent and reachability report only.
  - atlas-brew status, install and usage; brewcare's upkeep and hook lines.
  - upkeep calls every phase the hook knows.
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
ATLAS_REAL = os.path.dirname(BOARD)
sys.path.insert(0, BOARD)

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)[:2000]) if detail else ""))


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    if mode:
        os.chmod(path, mode)


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


work = os.path.realpath(tempfile.mkdtemp(prefix="atlas-hook-"))
home = os.path.join(work, "home")
shims = os.path.join(work, "shims")
atlas = os.path.join(work, "atlas")
state = os.path.join(work, "state")
upkeep_state = os.path.join(work, "upkeep")
CALLS = os.path.join(work, "calls.log")
SETUP_DIR = os.path.join(home, ".local", "state", "atlas-setup")
HOOK_STATE = os.path.join(state, "atlas-upkeep.json")
PATH = os.pathsep.join([shims, "/opt/homebrew/bin", "/usr/local/bin",
                        os.path.join(home, ".local", "bin"),
                        "/usr/bin", "/bin", "/usr/sbin", "/sbin"])
ENV = dict(os.environ, HOME=home, PATH=PATH,
           XDG_CONFIG_HOME=os.path.join(home, ".config"),
           XDG_STATE_HOME=os.path.join(home, ".local", "state"),
           BOARD_STATE_DIR=state, UPKEEP_STATE_DIR=upkeep_state, HOOK_CALLS=CALLS)
for k in ("TUTORBOARD_COURSES", "TUTORBOARD_SESSION", "TUTORBOARD_TURN", "PYTHONPATH",
          "UPKEEP_DRY_RUN"):
    ENV.pop(k, None)

EXE = stat.S_IRWXU
LOG = 'echo "$(basename "$0") $* @ $PWD" >>"$HOOK_CALLS"\n'
for tool in ("brew", "launchctl", "tailscale"):
    write(os.path.join(shims, tool), "#!/bin/bash\n" + LOG + "exit 0\n", EXE)
# uv and mise fail when a file in the work dir says so.
for tool in ("uv", "mise"):
    write(os.path.join(shims, tool), "#!/bin/bash\n" + LOG +
          '[ -f "%s/fail-%s" ] && { echo "%s broke" >&2; exit 4; }\n'
          'case "$*" in "outdated --json --bump --local") echo "{}" ;;\n'
          '  "ls --no-global --json") cat "%s/mise-ls.json" 2>/dev/null ;; esac\nexit 0\n'
          % (work, tool, tool, work), EXE)
for tool in ("brew", "launchctl", "tailscale", "uv", "mise"):
    where = shutil.which(tool, path=PATH)
    if where != os.path.join(shims, tool):
        print("REFUSED: %s resolves to %s, not the shim; nothing was run" % (tool, where))
        shutil.rmtree(work, ignore_errors=True)
        sys.exit(1)


def calls(start=""):
    return [l for l in read(CALLS).splitlines() if l.startswith(start)]


def hook(*args, env=None):
    e = dict(ENV)
    e.update(env or {})
    p = subprocess.run(["/usr/bin/python3", os.path.join(atlas, "scripts", "brew-upgrade.py")]
                       + list(args), env=e, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=300, cwd=atlas)
    return p.returncode, p.stdout, p.stderr


def hook_state():
    try:
        return json.loads(read(HOOK_STATE))
    except ValueError:
        return {}


def git(where, *args):
    """git in `where` under the fixture's HOME; raises on failure."""
    return subprocess.run(["git", "-C", where, "-c", "user.name=fixture",
                           "-c", "user.email=fixture@example.com"] + list(args),
                          env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=60, check=True).stdout


def hook_log():
    return read(os.path.join(SETUP_DIR, "upkeep-hook.log"))


# Locks in mise's own shape: an array table per tool, platform sub-tables.
ROOT_LOCK = ('[[tools.python]]\nversion = "3.13.5"\nbackend = "core:python"\n\n'
             '[tools.python.platforms.macos-arm64]\nurl = "https://example.invalid/py"\n')
S_TOML = '[tools]\nnode = "22"\n"npm:prettier" = "3"\n'
S_LOCK = ('[[tools.node]]\nversion = "22.11.0"\nbackend = "core:node"\n\n'
          '[tools.node.platforms.macos-arm64]\nurl = "https://example.invalid/node"\n\n'
          '[[tools."npm:prettier"]]\nversion = "3.3.3"\nbackend = "npm:prettier"\n')


try:
    # The fixture Atlas, a git repository with its locks committed.
    for rel in ("scripts/brew-upgrade.py", "scripts/tools.sh", "upkeep.d/hook"):
        write(os.path.join(atlas, rel), read(os.path.join(ATLAS_REAL, rel)), EXE)
    os.symlink(BOARD, os.path.join(atlas, "board"))
    write(os.path.join(atlas, "Brewfile"), 'brew "texlive"\ncask "font-dejavu"\n')
    write(os.path.join(atlas, "mise.toml"), '[tools]\npython = "3.13"\n')
    write(os.path.join(atlas, "mise.lock"), ROOT_LOCK)
    S = os.path.join(atlas, "projects", "S")
    write(os.path.join(S, "Brewfile"), 'brew "go"\nbrew "texlive"  # again\n')
    write(os.path.join(S, "pyproject.toml"),
          '[project]\nname = "s"\n[project.optional-dependencies]\ntest = ["pytest"]\n')
    write(os.path.join(S, ".venv", "bin", "python"), "#!/bin/sh\nexit 1\n", EXE)
    write(os.path.join(S, "mise.toml"), S_TOML)
    write(os.path.join(S, "mise.lock"), S_LOCK)
    git(atlas, "init", "-q")
    git(atlas, "add", "-A")
    git(atlas, "commit", "-qm", "fixture")
    ROLE = os.path.join(home, ".config", "tutor-board", "role")
    write(ROLE, "coding\n")

    # ===================================================================
    # protected-casks
    # ===================================================================
    code, out, err = hook("hook", "protected-casks")
    check("a coding laptop protects nothing", code == 0 and out == "", (out, err))
    os.remove(ROLE)
    code, out, err = hook("hook", "protected-casks")
    check("nor a host whose tailscale is no brew service", code == 0 and out == "", out)
    svc = os.path.join(home, "Library", "LaunchAgents", "homebrew.mxcl.tailscale.plist")
    write(svc, "<plist/>\n")
    code, out, err = hook("hook", "protected-casks")
    check("a host's tailscale brew service is protected", out == "tailscale\n", out)
    os.remove(svc)
    write(ROLE, "coding\n")

    # ===================================================================
    # brewfiles
    # ===================================================================
    code, out, err = hook("hook", "brewfiles")
    union = os.path.join(SETUP_DIR, "Brewfile.all")
    text = read(union)
    check("brewfiles prints the union's path",
          code == 0 and out == union + "\n", (out, err))
    check("the union joins the root Brewfile and the subject's, once each",
          text.count('brew "texlive"') == 1 and 'brew "go"' in text
          and 'cask "font-dejavu"' in text, text)
    p = subprocess.run([os.path.join(atlas, "upkeep.d", "hook"), "brewfiles"], env=ENV,
                       stdout=subprocess.PIPE, universal_newlines=True, timeout=120)
    check("upkeep.d/hook reaches the same answer", p.stdout == union + "\n", p.stdout)

    # ===================================================================
    # after-brew
    # ===================================================================
    open(CALLS, "w").close()
    code, out, err = hook("hook", "after-brew")
    check("after-brew re-syncs the broken .venv with its test extra",
          code == 0 and "uv sync --locked --extra test @ %s" % S in calls("uv"),
          (read(CALLS), err))
    check("and, repaired, records no problem", hook_state().get("problems") == [],
          hook_state())
    write(os.path.join(work, "fail-uv"), "")
    hook("hook", "after-brew")
    probs = hook_state().get("problems") or []
    check("a .venv uv cannot fix is a problem, with its fix",
          [p["what"] for p in probs] == ["projects/S's .venv does not start"]
          and probs[0]["fix"] == "cd projects/S && uv sync --locked --extra test", probs)
    os.remove(os.path.join(work, "fail-uv"))

    # ===================================================================
    # toolchain
    # ===================================================================
    write(os.path.join(home, ".local", "share", "uv", "python", "cpython-3.13.5", "x"), "")
    open(CALLS, "w").close()
    check("the fixture is a clean checkout before toolchain",
          git(atlas, "status", "--porcelain") == "", git(atlas, "status", "--porcelain"))
    code, out, err = hook("hook", "toolchain")
    check("toolchain upgrades uv's Pythons", calls("uv python upgrade"), read(CALLS))
    check("installs each mise directory's own tools, locked, there",
          "mise install --locked node npm:prettier @ %s" % S in calls("mise"), read(CALLS))
    check("installs Atlas's own root mise pins too",
          "mise install --locked python @ %s" % atlas in calls("mise"), read(CALLS))
    check("prunes only the pinned tools",
          any(l.startswith("mise prune --yes --tools node npm:prettier ")
              for l in calls("mise")), read(CALLS))
    check("a clean checkout whose locks cover their tomls is not re-locked",
          not calls("mise lock"), read(CALLS))
    st = hook_state()
    check("and, with nothing failed, stamps its success",
          st.get("failed") == {} and st.get("toolchain_success"), st)

    # A fresh clone: git may write each lock before its toml, so the lock is
    # older by mtime, yet it matches HEAD and covers its toml.
    clone = os.path.join(work, "clone")
    subprocess.run(["git", "clone", "-q", atlas, clone], env=ENV, check=True, timeout=60)
    CS = os.path.join(clone, "projects", "S")
    for d in (clone, CS):
        os.utime(os.path.join(d, "mise.lock"), (1000.0, 1000.0))
        os.utime(os.path.join(d, "mise.toml"), (2000.0, 2000.0))
    open(CALLS, "w").close()
    p = subprocess.run(["/usr/bin/python3", os.path.join(clone, "scripts", "brew-upgrade.py"),
                        "hook", "toolchain"], env=ENV, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True, timeout=300, cwd=clone)
    check("a fresh clone whose locks are older by mtime is not re-locked, and installs",
          p.returncode == 0 and not calls("mise lock")
          and "mise install --locked node npm:prettier @ %s" % CS in calls("mise")
          and "mise install --locked python @ %s" % clone in calls("mise"),
          (read(CALLS), p.stderr))
    check("and the clone stays clean", git(clone, "status", "--porcelain") == "",
          git(clone, "status", "--porcelain"))

    # A mise.toml edited since HEAD is re-locked first, whatever the mtimes;
    # a failure there is a problem, not a silent success.
    write(os.path.join(S, "mise.toml"), S_TOML.replace('"22"', '"24"'))
    os.utime(os.path.join(S, "mise.toml"), (1000.0, 1000.0))
    write(os.path.join(work, "fail-mise"), "")
    open(CALLS, "w").close()
    before_success = hook_state().get("toolchain_success")
    hook("hook", "toolchain")
    st = hook_state()
    check("a mise.toml changed from HEAD is re-locked, even with an older mtime, "
          "and a lock failure is tool:mise-lock",
          "mise lock @ %s" % S in calls("mise")
          and "mise lock @ %s" % atlas not in calls("mise")
          and "mise lock in projects/S: mise.toml differs from HEAD" in hook_log()
          and st["failed"].get("tool:mise-lock") == "mise broke"
          and st.get("toolchain_success") == before_success, (read(CALLS), st))
    os.remove(os.path.join(work, "fail-mise"))
    git(atlas, "checkout", "--", "projects/S/mise.toml")

    # A committed toml whose committed lock lacks one of its tools (a
    # declaration whose own `mise lock` failed) is re-locked.
    write(os.path.join(S, "mise.toml"), S_TOML + 'go = "1.23"\n')
    git(atlas, "commit", "-qam", "pin go, lock not refreshed")
    open(CALLS, "w").close()
    hook("hook", "toolchain")
    check("a committed toml with a tool its lock has no entry for is re-locked",
          "mise lock @ %s" % S in calls("mise")
          and "mise lock in projects/S: mise.lock has no entry for go" in hook_log(),
          (read(CALLS), hook_log()[-600:]))
    git(atlas, "reset", "-q", "--hard", "HEAD~1")

    # A missing lock is locked.
    os.remove(os.path.join(S, "mise.lock"))
    open(CALLS, "w").close()
    hook("hook", "toolchain")
    check("a missing mise.lock is locked",
          "mise lock @ %s" % S in calls("mise")
          and "mise lock in projects/S: mise.lock is missing" in hook_log(), read(CALLS))
    git(atlas, "checkout", "--", "projects/S/mise.lock")

    # A mise.lock edited since HEAD, its toml unchanged, is re-locked: the
    # lock may no longer satisfy the toml.
    write(os.path.join(S, "mise.lock"), S_LOCK.replace("22.11.0", "20.0.0"))
    open(CALLS, "w").close()
    hook("hook", "toolchain")
    check("a mise.lock changed from HEAD is re-locked; the clean root is not",
          "mise lock @ %s" % S in calls("mise")
          and "mise lock @ %s" % atlas not in calls("mise")
          and "mise lock in projects/S: mise.lock differs from HEAD" in hook_log(),
          (read(CALLS), hook_log()[-600:]))
    git(atlas, "checkout", "--", "projects/S/mise.lock")

    # A subject git holds neither file of: git never wrote them, so mtimes
    # decide.
    U = os.path.join(atlas, "projects", "U")
    write(os.path.join(U, "mise.toml"), '[tools]\nzig = "0.13"\n')
    write(os.path.join(U, "mise.lock"), '[[tools.zig]]\nversion = "0.13.0"\n')
    os.utime(os.path.join(U, "mise.lock"), (1000.0, 1000.0))
    os.utime(os.path.join(U, "mise.toml"), (2000.0, 2000.0))
    open(CALLS, "w").close()
    hook("hook", "toolchain")
    check("an untracked mise.toml newer than its lock is re-locked; the clean one beside "
          "it is not",
          "mise lock @ %s" % U in calls("mise") and "mise lock @ %s" % S not in calls("mise")
          and "mise lock in projects/U: mise.toml is newer than mise.lock, and git holds "
          "neither" in hook_log(), (read(CALLS), hook_log()[-600:]))
    os.utime(os.path.join(U, "mise.lock"), (3000.0, 3000.0))
    open(CALLS, "w").close()
    hook("hook", "toolchain")
    check("an untracked lock newer than its toml is not re-locked, and installs",
          not calls("mise lock") and "mise install --locked zig @ %s" % U in calls("mise"),
          read(CALLS))
    shutil.rmtree(U)

    # The lock reader and the staleness decision, called directly. No
    # bytecode, so loading the script leaves the fixture clean.
    import importlib.util                                    # noqa: E402
    sys.dont_write_bytecode = True
    os.environ.update(ENV)          # the shims, never the real mise
    spec = importlib.util.spec_from_file_location(
        "brew_upgrade_under_test", os.path.join(atlas, "scripts", "brew-upgrade.py"))
    bu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bu)
    check("locked_names reads array tables, quoted backends, sub-tables and a [tools] table",
          bu.locked_names(S_LOCK + "[tools]\nruby = \"3\"\n# lua = \"5\"\n")
          == {"node", "npm:prettier", "ruby"},
          bu.locked_names(S_LOCK))
    check("and finds no tool in a lock that names none",
          bu.locked_names("# empty\n[settings]\nx = 1\n") == set())
    SN = ["node", "npm:prettier"]
    check("lock_stale: clean is \"\", a dropped entry names the tool",
          bu.lock_stale(S, SN) == ""
          and bu.lock_stale(S, SN + ["go"]) == "mise.lock has no entry for go",
          (bu.lock_stale(S, SN), bu.lock_stale(S, SN + ["go"])))
    with open(os.path.join(S, "mise.lock"), "a", encoding="utf-8") as fh:
        fh.write("# a hand edit\n")
    check("lock_stale: an uncommitted edit to the lock alone is stale",
          bu.lock_stale(S, SN) == "mise.lock differs from HEAD", bu.lock_stale(S, SN))
    git(atlas, "checkout", "--", "projects/S/mise.lock")

    # A tracked mise.toml that is a symlink: git holds its target, and so
    # does the comparison.
    L = os.path.join(work, "linked")
    write(os.path.join(L, "real.toml"), S_TOML)
    write(os.path.join(L, "other.toml"), S_TOML.replace('"22"', '"24"'))
    os.symlink("real.toml", os.path.join(L, "mise.toml"))
    write(os.path.join(L, "mise.lock"), S_LOCK)
    git(L, "init", "-q")
    git(L, "add", "-A")
    git(L, "commit", "-qm", "linked")
    os.utime(os.path.join(L, "mise.lock"), (1000.0, 1000.0))
    stale_clean = bu.lock_stale(L, SN)
    os.remove(os.path.join(L, "mise.toml"))
    os.symlink("other.toml", os.path.join(L, "mise.toml"))
    stale_moved = bu.lock_stale(L, SN)
    check("lock_stale: a clean symlinked mise.toml is fresh; one pointed elsewhere is stale",
          stale_clean == "" and stale_moved == "mise.toml differs from HEAD",
          (stale_clean, stale_moved))

    # mise locks a tool under its own name: `nodejs` in a toml is
    # `[[tools.node]]` in the lock. `mise ls` (the shim answers from
    # mise-ls.json) gives that name; only its pins from this toml count.
    A = os.path.join(work, "aliased")
    write(os.path.join(A, "mise.toml"), '[tools]\nnodejs = "22"\ngolang = "1.23"\n')
    write(os.path.join(A, "mise.lock"), '[[tools.node]]\nversion = "22.11.0"\n\n'
          '[[tools.go]]\nversion = "1.23.12"\n')
    git(A, "init", "-q")
    git(A, "add", "-A")
    git(A, "commit", "-qm", "aliased")
    os.utime(os.path.join(A, "mise.lock"), (1000.0, 1000.0))

    def mise_ls(where, names, other=()):
        src = {"type": "mise.toml", "path": os.path.join(where, "mise.toml")}
        doc = dict((n, [{"version": "1", "source": src}]) for n in names)
        doc.update((n, [{"version": "1", "source": {"type": "mise.toml",
                                                    "path": os.path.join(work, "x.toml")}}])
                   for n in other)
        write(os.path.join(work, "mise-ls.json"), json.dumps(doc))
    AN = ["golang", "nodejs"]
    mise_ls(A, ["go", "node"], other=["python"])
    got = bu.lock_stale(A, AN)
    check("lock_stale: a clean clone pinning aliases its lock holds under mise's names "
          "is fresh; another config's tools do not count", got == "", got)
    mise_ls(A, ["go", "node", "zig"])
    got = bu.lock_stale(A, AN)
    check("and a tool mise names that the lock lacks is stale",
          got == "mise.lock has no entry for zig", got)
    os.remove(os.path.join(work, "mise-ls.json"))
    got = bu.lock_stale(A, AN)
    check("and when mise cannot answer, the toml's own names stand",
          got == "mise.lock has no entry for golang, nodejs", got)

    # A checkout's eol and ident conversions make its files differ from the
    # raw blobs at HEAD; git calls them clean, and so does lock_stale.
    for label, attrs, opts in (("eol=crlf", "mise.* text eol=crlf\n", []),
                               ("core.autocrlf", "", ["--config", "core.autocrlf=true"]),
                               ("ident", "mise.toml ident\n", [])):
        R = os.path.join(work, "filtered-" + label.replace("=", "-").replace(".", "-"))
        C = R + "-clone"
        write(os.path.join(R, "mise.toml"), "# $Id$\n" + S_TOML)
        write(os.path.join(R, "mise.lock"), S_LOCK)
        if attrs:
            write(os.path.join(R, ".gitattributes"), attrs)
        git(R, "init", "-q")
        git(R, "add", "-A")
        git(R, "commit", "-qm", label)
        subprocess.run(["git", "clone", "-q"] + opts + [R, C], env=ENV, check=True,
                       timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.utime(os.path.join(C, "mise.lock"), (1000.0, 1000.0))
        os.utime(os.path.join(C, "mise.toml"), (2000.0, 2000.0))
        with open(os.path.join(C, "mise.toml"), "rb") as fh:
            raw = fh.read() != subprocess.run(
                ["git", "-C", C, "show", "HEAD:mise.toml"], env=ENV, check=True,
                stdout=subprocess.PIPE, timeout=60).stdout
        clean = git(C, "status", "--porcelain") == ""
        fresh = bu.lock_stale(C, SN)
        with open(os.path.join(C, "mise.toml"), "a", encoding="utf-8") as fh:
            fh.write('go = "1.23"\n')
        edited = bu.lock_stale(C, SN)
        check("lock_stale: a clean %s clone is fresh; an edit there is stale" % label,
              raw and clean and fresh == "" and edited == "mise.toml differs from HEAD",
              (raw, clean, fresh, edited))

    # Where git cannot answer (no repository, no commit, no git), mtimes
    # decide, both ways.
    def by_mtime(where, toml_t, lock_t):
        os.utime(os.path.join(where, "mise.toml"), (toml_t, toml_t))
        os.utime(os.path.join(where, "mise.lock"), (lock_t, lock_t))
        return bu.lock_stale(where, SN)
    NEWER = "mise.toml is newer than mise.lock, and git holds neither"
    N = os.path.join(work, "norepo")
    write(os.path.join(N, "mise.toml"), S_TOML)
    write(os.path.join(N, "mise.lock"), S_LOCK)
    got = (by_mtime(N, 1000.0, 2000.0), by_mtime(N, 2000.0, 1000.0))
    check("lock_stale outside any repository: an older toml is fresh, a newer one stale",
          got == ("", NEWER), got)
    git(N, "init", "-q")
    got = (by_mtime(N, 1000.0, 2000.0), by_mtime(N, 2000.0, 1000.0))
    check("and in a repository with no commit yet, the same", got == ("", NEWER), got)
    saved = os.environ.get("PATH", "")
    os.environ["PATH"] = os.path.join(work, "empty-path")
    try:
        got = (by_mtime(S, 1000.0, 2000.0), by_mtime(S, 2000.0, 1000.0))
    finally:
        os.environ["PATH"] = saved
    os.utime(os.path.join(S, "mise.toml"), None)
    os.utime(os.path.join(S, "mise.lock"), None)
    check("and with no git on PATH, the same", got == ("", NEWER), got)
    check("the fixture is clean again", git(atlas, "status", "--porcelain") == "",
          git(atlas, "status", "--porcelain"))
    open(CALLS, "w").close()
    write(os.path.join(work, "fail-mise"), "")
    hook("hook", "toolchain")
    st = hook_state()
    check("a failed mise install is tool:mise:<subject>, and no success is stamped",
          st["failed"].get("tool:mise:projects/S") == "mise broke"
          and st["failed"].get("tool:mise-prune") == "mise broke"
          and st.get("toolchain_attempt") >= st.get("toolchain_success"), st)
    os.remove(os.path.join(work, "fail-mise"))
    open(CALLS, "w").close()
    before = read(HOOK_STATE)
    code, out, err = hook("hook", "toolchain", env={"UPKEEP_DRY_RUN": "1"})
    check("a dry run mutates nothing and writes no state",
          not calls("uv python") and not [l for l in calls("mise") if "install" in l
                                          or "prune" in l]
          and read(HOOK_STATE) == before and "would run" in err, (read(CALLS), err))

    # ===================================================================
    # status
    # ===================================================================
    code, out, err = hook("hook", "status")
    check("status prints each failed tool and exits 0",
          code == 0 and "mise:projects/S did not update: mise broke" in out, (out, err))
    write(os.path.join(state, "tools.json"), json.dumps({
        "tools": {"widget": {"failed": "T_UPDATE exited 3"}},
        "pins": [{"subject": "projects/S", "tool": "node", "pinned": "20", "latest": "22"}]}))
    code, out, err = hook("hook", "status")
    check("and tools.json's lines, but never a pin behind",
          "widget failed: T_UPDATE exited 3" in out and "pin behind" not in out, out)
    os.remove(ROLE)
    write(os.path.join(home, "Library", "LaunchAgents", "tutor-board.plist"),
          "<?xml version=\"1.0\"?><plist version=\"1.0\"><dict><key>ProgramArguments"
          "</key><array><string>/gone/python3</string></array></dict></plist>\n")
    open(CALLS, "w").close()
    code, out, err = hook("hook", "status")
    check("on the host, a gone board interpreter and an unserved board are named, "
          "report only",
          "the tutor-board LaunchAgent's python /gone/python3 is gone; bash board/install.sh"
          in out and "tailscale does not serve the board" in out
          and not calls("bash") and calls("tailscale serve status"), (out, read(CALLS)))
    write(ROLE, "coding\n")

    # ===================================================================
    # atlas-brew status, install, usage
    # ===================================================================
    write(os.path.join(upkeep_state, "state.json"), json.dumps({
        "last_attempt": "2099-11-01T03:30:00", "last_success": "2099-11-01T03:40:00",
        "last_result": "ok", "failed": {}, "held": {}, "problems": ["Xcode needs its "
                                                                     "first launch"]}))
    code, out, err = hook("status")
    check("atlas-brew status shows upkeep's run and the hook's lines, exit 1",
          code == 1 and "upkeep:   ok Nov 1 03:30; 0 held, 0 failed, 1 problems" in out
          and "upkeep: Xcode needs its first launch" in out
          and "tools: mise:projects/S did not update: mise broke" in out, out)
    write(HOOK_STATE, json.dumps({"failed": {}, "problems": [],
                                  "toolchain_success": "2099-11-01T03:50:00"}))
    os.remove(os.path.join(state, "tools.json"))
    write(os.path.join(upkeep_state, "state.json"), json.dumps({
        "last_attempt": "2099-11-01T03:30:00", "last_success": "2099-11-01T03:40:00",
        "last_result": "ok"}))
    code, out, err = hook("status")
    check("and exit 0 when all is well", code == 0 and "Atlas toolchain Nov 1 03:50" in out,
          out)
    old = os.path.join(home, "Library", "LaunchAgents", "atlas.brew-upgrade.plist")
    write(old, "<plist/>\n")
    open(CALLS, "w").close()
    code, out, err = hook("install")
    link = os.path.join(home, ".local", "bin", "atlas-brew")
    check("install links atlas-brew and retires atlas.brew-upgrade",
          code == 0 and os.path.realpath(link) == os.path.join(atlas, "scripts",
                                                               "brew-upgrade.py")
          and not os.path.exists(old)
          and any(l.startswith("launchctl bootout gui/") and "atlas.brew-upgrade" in l
                  for l in calls("launchctl")), (out, read(CALLS)))
    check("usage: a wrong command is exit 2, a phase it does not know is a quiet 0",
          hook("nope")[0] == 2 and hook("hook", "a-new-phase") == (0, "", ""))

    # ===================================================================
    # brewcare, and upkeep's phases
    # ===================================================================
    from tutorboard import brewcare                          # noqa: E402
    N = datetime(2026, 11, 5, 9, 0)
    up = os.path.join(work, "up2")
    write(os.path.join(up, "state.json"), json.dumps({
        "last_attempt": "2026-11-01T03:30:00", "last_success": "2026-11-01T03:31:00",
        "last_result": "partial", "failed": {"cask slack": "Error: x"},
        "held": {"node": {"installed": "24.1", "latest": "24.2", "why": "pinned"}},
        "problems": ["flutter doctor: [!] Xcode"], "brew_by": "com.mikeyferguson.brewupgrade",
        "hooks": {atlas: ["not shown twice"]}}))
    s2 = os.path.join(work, "s2")
    write(os.path.join(s2, "atlas-upkeep.json"), json.dumps({
        "failed": {"tool:uv-python": "no"},
        "problems": [{"what": "TeX is missing preview.sty", "fix": "tlmgr install preview"}]}))
    said = brewcare.lines(s2, N, upkeep=up)
    check("brewcare: upkeep's failures, holds, problems and staleness, then the hook's",
          said == ["upkeep: cask slack failed: Error: x",
                   "upkeep: node 24.1 -> 24.2 is held: pinned",
                   "upkeep: flutter doctor: [!] Xcode",
                   "upkeep: no successful run since Nov 1 03:31",
                   "tools: uv-python did not update: no",
                   "atlas: TeX is missing preview.sty; tlmgr install preview"], said)
    check("brewcare.summary: upkeep's run, who did brew, and the hook's",
          brewcare.summary(s2, upkeep=up)
          == "partial Nov 1 03:30; 1 held, 1 failed, 1 problems; brew left to "
             "com.mikeyferguson.brewupgrade; Atlas toolchain never, 1 failed, 1 problems",
          brewcare.summary(s2, upkeep=up))
    check("and with neither, says how to start",
          brewcare.summary(os.path.join(work, "none"), upkeep=os.path.join(work, "none"))
          == "no upkeep run yet (bash upkeep/setup-mac.sh); no Atlas hook run yet")
    upkeep_py = read(os.path.join(ATLAS_REAL, "upkeep", "upkeep.py"))
    asked = set(re.findall(r'hook(?:_lists)?\((?:root, )?"([a-z-]+)"', upkeep_py))
    loop = re.search(r'for ph in \(([^)]*)\)', upkeep_py)
    if loop:
        asked |= set(loop.group(1).replace('"', "").replace(" ", "").split(","))
    asked.discard("")
    known = set(re.search(r'PHASES = \(([^)]*)\)', read(os.path.join(
        ATLAS_REAL, "scripts", "brew-upgrade.py"))).group(1).replace('"', "").replace(
            " ", "").split(","))
    check("upkeep asks only phases the hook knows",
          len(asked) == 5 and asked <= known, (asked, known))
finally:
    shutil.rmtree(work, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("Atlas's upkeep hook protects, joins, repairs, keeps the toolchain and reports")
