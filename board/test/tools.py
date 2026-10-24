#!/usr/bin/env python3
"""Tools on every machine: the Brewfile union, mise markers, descriptors.

    python3 test/tools.py

A fixture Atlas in a temp dir holds the real scripts/setup.sh and
scripts/tools.sh, with board/ a link to this one. HOME and the state
directories are temp dirs, and brew, mise, curl and uname are shims first on
the PATH that only log; the suite refuses to run when one resolves anywhere
else. Nothing is installed on this machine.

  - THE UNION: the root Brewfile and each subject's, comments dropped, taps
    first, sorted and deduplicated; Brewfile.all rewritten only on change; an
    entry that leaves it is remembered while it is still installed.
  - SETUP TWICE: a subject with a mise.toml, a Cargo.toml one directory down,
    a pubspec.yaml and a warden/build.zig.zon builds through mise; zig fetches
    only under a zig pin. A second run is clean and changes
    nothing, as a host and as a coding laptop. Off a Mac it refuses. A deleted subject's Brewfile lines and descriptors
    leave the plan, nothing is uninstalled, and brewcare names what is left
    behind.
  - DESCRIPTORS: tools.sh install, update, list, path and check; the role;
    T_EVERY_DAYS; a failing update or check, and its recovery; a tool with no
    installer, and one with no T_UPDATE, which only goes stale; a name never
    seen before; one name in two subjects, identical or not; tools.json.
  - REPORTING: brewcare's tools lines (failed, stale, conflict, no longer
    declared, pin behind) and the doctor's summary; `mise outdated` parsed;
    the tools a mise.toml pins, which alone are pruned.
  - PATHS: the tutor-board plist's PATH (board/install.sh's AGENT_PATH) ends
    in mise's shims, and its python is not a planted shim; the real tree declares no
    conflicting descriptor.
"""

import glob
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timedelta

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


work = os.path.realpath(tempfile.mkdtemp(prefix="atlas-tools-"))
home = os.path.join(work, "home")
shims = os.path.join(work, "shims")
atlas = os.path.join(work, "atlas")
state = os.path.join(work, "state")
CALLS = os.path.join(work, "calls.log")
prefix = os.path.join(work, "prefix")
SETUP_DIR = os.path.join(home, ".local", "state", "atlas-setup")
TOOLS_JSON = os.path.join(state, "tools.json")
# setup.sh puts these in front only when they are missing, so they follow the shims.
PATH = os.pathsep.join([shims, "/opt/homebrew/bin", "/usr/local/bin",
                        os.path.join(home, ".local", "bin"),
                        os.path.join(home, ".local", "go", "bin"),
                        os.path.join(home, ".elan", "bin"),
                        "/usr/bin", "/bin", "/usr/sbin", "/sbin"])
ENV = dict(os.environ, HOME=home, PATH=PATH,
           XDG_CONFIG_HOME=os.path.join(home, ".config"),
           XDG_STATE_HOME=os.path.join(home, ".local", "state"),
           BOARD_STATE_DIR=state, TOOLS_CALLS=CALLS)
for k in ("TUTORBOARD_COURSES", "TUTORBOARD_SESSION", "TUTORBOARD_TURN", "PYTHONPATH"):
    ENV.pop(k, None)
os.environ.update({"BOARD_STATE_DIR": state, "HOME": home,
                   "XDG_STATE_HOME": ENV["XDG_STATE_HOME"]})

EXE = stat.S_IRWXU
LOG = 'echo "$(basename "$0") $* @ $PWD" >>"$TOOLS_CALLS"\n'
for tool in ("brew", "mise", "curl", "uv", "go", "elan", "lake"):
    write(os.path.join(shims, tool), "#!/bin/bash\n" + LOG + "exit 0\n", EXE)
write(os.path.join(shims, "uname"), "#!/bin/bash\necho Darwin\n", EXE)
for tool in ("brew", "mise", "curl", "uname"):
    where = shutil.which(tool, path=PATH)
    if where != os.path.join(shims, tool):
        print("REFUSED: %s resolves to %s, not the shim; nothing was run" % (tool, where))
        shutil.rmtree(work, ignore_errors=True)
        sys.exit(1)

from tutorboard import brewcare, toolplan                    # noqa: E402


