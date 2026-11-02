#!/usr/bin/python3
"""brew-upgrade.py -- Atlas's half of the machine upkeep: its upkeep.d/hook.

    atlas-brew hook <phase>         upkeep's call (upkeep.d/hook): protected-casks,
                                    brewfiles, after-brew, toolchain or status
    atlas-brew status               upkeep's last run and this hook's; exit 1 on a problem
    atlas-brew repair [--dry-run]   the probes and repairs, now
    atlas-brew install              link ~/.local/bin/atlas-brew; retire atlas.brew-upgrade

upkeep (upkeep/upkeep.py, `com.mikeyferguson.upkeep`) owns brew, npm, the
schedule and the notifications on every Mac. This file keeps what is
Atlas's. State is $BOARD_STATE_DIR/atlas-upkeep.json (else
~/.local/state/tutor-board/); board/tutorboard/brewcare.py reads it and
upkeep's state for /sync.json and `board doctor`. The log is
~/.local/state/atlas-setup/upkeep-hook.log.

The phases, each with its reason:

  * protected-casks: tailscale on the host while it runs as a brew service,
    because it carries the board's tailnet; upgrade it by hand and restart it.
  * brewfiles: the Brewfile union setup.sh bundles (the root Brewfile and
    every subject's, `toolplan.write_union`), so upkeep installs a new entry.
  * after-brew: repairs that act only on breakage. A subject's .venv that
    cannot start is re-synced with `uv sync --locked`; the board's LaunchAgent
    whose interpreter is gone is reinstalled.
  * toolchain: `uv python upgrade`, `mise install --locked <tools>` in every
    subject directory holding a mise.toml, `mise prune --tools` of the tools
    those files name, `scripts/tools.sh update`, and the mise pins behind
    into tools.json. Install names the directory's own tools because
    --locked fails on any tool without a mise.lock entry; the prune is named
    because a bare one removes versions the owner's other projects use. A pin
    moves only by a commit of mise.toml and mise.lock, never from here.
  * status: the probes again, report only (venvs, TeX, the board's agent and
    reachability), then each failed tool and each tools.json line but a pin
    behind, as upkeep's problem lines. upkeep re-asks hourly while any stand.

UPKEEP_DRY_RUN=1 makes every mutating call a description. Stdlib only and
3.7-clean: upkeep runs it under /usr/bin/python3.
"""

import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime

sys.dont_write_bytecode = True

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.realpath(__file__))
ATLAS = os.path.dirname(HERE)
BOARD_DIR = os.path.join(ATLAS, "board")
SCRIPT = os.path.realpath(__file__)

STATE_DIR = os.environ.get("BOARD_STATE_DIR") or os.path.join(HOME, ".local", "state",
                                                              "tutor-board")
STATE = os.path.join(STATE_DIR, "atlas-upkeep.json")
TOOLS_JSON = os.path.join(STATE_DIR, "tools.json")
SETUP_DIR = os.path.join(os.environ.get("XDG_STATE_HOME")
                         or os.path.join(HOME, ".local", "state"), "atlas-setup")
LOG = os.path.join(SETUP_DIR, "upkeep-hook.log")
CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME")
                          or os.path.join(HOME, ".config"), "tutor-board")
ROLE_FILE = os.path.join(CONFIG_DIR, "role")
BOARD_CONFIG = os.path.join(CONFIG_DIR, "config.json")
AGENTS = os.path.join(HOME, "Library", "LaunchAgents")
BOARD_AGENT = os.path.join(AGENTS, "tutor-board.plist")
RETIRED = "atlas.brew-upgrade"
LINK = os.path.join(HOME, ".local", "bin", "atlas-brew")
UV_PYTHONS = os.path.join(HOME, ".local", "share", "uv", "python")
TOOLS_SH = os.path.join(ATLAS, "scripts", "tools.sh")

LOG_MAX = 2000000
BOARD_PORT = 8778
T_TOOLS = 1800
T_MISE = 3600
T_UVPY = 1800
T_UVSYNC = 1800
T_BINSTALL = 3600
T_PROBE = 60

DRY = bool(os.environ.get("UPKEEP_DRY_RUN"))
PHASES = ("protected-casks", "brewfiles", "after-brew", "toolchain", "status")


def now():
    return datetime.now()


def stamp(when=None):
    return (when or now()).replace(microsecond=0).isoformat()


