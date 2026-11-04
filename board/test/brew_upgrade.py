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
    failure is tool:<name>; a dry run mutates nothing.
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
          'case "$*" in "outdated --json --bump --local") echo "{}" ;; esac\nexit 0\n'
          % (work, tool, tool), EXE)
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


try:
    # The fixture Atlas.
    for rel in ("scripts/brew-upgrade.py", "scripts/tools.sh", "upkeep.d/hook"):
        write(os.path.join(atlas, rel), read(os.path.join(ATLAS_REAL, rel)), EXE)
    os.symlink(BOARD, os.path.join(atlas, "board"))
    write(os.path.join(atlas, "Brewfile"), 'brew "texlive"\ncask "font-dejavu"\n')
    write(os.path.join(atlas, "mise.toml"), '[tools]\npython = "3.13"\n')
    write(os.path.join(atlas, "mise.lock"), "root lock\n")
    S = os.path.join(atlas, "projects", "S")
    write(os.path.join(S, "Brewfile"), 'brew "go"\nbrew "texlive"  # again\n')
    write(os.path.join(S, "pyproject.toml"),
          '[project]\nname = "s"\n[project.optional-dependencies]\ntest = ["pytest"]\n')
    write(os.path.join(S, ".venv", "bin", "python"), "#!/bin/sh\nexit 1\n", EXE)
    write(os.path.join(S, "mise.toml"), '[tools]\nnode = "22"\n')
    write(os.path.join(S, "mise.lock"), "x\n")
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
    code, out, err = hook("hook", "toolchain")
    check("toolchain upgrades uv's Pythons", calls("uv python upgrade"), read(CALLS))
    check("installs each mise directory's own tools, locked, there",
          "mise install --locked node @ %s" % S in calls("mise"), read(CALLS))
    check("installs Atlas's own root mise pins too",
          "mise install --locked python @ %s" % atlas in calls("mise"), read(CALLS))
    check("prunes only the pinned tools", any(l.startswith("mise prune --yes --tools node ")
                                             for l in calls("mise")), read(CALLS))
    st = hook_state()
    check("and, with nothing failed, stamps its success",
          st.get("failed") == {} and st.get("toolchain_success"), st)
    # A lock older than its toml is refreshed first; a failure there is a
    # problem, not a silent success.
    write(os.path.join(work, "fail-mise"), "")
    old = 1000.0
    os.utime(os.path.join(S, "mise.lock"), (old, old))
    before_success = hook_state().get("toolchain_success")
    hook("hook", "toolchain")
    st = hook_state()
    check("a stale mise.lock is refreshed, and a lock failure is tool:mise-lock",
          "mise lock @ %s" % S in calls("mise")
          and st["failed"].get("tool:mise-lock") == "mise broke"
          and st.get("toolchain_success") == before_success, st)
    os.remove(os.path.join(work, "fail-mise"))
    os.utime(os.path.join(S, "mise.lock"), None)
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