def run(argv, cwd=None):
    p = subprocess.run(argv, cwd=cwd or work, env=ENV, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True, timeout=300)
    return p.returncode, p.stdout


def calls(start=""):
    return [l for l in read(CALLS).splitlines() if l.startswith(start)]


def tools_json():
    try:
        return json.loads(read(TOOLS_JSON))
    except ValueError:
        return {}


def descriptor(name, install=True, update="true", check_cmd=None, roles="host coding",
               every=1, stale=14, version_cmd=None, extra=""):
    """A descriptor whose tool is a script under $HOME/.<name>/bin printing
    `<name> <version>`, the version kept in $HOME/.<name>/version."""
    bindir = "$HOME/.%s/bin" % name
    inst = ('mkdir -p "%s" && printf "#!/bin/sh\\necho %s \\$(cat \\"\\$HOME/.%s/version\\" '
            '2>/dev/null || echo 1.0.0)\\n" >"%s/%s" && chmod +x "%s/%s" && echo x >>'
            '"$HOME/%s.installs"' % (bindir, name, name, bindir, name, bindir, name, name))
    return ("# a fixture tool\n"
            'T_NAME="%s"\nT_BIN="%s"\nT_BIN_DIR="%s"\nT_ROLES="%s"\n'
            "T_INSTALL='%s'\nT_MANUAL='fetch %s by hand'\nT_UPDATE='%s'\n"
            "T_VERSION='%s'\nT_CHECK='%s'\nT_EVERY_DAYS=%d\nT_STALE_DAYS=%d\n%s"
            % (name, name, bindir, roles, inst if install else "", name, update,
               version_cmd or "%s --version" % name, check_cmd or "%s" % name,
               every, stale, extra))


TOOLS_SH = os.path.join(atlas, "scripts", "tools.sh")


def tools(*args):
    return run(["bash", TOOLS_SH] + list(args))