def run(argv, timeout, mutating=False, env=None, cwd=None):
    """(code, stdout, stderr). Never raises: a timeout is 124, a missing
    program 127. A mutating call under a dry run is described, not run."""
    argv = [str(a) for a in argv]
    if mutating and DRY:
        log("[dry-run] would run %s" % " ".join(argv))
        return 0, "", ""
    full = dict(os.environ)
    path = [d for d in full.get("PATH", "").split(os.pathsep) if d]
    for d in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin",
              "/sbin"):
        if d not in path:
            path.append(d)
    full["PATH"] = os.pathsep.join(path)
    if env:
        full.update(env)
    try:
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           stdin=subprocess.DEVNULL, universal_newlines=True,
                           timeout=timeout, env=full, cwd=cwd, start_new_session=True)
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", "timed out after %ds" % timeout
    except (OSError, ValueError) as exc:
        return 127, "", str(exc)


def log(msg):
    """One stamped line in the hook's log; echoed on a terminal or a dry run."""
    line = "[%s] %s" % (now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    if DRY or sys.stderr.isatty():
        print(line, file=sys.stderr, flush=True)
    if DRY:
        return
    try:
        os.makedirs(SETUP_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def log_tail(out, tag, n=8):
    for l in [l for l in (out or "").splitlines() if l.strip()][-n:]:
        log("    [%s] %s" % (tag, l))


def last_line(*outs):
    for out in outs:
        lines = [l.strip() for l in (out or "").splitlines() if l.strip()]
        if lines:
            return lines[-1][:300]
    return ""


def trim_log():
    if DRY:
        return
    try:
        if os.path.getsize(LOG) <= LOG_MAX:
            return
        with open(LOG, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        with open(LOG + ".tmp", "w", encoding="utf-8") as fh:
            fh.writelines(lines[len(lines) // 2:])
        os.replace(LOG + ".tmp", LOG)
    except OSError:
        pass


def load_state():
    try:
        with open(STATE, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state):
    if DRY:
        return
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(STATE + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(STATE + ".tmp", STATE)
    except OSError as exc:
        log("! could not write %s: %s" % (STATE, exc))


def read_role():
    try:
        with open(ROLE_FILE, encoding="utf-8") as fh:
            return "coding" if fh.read().strip() == "coding" else "host"
    except OSError:
        return "host"


def board_port():
    try:
        with open(BOARD_CONFIG, encoding="utf-8") as fh:
            port = int(json.load(fh).get("port") or BOARD_PORT)
        return port if 0 < port < 65536 else BOARD_PORT
    except (OSError, ValueError, TypeError, AttributeError):
        return BOARD_PORT


def read_plist(path):
    try:
        with open(path, "rb") as fh:
            data = plistlib.load(fh)
        return data if isinstance(data, dict) else None
    except Exception:                                        # noqa: BLE001
        return None


def board_import(name):
    """A tutorboard module, from this checkout's board/, or None."""
    if BOARD_DIR not in sys.path:
        sys.path.insert(0, BOARD_DIR)
    try:
        return __import__("tutorboard." + name, fromlist=[name])
    except Exception:                                        # noqa: BLE001
        return None


def subject_list():
    mod = board_import("subjects")
    if mod is None:
        return None
    try:
        return [(s["id"], s["root"]) for s in mod.all(base=ATLAS)]
    except Exception:                                        # noqa: BLE001
        return None


def has_extra(pyproject, want):
    """Does pyproject.toml declare the optional extra `want`? A line scan."""
    inside = False
    try:
        with open(pyproject, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if line.startswith("["):
                    inside = line == "[project.optional-dependencies]"
                    continue
                parts = line.split()
                if inside and len(parts) >= 2 and parts[0] == want and parts[1] == "=":
                    return True
    except OSError:
        pass
    return False


def problem(what, fix):
    return {"what": what, "fix": fix}


# ---------------------------------------------------------------- the probes

def act(argv, timeout, acting, cwd=None):
    """Run a repair: True when it ran and worked, None when it did not run."""
    if not acting:
        return None
    code, out, err = run(argv, timeout, mutating=True, cwd=cwd)
    if DRY:
        return None
    if code != 0:
        log_tail(out + "\n" + err, os.path.basename(argv[0]))
    return code == 0


def probe_board_agent(acting):
    data = read_plist(BOARD_AGENT)
    if data is None:
        return [problem("no tutor-board LaunchAgent", "bash board/install.sh")]
    args = data.get("ProgramArguments") or []
    exe = str(args[0]) if args else ""
    if exe and os.path.exists(exe):
        return []
    log("probe board agent: its interpreter %s is gone" % (exe or "(none)"))
    if act(["bash", os.path.join(ATLAS, "board", "install.sh")], T_BINSTALL, acting):
        log("repaired: board/install.sh re-rendered and reloaded tutor-board")
        return []
    return [problem("the tutor-board LaunchAgent's python %s is gone" % exe,
                    "bash board/install.sh")]


def probe_venvs(acting):
    subs = subject_list()
    if subs is None:
        return [problem("the subjects could not be listed", "python3 board/bin/board doctor")]
    out = []
    for ident, root in subs:
        pyproject = os.path.join(root, "pyproject.toml")
        if not os.path.isfile(pyproject):
            continue
        venv = os.path.join(root, ".venv")
        if not os.path.isdir(venv):
            out.append(problem("%s has no .venv" % ident, "bash scripts/setup.sh"))
            continue
        code, _, _ = run([os.path.join(venv, "bin", "python"), "-c", "pass"], T_PROBE)
        if code == 0:
            continue
        log("probe venv %s: broken (exit %d)" % (ident, code))
        argv = ["uv", "sync", "--locked"]
        if has_extra(pyproject, "test"):
            argv += ["--extra", "test"]
        if act(argv, T_UVSYNC, acting, cwd=root):
            log("repaired: %s's .venv re-synced" % ident)
            continue
        out.append(problem("%s's .venv does not start" % ident,
                           "cd %s && %s" % (ident, " ".join(argv))))
    return out


def probe_tex():
    """TeX's programs and the packages the board's builds load. Report only."""
    mod = board_import("tex")
    try:
        dirs = mod.tex_bin_dirs() if mod else []
    except Exception:                                        # noqa: BLE001
        dirs = []
    path = os.pathsep.join(dirs + [os.environ.get("PATH", "")])
    missing = [exe for exe in ("latex", "pdflatex", "dvisvgm", "latexmk")
               if not shutil.which(exe, path=path)]
    stys = ["standalone.sty", "varwidth.sty", "preview.sty", "needspace.sty"]
    kpse = shutil.which("kpsewhich", path=path)
    absent = list(stys)
    if kpse:
        _, out, _ = run([kpse] + stys, T_PROBE)
        found = set(os.path.basename(l.strip()) for l in out.splitlines() if l.strip())
        absent = [s for s in stys if s not in found]
    if not missing and not absent:
        return []
    if missing or not kpse:
        return [problem("TeX is missing %s" % ", ".join(missing + absent),
                        "brew reinstall texlive")]
    return [problem("TeX is missing %s" % ", ".join(absent),
                    "tlmgr install %s" % " ".join(s[:-4] for s in absent))]


def probe_board_serve():
    """The board answers and tailscale serves it. Report only."""
    port = board_port()
    out = []
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=10) as r:
            up = r.status == 200
    except Exception:                                        # noqa: BLE001
        up = False
    if not up:
        out.append(problem("the board does not answer on 127.0.0.1:%d" % port,
                           "see ~/.local/state/tutor-board/server.log"))
    _, said, _ = run(["tailscale", "serve", "status"], T_PROBE)
    if "127.0.0.1:%d" % port not in said:
        out.append(problem("tailscale does not serve the board",
                           "tailscale serve --bg --https=443 http://127.0.0.1:%d" % port))
    return out


def probes(role, acting):
    found = []
    if role == "host":
        found += probe_board_agent(acting)
    found += probe_venvs(acting)
    found += probe_tex()
    if role == "host":
        found += probe_board_serve()
    for p in found:
        log("problem: %s; %s" % (p["what"], p["fix"]))
    return found


# ------------------------------------------------------------- the toolchain

def mise_env():
    """mise answers no prompt here, and trusts the Atlas tree's own configs
    for this call only; setup.sh trusts them for good."""
    return {"MISE_YES": "1", "MISE_TRUSTED_CONFIG_PATHS": ATLAS}


def tool_failures():
    """{tool:<name>: why} for each tool tools.json says failed."""
    try:
        with open(TOOLS_JSON, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return {}
    tools = doc.get("tools") if isinstance(doc, dict) else None
    return dict(("tool:" + name, str(rec.get("failed")))
                for name, rec in sorted((tools or {}).items())
                if isinstance(rec, dict) and rec.get("failed"))


def toolchain():
    """uv's Pythons, the subjects' mise pins, the descriptors, the pins
    behind. {tool:<name>: why} of what failed."""
    failed = {}
    uv = shutil.which("uv", path=os.environ.get("PATH", "") + os.pathsep
                      + "/opt/homebrew/bin" + os.pathsep + "/usr/local/bin")
    try:
        pythons = [n for n in os.listdir(UV_PYTHONS) if n.startswith("cpython-")]
    except OSError:
        pythons = []
    if uv and pythons:
        code, out, err = run([uv, "python", "upgrade"], T_UVPY, mutating=True)
        if code != 0:
            failed["tool:uv-python"] = last_line(err, out) or "exit %d" % code
            log_tail(out + "\n" + err, "uv")

    plan = board_import("toolplan")
    try:
        dirs = [(i, d, plan.pinned_in(d)) for i, d in plan.mise_dirs(ATLAS)] if plan else []
        pinned = plan.mise_tools(ATLAS) if plan else []
    except Exception:                                        # noqa: BLE001
        dirs, pinned = [], []
    for ident, where, names in dirs:
        if not names:
            continue
        code, out, err = run(["mise", "install", "--locked"] + names, T_MISE,
                             mutating=True, cwd=where, env=mise_env())
        if code != 0:
            failed["tool:mise:" + ident] = last_line(err, out) or "exit %d" % code
            log_tail(out + "\n" + err, "mise")
    if pinned:
        code, out, err = run(["mise", "prune", "--yes", "--tools"] + pinned, T_MISE,
                             mutating=True, env=mise_env())
        if code != 0:
            failed["tool:mise-prune"] = last_line(err, out) or "exit %d" % code

    if os.path.isfile(TOOLS_SH):
        code, out, err = run(["bash", TOOLS_SH, "update"], T_TOOLS, mutating=True)
        if code != 0:
            log_tail(out + "\n" + err, "tools.sh")
        if not DRY:
            said = tool_failures()
            failed.update(said)
            if code != 0 and not said:
                failed["tool:tools.sh"] = last_line(out, err) or "exit %d" % code

    pins = []
    for ident, where, _names in dirs:
        code, out, err = run(["mise", "outdated", "--json", "--bump", "--local"],
                             T_PROBE * 5, cwd=where, env=mise_env())
        if code == 0 and plan is not None:
            pins += plan.pins_of(out, ident, where)
        elif code != 0:
            log("! mise outdated in %s exited %d" % (ident, code))
    for p in pins:
        log("pin behind: %s %s %s -> %s" % (p["subject"], p["tool"], p["pinned"],
                                            p["latest"]))
    if plan is not None and not DRY:
        try:
            plan.write_pins(pins)
        except Exception as exc:                             # noqa: BLE001
            log("! could not write tools.json: %s" % exc)
    for name, why in sorted(failed.items()):
        log("! %s: %s" % (name, why))
    return failed


# ----------------------------------------------------------------- the phases

def brewfile_union():
    """The Brewfile union's path: Brewfile.all, rewritten by toolplan only
    when it changed; under a dry run, a temp copy when it would change. The
    root Brewfile alone when toolplan cannot answer."""
    plan = board_import("toolplan")
    dest = os.path.join(SETUP_DIR, "Brewfile.all")
    try:
        if plan is None:
            raise ValueError("no toolplan")
        if not DRY:
            plan.write_union(ATLAS, dest)
            return dest
        text = plan.union_text(ATLAS)
        try:
            with open(dest, encoding="utf-8") as fh:
                if fh.read() == text:
                    return dest
        except OSError:
            pass
        fd, tmp = tempfile.mkstemp(prefix="Brewfile.all.")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        return tmp
    except Exception:                                        # noqa: BLE001
        root = os.path.join(ATLAS, "Brewfile")
        return root if os.path.isfile(root) else None


def tailscale_service():
    return any(os.path.exists(os.path.join(d, "homebrew.mxcl.tailscale.plist"))
               for d in (AGENTS, "/Library/LaunchAgents", "/Library/LaunchDaemons"))


def status_lines(state):
    """The lines upkeep shows: each problem, each failed tool, and each
    tools.json line but a pin behind (a pin is the subject's to propose)."""
    out = ["%s; %s" % (p.get("what"), p.get("fix")) for p in state.get("problems") or []
           if isinstance(p, dict)]
    failed = state.get("failed") or {}
    for name, why in sorted(failed.items()):
        out.append("%s did not update: %s" % (name[5:] if name.startswith("tool:")
                                               else name, why))
    care = board_import("brewcare")
    if care is not None:
        try:
            doc = care.read_tools(STATE_DIR)
            skip = set(k[5:] for k in failed if k.startswith("tool:"))
            for line in care.tool_lines_of(doc, now(), skip=skip) if doc else []:
                if not line.startswith("tools: pin behind: "):
                    out.append(line[len("tools: "):])
        except Exception:                                    # noqa: BLE001
            pass
    return out


def cmd_hook(ph):
    trim_log()
    role = read_role()
    if ph == "protected-casks":
        if role == "host" and tailscale_service():
            print("tailscale")
        return 0
    if ph == "brewfiles":
        bf = brewfile_union()
        if bf:
            print(bf)
        return 0
    state = load_state()
    state["role"] = role
    if ph == "after-brew":
        log("after-brew: the repairs")
        state.update({"problems": probes(role, True), "probed_at": stamp(),
                      "after_brew_at": stamp()})
        save_state(state)
        return 0
    if ph == "toolchain":
        log("toolchain")
        state["toolchain_attempt"] = stamp()
        save_state(state)
        failed = toolchain()
        state["failed"] = failed
        if not failed:
            state["toolchain_success"] = stamp()
        save_state(state)
        return 0
    state.update({"problems": probes(role, False), "probed_at": stamp()})
    save_state(state)
    for line in status_lines(state):
        print(line)
    return 0


def cmd_repair():
    role = read_role()
    state = load_state()
    state.update({"role": role, "problems": probes(role, True), "probed_at": stamp()})
    save_state(state)
    for line in status_lines(state):
        print(line)
    return 1 if state["problems"] else 0


def cmd_status():
    care = board_import("brewcare")
    if care is None:
        print("board/tutorboard/brewcare.py could not be loaded")
        return 1
    print("upkeep:   %s" % care.summary(STATE_DIR))
    state = load_state()
    print("role:     %s" % read_role())
    print("atlas:    toolchain %s, probed %s" % (state.get("toolchain_success") or "never",
                                                 state.get("probed_at") or "never"))
    lines = care.lines(STATE_DIR)
    for line in lines:
        print("  %s" % line)
    return 1 if [l for l in lines if not l.startswith("tools: pin behind: ")] else 0


def cmd_install():
    """Link atlas-brew and retire the old LaunchAgent: upkeep runs the hook."""
    old = os.path.join(AGENTS, RETIRED + ".plist")
    if os.path.exists(old):
        run(["launchctl", "bootout", "gui/%d/%s" % (os.getuid(), RETIRED)], T_PROBE)
        try:
            os.remove(old)
        except OSError:
            pass
        print("%s retired: booted out, its plist removed" % RETIRED)
    try:
        os.makedirs(os.path.dirname(LINK), exist_ok=True)
        if os.path.islink(LINK) and os.readlink(LINK) != SCRIPT:
            os.remove(LINK)
        if not os.path.lexists(LINK):
            os.symlink(SCRIPT, LINK)
    except OSError as exc:
        print("could not link %s: %s" % (LINK, exc))
        return 1
    print("atlas-brew linked; upkeep runs Atlas's hook (upkeep.d/hook)")
    return 0


USAGE = ("usage: atlas-brew hook <%s> | status | repair [--dry-run] | install"
         % "|".join(PHASES))


def main(argv):
    global DRY
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "hook" and len(rest) == 1 and rest[0] in PHASES:
        return cmd_hook(rest[0])
    if cmd == "hook" and len(rest) == 1:
        return 0                     # a phase a newer upkeep asks for: nothing to say
    if cmd == "repair" and rest in ([], ["--dry-run"]):
        DRY = DRY or bool(rest)
        return cmd_repair()
    if cmd == "status" and not rest:
        return cmd_status()
    if cmd == "install" and not rest:
        return cmd_install()
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