try:
    # --- the fixture Atlas ------------------------------------------------
    os.makedirs(os.path.join(atlas, "scripts"))
    for rel in ("scripts/setup.sh", "scripts/tools.sh"):
        shutil.copy(os.path.join(ATLAS_REAL, rel), os.path.join(atlas, rel))
    os.symlink(BOARD, os.path.join(atlas, "board"))
    os.makedirs(os.path.join(atlas, "ai-config", ".git"))
    write(os.path.join(atlas, "Brewfile"),
          '# the root\nbrew "uv"            # every uv.lock\nbrew "mise"\n'
          'cask "font-x"   # a "quoted" # comment\n')
    M = os.path.join(atlas, "projects", "M")
    write(os.path.join(M, "tutorboard.json"), json.dumps({"check": "cargo test"}))
    write(os.path.join(M, "mise.toml"),
          '[tools]\nrust = "1.80.0"\nflutter = "3.24.0"\nzig = "0.17.0"\n')
    write(os.path.join(M, "mise.lock"), "locked\n")
    write(os.path.join(M, "app", "Cargo.toml"), "[package]\nname = \"app\"\n")
    write(os.path.join(M, "app", "Cargo.lock"), "locked\n")
    write(os.path.join(M, "app", "target", "Cargo.toml"), "not a marker\n")
    write(os.path.join(M, "ui", "pubspec.yaml"), "name: ui\n")
    write(os.path.join(M, "ui", "pubspec.lock"), "locked\n")
    write(os.path.join(M, "warden", "build.zig.zon"), ".{ .name = .warden }\n")
    for out in ("zig-out", ".zig-cache", "zig-pkg"):
        write(os.path.join(M, out, "build.zig.zon"), "not a marker\n")
    write(os.path.join(M, "Brewfile"),
          'brew "uv"  # also the root\nbrew "ripgrep"\ntap "acme/tools"\n'
          'brew "acme/tools/widget-cli"\n')
    write(os.path.join(M, "tools", "widget.sh"), descriptor("widget"))
    # A build.zig.zon under a mise.toml that pins no zig is never fetched.
    Z = os.path.join(atlas, "projects", "Z")
    write(os.path.join(Z, "tutorboard.json"), json.dumps({"check": "zig build test"}))
    write(os.path.join(Z, "mise.toml"), '[tools]\nrust = "1.80.0"\n')
    write(os.path.join(Z, "mise.lock"), "locked\n")
    write(os.path.join(Z, "warden", "build.zig.zon"), ".{ .name = .warden }\n")
    write(os.path.join(atlas, "courses", "C", "notes.md"), "no code\n")

    # =======================================================================
    # the union
    # =======================================================================
    got, labels = toolplan.union(atlas)
    check("the union: the root and each subject's Brewfile, comments dropped, taps "
          "first, sorted, each entry once",
          got == ['tap "acme/tools"', 'brew "acme/tools/widget-cli"', 'brew "mise"',
                  'brew "ripgrep"', 'brew "uv"', 'cask "font-x"']
          and labels == ["Brewfile", "projects/M/Brewfile"], (got, labels))

    # =======================================================================
    # setup.sh, twice
    # =======================================================================
    setup = os.path.join(atlas, "scripts", "setup.sh")
    code1, out1 = run(["bash", setup])
    first_calls = read(CALLS)
    union = os.path.join(SETUP_DIR, "Brewfile.all")
    check("setup ends clean", code1 == 0 and "FAILED" not in out1, out1)
    check("it bundles the union with --no-upgrade, never --cleanup",
          calls("brew bundle install --no-upgrade --file=%s " % union)
          and not [l for l in calls("brew") if "cleanup" in l or "uninstall" in l]
          and 'brew "ripgrep"' in read(union) and 'brew "uv"' in read(union)
          and "Brewfile.all rewritten" in out1, (calls("brew"), out1))
    check("a subject with a mise.toml builds: mise trust and install --locked at its "
          "root, cargo fetch, flutter pub get and zig build --fetch one directory "
          "down, through mise",
          calls("mise trust --quiet %s/mise.toml @ " % M)
          and calls("mise install --locked flutter rust zig @ %s" % M)
          and calls("mise exec -- cargo fetch --locked @ %s" % os.path.join(M, "app"))
          and calls("mise exec -- flutter pub get --enforce-lockfile @ %s"
                    % os.path.join(M, "ui"))
          and calls("mise exec -- zig build --fetch @ %s" % os.path.join(M, "warden"))
          and not [l for l in calls("mise") if "target" in l or "zig-" in l]
          and "ok (mise install, cargo fetch, flutter pub get, zig build --fetch)" in out1,
          (calls(), out1))
    check("a build.zig.zon whose mise.toml pins no zig is not fetched, and setup says so",
          not calls("mise exec -- zig build --fetch @ %s" % Z)
          and "ok (mise install, zig skipped (no zig pin))" in out1, (calls(), out1))
    widget = os.path.join(home, ".widget", "bin", "widget")
    check("and the descriptor's tool is installed",
          os.path.exists(widget) and read(os.path.join(home, "widget.installs")) == "x\n"
          and "1 tool(s) declared for a host, 0 problem(s)" in out1, out1)
    before = {p: (read(p), os.stat(p).st_mtime_ns) for p in (union, TOOLS_JSON)}
    open(CALLS, "w").close()
    code2, out2 = run(["bash", setup])
    check("a second run is clean", code2 == 0 and "FAILED" not in out2, out2)
    check("and changes nothing: Brewfile.all and tools.json untouched, nothing "
          "installed twice",
          "Brewfile.all unchanged" in out2
          and all((read(p), os.stat(p).st_mtime_ns) == before[p] for p in before)
          and read(os.path.join(home, "widget.installs")) == "x\n",
          (out2, read(TOOLS_JSON)))
    check("and asks the same of brew and mise",
          sorted(read(CALLS).splitlines()) == sorted(first_calls.splitlines()),
          (first_calls, read(CALLS)))
    check("setup's PATH ends in mise's shims", "mise/shims" in read(setup)
          and 'PATH="$PATH:$HOME/.local/share/mise/shims"' in read(setup))

    # The same, as a coding laptop: a coding-only tool goes in once.
    ROLE = os.path.join(home, ".config", "tutor-board", "role")
    write(ROLE, "coding\n")
    write(os.path.join(M, "tools", "coder.sh"), descriptor("coder", roles="coding"))
    code1, out1 = run(["bash", setup])
    check("a coding laptop: setup ends clean and installs its coding-only tool",
          code1 == 0 and "FAILED" not in out1
          and "2 tool(s) declared for a coding, 0 problem(s)" in out1
          and read(os.path.join(home, "coder.installs")) == "x\n", out1)
    before = {p: (read(p), os.stat(p).st_mtime_ns) for p in (union, TOOLS_JSON)}
    open(CALLS, "w").close()
    code2, out2 = run(["bash", setup])
    check("and a second run there is clean and changes nothing",
          code2 == 0 and "FAILED" not in out2 and "Brewfile.all unchanged" in out2
          and all((read(p), os.stat(p).st_mtime_ns) == before[p] for p in before)
          and read(os.path.join(home, "coder.installs")) == "x\n"
          and sorted(read(CALLS).splitlines()) == sorted(first_calls.splitlines()),
          (out2, read(CALLS)))
    os.remove(ROLE)
    os.remove(os.path.join(M, "tools", "coder.sh"))
    shutil.rmtree(os.path.join(home, ".coder"))
    tools("install")

    # Off a Mac: refused, and nothing runs.
    write(os.path.join(shims, "uname"), "#!/bin/bash\necho Linux\n", EXE)
    open(CALLS, "w").close()
    os.rename(widget, widget + ".away")
    code, out = run(["bash", setup])
    check("off a Mac, setup refuses, runs no mise or brew and installs no descriptor",
          code != 0 and not calls("mise") and not calls("brew")
          and "not a Mac" in out
          and not os.path.exists(widget), (out, calls()))
    os.rename(widget + ".away", widget)
    write(os.path.join(shims, "uname"), "#!/bin/bash\necho Darwin\n", EXE)

    # =======================================================================
    # descriptors
    # =======================================================================
    code, out = tools("list")
    check("list names the tool, its version, where and its subjects",
          code == 0 and "widget" in out and "1.0.0" in out and widget in out
          and "(projects/M)" in out, out)
    code, out = tools("path")
    check("path prints the directories the tools live in",
          code == 0 and out.strip() == os.path.dirname(widget), out)
    code, out = tools("update")
    check("update the day it was installed runs nothing (T_EVERY_DAYS)",
          code == 0 and "->" not in out, out)
    write(os.path.join(M, "tools", "widget.sh"), descriptor(
        "widget", update='echo 1.1.0 >"$HOME/.widget/version"'))
    code, out = tools("update", "--force")
    rec = tools_json()["tools"]["widget"]
    check("update --force runs T_UPDATE and reads the version before and after",
          code == 0 and "widget 1.0.0 -> 1.1.0" in out and rec["version"] == "1.1.0"
          and not rec.get("failed"), (out, rec))
    write(os.path.join(M, "tools", "widget.sh"), descriptor("widget", update="exit 4"))
    code, out = tools("update", "--force")
    rec = tools_json()["tools"]["widget"]
    check("a failing T_UPDATE: exit 1, and tools.json says so",
          code == 1 and "widget did not update (exit 4)" in out
          and rec["failed"] == "T_UPDATE exited 4" and rec["failed_step"] == "update",
          (out, rec))
    code, out = run(["bash", setup])
    check("setup's install leaves an update failure standing",
          tools_json()["tools"]["widget"].get("failed") == "T_UPDATE exited 4", out)
    said = brewcare.tool_lines_of(tools_json())
    check("brewcare names it", "tools: widget failed: T_UPDATE exited 4" in said, said)
    write(os.path.join(M, "tools", "widget.sh"), descriptor("widget"))
    # A build.zig.zon under a mise.toml that pins no zig is never fetched.
    Z = os.path.join(atlas, "projects", "Z")
    write(os.path.join(Z, "tutorboard.json"), json.dumps({"check": "zig build test"}))
    write(os.path.join(Z, "mise.toml"), '[tools]\nrust = "1.80.0"\n')
    write(os.path.join(Z, "mise.lock"), "locked\n")
    write(os.path.join(Z, "warden", "build.zig.zon"), ".{ .name = .warden }\n")
    code, out = tools("update", "--force")
    check("and it clears once an update works",
          code == 0 and not tools_json()["tools"]["widget"].get("failed"), out)
    write(os.path.join(M, "tools", "widget.sh"), descriptor("widget", update=""))
    doc = tools_json()
    doc["tools"]["widget"]["updated"] = "2026-01-01T00:00:00"
    write(TOOLS_JSON, json.dumps(doc))
    code, out = tools("update", "--force")
    rec = tools_json()["tools"]["widget"]
    check("no T_UPDATE is no failure: updated by hand, its T_MANUAL kept",
          code == 0 and not rec.get("failed") and "0 problem(s)" in out
          and rec.get("manual") == "by hand: fetch widget by hand"
          and rec["updated"] == "2026-01-01T00:00:00", (out, rec))
    said = brewcare.tool_lines_of(tools_json())
    check("and it is named only once stale, with what to do by hand",
          "tools: widget not updated since Jan 1 00:00 (stale after 14 days); by hand: "
          "fetch widget by hand" in said and not [l for l in said if "failed" in l], said)
    write(os.path.join(home, ".widget", "version"), "1.2.0\n")
    code, out = tools("update", "--force")
    rec = tools_json()["tools"]["widget"]
    check("a version the owner moved counts as updated",
          code == 0 and rec["version"] == "1.2.0"
          and rec["updated"] != "2026-01-01T00:00:00", rec)
    write(os.path.join(M, "tools", "widget.sh"), descriptor("widget"))
    # A build.zig.zon under a mise.toml that pins no zig is never fetched.
    Z = os.path.join(atlas, "projects", "Z")
    write(os.path.join(Z, "tutorboard.json"), json.dumps({"check": "zig build test"}))
    write(os.path.join(Z, "mise.toml"), '[tools]\nrust = "1.80.0"\n')
    write(os.path.join(Z, "mise.lock"), "locked\n")
    write(os.path.join(Z, "warden", "build.zig.zon"), ".{ .name = .warden }\n")
    write(os.path.join(home, ".widget", "version"), "1.1.0\n")
    code, out = tools("update", "--force")
    check("and a T_UPDATE again drops the by-hand note",
          code == 0 and "manual" not in tools_json()["tools"]["widget"], tools_json())

    # The last try is stamped when its run ended; the daily run starts a day
    # after the last one began, so a day minus the run's length has passed.
    write(os.path.join(M, "tools", "widget.sh"), descriptor(
        "widget", update='echo 1.3.0 >"$HOME/.widget/version"'))
    for hours, moves in ((24 - 5.0 / 3600, True), (19, False)):
        write(os.path.join(home, ".widget", "version"), "1.1.0\n")
        doc = tools_json()
        ago = (datetime.now() - timedelta(hours=hours)).replace(microsecond=0).isoformat()
        doc["tools"]["widget"].update({"attempted": ago, "updated": ago})
        write(TOOLS_JSON, json.dumps(doc))
        code, out = tools("update")
        check("T_EVERY_DAYS=1, last tried %.3fh ago: %s" % (
            hours, "it updates" if moves else "not yet"),
              code == 0 and ("widget 1.1.0 -> 1.3.0" in out) is moves, out)
    write(os.path.join(M, "tools", "widget.sh"), descriptor("widget", check_cmd="false"))
    code, out = tools("check")
    check("a failing T_CHECK fails check, recorded",
          code == 1 and "widget fails its check: false" in out
          and tools_json()["tools"]["widget"]["failed_step"] == "check", out)
    write(os.path.join(M, "tools", "widget.sh"), descriptor("widget"))
    # A build.zig.zon under a mise.toml that pins no zig is never fetched.
    Z = os.path.join(atlas, "projects", "Z")
    write(os.path.join(Z, "tutorboard.json"), json.dumps({"check": "zig build test"}))
    write(os.path.join(Z, "mise.toml"), '[tools]\nrust = "1.80.0"\n')
    write(os.path.join(Z, "mise.lock"), "locked\n")
    write(os.path.join(Z, "warden", "build.zig.zon"), ".{ .name = .warden }\n")
    code, out = tools("check")
    check("and a passing one clears it", code == 0 and "widget works (1.1.0)" in out
          and not tools_json()["tools"]["widget"].get("failed"), out)

    write(os.path.join(M, "tools", "gadget.sh"), descriptor("gadget", install=False))
    write(os.path.join(M, "tools", "laptopper.sh"),
          descriptor("laptopper", roles="coding"))
    code, out = tools("install")
    check("a tool with no T_INSTALL is reported with its T_MANUAL, exit 1",
          code == 1 and "gadget is not installed; by hand: fetch gadget by hand" in out
          and tools_json()["tools"]["gadget"]["failed"]
          == "not installed; by hand: fetch gadget by hand", out)
    check("a coding-only tool is not installed on a host",
          "laptopper" not in out and "laptopper" not in tools_json()["tools"], out)
    write(os.path.join(home, ".config", "tutor-board", "role"), "coding\n")
    code, out = tools("install")
    check("and is on a coding laptop",
          "laptopper installed (1.0.0)" in out
          and os.path.exists(os.path.join(home, ".laptopper", "bin", "laptopper")), out)
    os.remove(os.path.join(home, ".config", "tutor-board", "role"))
    os.remove(os.path.join(M, "tools", "gadget.sh"))
    os.remove(os.path.join(M, "tools", "laptopper.sh"))

    write(os.path.join(M, "tools", "wrong.sh"), descriptor("other"))
    code, out = tools("install")
    check("a descriptor whose T_NAME is not its file's name is refused",
          code == 1 and "wrong.sh: T_NAME must be wrong and T_BIN set" in out, out)
    os.remove(os.path.join(M, "tools", "wrong.sh"))

    D = os.path.join(atlas, "projects", "D")
    os.makedirs(os.path.join(D, "tools"))
    shutil.copy(os.path.join(M, "tools", "widget.sh"), os.path.join(D, "tools"))
    plan, conflicts = toolplan.descriptors(atlas)
    check("the same bytes in two subjects are one tool",
          [p["subjects"] for p in plan] == [["projects/D", "projects/M"]]
          and not conflicts, (plan, conflicts))
    write(os.path.join(D, "tools", "widget.sh"), descriptor("widget", every=7))
    code, out = tools("update")
    check("differing bytes: neither is used, both are named, exit 1",
          code == 1 and "widget: declared differently in projects/D/tools/widget.sh and "
          "projects/M/tools/widget.sh" in out and "0 tool(s) declared" in out, out)
    doc = tools_json()
    check("and tools.json and brewcare name the conflict, not as left behind",
          doc.get("conflicts") == [{"name": "widget", "paths": [
              "projects/D/tools/widget.sh", "projects/M/tools/widget.sh"]}]
          and "widget" in doc["tools"] and "widget" not in (doc.get("left") or {})
          and any("widget is declared differently" in l
                  for l in brewcare.tool_lines_of(doc)), doc)
    shutil.rmtree(D)
    code, out = tools("install")
    check("removing one copy clears it", code == 0 and "conflicts" not in tools_json(),
          out)
    # tools.sh names no tool: a name it has never seen installs, and no name a
    # real descriptor (the subjects' or ai-config's) uses appears in it.
    fresh = "t" + uuid.uuid4().hex[:10]
    write(os.path.join(M, "tools", fresh + ".sh"), descriptor(fresh))
    code, out = tools("install")
    check("a tool of any name installs: %s" % fresh,
          code == 0 and "%s installed (1.0.0)" % fresh in out
          and os.path.exists(os.path.join(home, "." + fresh, "bin", fresh)), out)
    os.remove(os.path.join(M, "tools", fresh + ".sh"))
    shutil.rmtree(os.path.join(home, "." + fresh))
    tools("install")
    body = read(os.path.join(ATLAS_REAL, "scripts", "tools.sh"))
    names = set()
    for pat in ("*/*/tools/*.sh", "ai-config/assistants/*.sh"):
        for f in glob.glob(os.path.join(ATLAS_REAL, pat)):
            names.add(os.path.basename(f)[:-3])
    names.discard("registry")
    check("tools.sh names no tool any descriptor declares",
          not [n for n in names if re.search(r"\b%s\b" % re.escape(n), body)],
          sorted(names))

    # =======================================================================
    # removal: a deleted subject leaves the plan; nothing is uninstalled
    # =======================================================================
    os.makedirs(os.path.join(prefix, "Cellar", "ripgrep", "14.1"))
    os.makedirs(os.path.join(prefix, "Cellar", "widget-cli", "1.0"))
    shutil.rmtree(M)
    shutil.rmtree(Z)
    open(CALLS, "w").close()
    code, out = run(["bash", setup])
    doc = tools_json()
    check("a deleted subject: setup is clean and its Brewfile lines leave the union",
          code == 0 and 'brew "ripgrep"' not in read(union)
          and 'tap "acme/tools"' not in read(union) and 'brew "uv"' in read(union)
          and "Brewfile.all rewritten" in out, (out, read(union)))
    check("nothing is uninstalled",
          not [l for l in calls("brew") if "uninstall" in l or "cleanup" in l
               or "untap" in l] and os.path.exists(widget), calls())
    check("its descriptor leaves the plan and is remembered as left behind",
          "widget" not in doc.get("tools", {})
          and doc["left"]["widget"]["dir"] == os.path.dirname(widget)
          and sorted(doc["left_brew"]) == ['brew "acme/tools/widget-cli"',
                                           'brew "ripgrep"', 'tap "acme/tools"'], doc)
    said = brewcare.tool_lines_of(doc, prefix=prefix)
    check("brewcare names each leftover still installed",
          "tools: no longer declared: widget at %s" % os.path.dirname(widget) in said
          and "tools: no longer declared: ripgrep at %s"
              % os.path.join(prefix, "Cellar", "ripgrep") in said
          and "tools: no longer declared: acme/tools/widget-cli at %s"
              % os.path.join(prefix, "Cellar", "widget-cli") in said, said)
    shutil.rmtree(os.path.join(prefix, "Cellar", "ripgrep"))
    os.remove(widget)
    said = brewcare.tool_lines_of(doc, prefix=prefix)
    check("and stops once the owner removes it",
          not [l for l in said if "ripgrep" in l or "widget at" in l], said)
    write(os.path.join(atlas, "projects", "N", "Brewfile"), 'brew "ripgrep"\n')
    run(["bash", setup])
    check("an entry that comes back leaves left_brew",
          'brew "ripgrep"' not in tools_json().get("left_brew", {}), tools_json())

    # =======================================================================
    # reporting
    # =======================================================================
    N = datetime(2026, 10, 23, 9, 0)
    doc = {"tools": {
        "fresh": {"updated": "2026-10-22T03:00:00", "stale_days": 14},
        "old": {"updated": "2026-10-01T03:00:00", "stale_days": 14},
        "never": {"seen": "2026-09-01T03:00:00"},
        "broke": {"updated": "2026-10-01T03:00:00", "failed": "T_UPDATE exited 1"}},
        "pins": [{"subject": "projects/S", "tool": "node", "pinned": "20.0.0",
                  "latest": "22.1.0"}]}
    said = brewcare.tool_lines_of(doc, N, prefix="")
    check("brewcare: a failure, each tool past its T_STALE_DAYS, a pin behind",
          said == ["tools: broke failed: T_UPDATE exited 1",
                   "tools: never not updated since Sep 1 03:00 (stale after 14 days)",
                   "tools: old not updated since Oct 1 03:00 (stale after 14 days)",
                   "tools: pin behind: projects/S node 20.0.0 -> 22.1.0"], said)
    write(TOOLS_JSON, json.dumps(doc))
    check("the doctor's summary counts them",
          brewcare.tools_summary(state, N) == "4 declared, 1 failed, 2 stale, "
          "0 no longer declared, 1 pins behind", brewcare.tools_summary(state, N))
    write(os.path.join(state, "brew.json"), json.dumps({
        "mode": "defer", "failed": {"tool:broke": "T_UPDATE exited 1"}}))
    said = brewcare.lines(state, N)
    check("brewcare.lines, which reach home through /sync.json, name a failure once",
          len([l for l in said if "broke" in l]) == 1
          and "tools: broke did not update: T_UPDATE exited 1" in said
          and "tools: pin behind: projects/S node 20.0.0 -> 22.1.0" in said, said)
    os.remove(os.path.join(state, "brew.json"))
    check("no tools.json: no summary", brewcare.tools_summary(work) is None)
    check("and doctor's line says to run setup only on a Mac, which writes it",
          brewcare.tools_doctor(work, platform="darwin")
          == "no tools.json yet (bash scripts/setup.sh)"
          and brewcare.tools_doctor(work, platform="linux")
          == "not kept here (the descriptors and mise are Mac only)",
          brewcare.tools_doctor(work, platform="linux"))

    write(os.path.join(atlas, "projects", "S", "app", "mise.toml"),
          '[tools]\n"cargo:ripgrep" = "14"  # a comment = x\nnode = { version = "20" }\n'
          '[tools.python]\nversion = "3.12"\n[env]\nX = "1"\n')
    check("mise_tools: the tools every mise.toml pins, and nothing from another table",
          toolplan.mise_tools(atlas) == ["cargo:ripgrep", "node", "python"],
          toolplan.mise_tools(atlas))
    check("pinned_in: one directory's own tools, which mise install --locked is named",
          toolplan.pinned_in(os.path.join(atlas, "projects", "S", "app"))
          == ["cargo:ripgrep", "node", "python"]
          and toolplan.pinned_in(os.path.join(atlas, "projects", "S")) == [])
    shutil.rmtree(os.path.join(atlas, "projects", "S"))
    def rec(name, requested, current, bump, latest, src):
        """A record of `mise outdated --json --bump --local`, as mise
        2026.10.17 prints it."""
        return {"name": name, "requested": requested, "current": current, "bump": bump,
                "latest": latest, "release_url": "https://example.invalid/" + latest,
                "source": {"type": "mise.toml", "path": src}}
    S = os.path.join(atlas, "projects", "S")
    said = json.dumps({
        "node": rec("node", "20.0.0", "20.0.0", "22.1.0", "22.1.0",
                    os.path.join(S, "mise.toml")),
        "go": rec("go", "1.22", None, "1.25", "1.25.3", os.path.join(S, "mise.toml")),
        "rust": rec("rust", "1.80.0", "1.80.0", None, "1.80.0",
                    os.path.join(S, "mise.toml")),
        "python": rec("python", "3", "3.14.0", None, "3.14.0",
                      os.path.join(S, "mise.toml")),
        "shfmt": rec("shfmt", "3.8.0", "3.8.0", "3.12.0", "3.12.0",
                     os.path.join(atlas, "projects", "mise.toml"))})
    check("mise outdated --bump: behind exactly when bump is set, installed or not, "
          "shown to the newest release; a null bump is current",
          toolplan.pins_of(said, "projects/S")
          == [{"subject": "projects/S", "tool": "go", "pinned": "1.22",
               "latest": "1.25.3"},
              {"subject": "projects/S", "tool": "node", "pinned": "20.0.0",
               "latest": "22.1.0"},
              {"subject": "projects/S", "tool": "shfmt", "pinned": "3.8.0",
               "latest": "3.12.0"}], toolplan.pins_of(said, "projects/S"))
    check("run in a directory, only that directory's own config counts, kept as dir",
          [p["tool"] for p in toolplan.pins_of(said, "projects/S", S)] == ["go", "node"]
          and toolplan.pins_of(said, "projects/S", S)[0]["dir"] == S
          and toolplan.pins_of("not json", "x") == []
          and toolplan.pins_of("[]", "x") == [] and toolplan.pins_of("", "x") == [])

    # =======================================================================
    # paths, and the real tree
    # =======================================================================
    # A python3 among mise's shims, which must never be the agent's.
    mise_py = os.path.join(home, ".local", "share", "mise", "shims", "python3")
    write(mise_py, "#!/bin/sh\nexit 1\n", EXE)
    p = subprocess.run(["bash", os.path.join(BOARD, "install.sh"), "--plist"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       env=dict((k, v) for k, v in os.environ.items() if k != "PYTHON"))
    import plistlib
    try:
        job = plistlib.loads(p.stdout)
    except Exception:                                        # noqa: BLE001
        job = {}
    path = (job.get("EnvironmentVariables") or {}).get("PATH", "")
    check("the tutor-board plist's PATH is install.sh's AGENT_PATH, mise's shims last",
          path.split(":")[-1] == os.path.join(os.path.expanduser("~"), ".local", "share",
                                              "mise", "shims")
          and "/opt/homebrew/bin" in path.split(":")
          and (job.get("ProgramArguments") or [""])[0] not in ("", mise_py)
          and "mise" not in (job.get("ProgramArguments") or [""])[0], (path, job))
    plan, conflicts = toolplan.descriptors(ATLAS_REAL)
    check("the real tree declares no name twice with different bytes", not conflicts,
          conflicts)
finally:
    shutil.rmtree(work, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("every machine installs what the subjects declare, keeps it current, and names "
      "what is left behind")
