#!/usr/bin/env python3
"""upkeep's tests. Stdlib unittest; nothing on this machine is touched.

    python3 upkeep/test_upkeep.py

Every program upkeep calls (brew, npm, node, opencode, launchctl, defaults,
sdkmanager, flutter, xcodebuild, xcode-select, mas, code, pmset, ioreg, curl,
pgrep, ps, osascript, caffeinate) is one fake, first on the PATH, that logs
its argv and answers from a JSON scenario file. HOME, /Applications, the root
helper's status and every state directory are temp dirs. The suite refuses to
run when any fake resolves anywhere else. upkeep itself runs under
/usr/bin/python3, the interpreter its LaunchAgents use.
"""

import json
import os
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
PY = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
sys.path.insert(0, HERE)
import upkeep as U                                           # noqa: E402

PROGRAMS = ["brew", "npm", "node", "launchctl", "defaults", "sdkmanager", "flutter",
            "xcodebuild", "xcode-select", "mas", "code", "pmset", "ioreg", "curl",
            "pgrep", "ps", "osascript", "caffeinate"]

FAKE = r'''#!/usr/bin/python3
import json, os, sys
name = os.path.basename(sys.argv[0])
args = sys.argv[1:]
D = os.environ["FAKE_DIR"]
def cfg():
    try:
        with open(os.path.join(D, "scenario.json")) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}
C = cfg()
stdin = ""
if name in ("defaults", "sdkmanager") and ("import" in args or "--licenses" in args
                                           or any(";" in a for a in args)):
    stdin = sys.stdin.read()
with open(os.path.join(D, "calls.jsonl"), "a") as fh:
    fh.write(json.dumps({"prog": name, "args": args, "cwd": os.getcwd(),
                         "stdin": len(stdin)}) + "\n")
line = " ".join(args)
for pat, code in (C.get("exit") or {}).items():
    if (name + " " + line).startswith(pat):
        sys.stdout.write((C.get("say") or {}).get(pat, ""))
        sys.exit(code)
def out(s):
    sys.stdout.write(s)
def loaded():
    try:
        with open(os.path.join(D, "loaded.json")) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return []
def save_loaded(v):
    with open(os.path.join(D, "loaded.json"), "w") as fh:
        json.dump(v, fh)
def opencode_works():
    p = os.path.join(os.path.dirname(sys.argv[0]), "opencode")
    with open(p, "w") as fh:
        fh.write("#!/bin/sh\necho 1.19.5\n")
    os.chmod(p, 0o755)
if name == "brew":
    if args[:1] == ["outdated"]:
        key = "greedy_outdated" if "--greedy-auto-updates" in args else "outdated"
        out(json.dumps(C.get(key) or {"formulae": [], "casks": []}))
    elif args[:2] == ["list", "--cask"]:
        out("\n".join(C.get("casks_installed") or []) + "\n")
    elif args[:2] == ["info", "--cask"]:
        want = [a for a in args[3:]]
        out(json.dumps({"casks": [c for c in C.get("cask_info") or []
                                  if c.get("token") in want]}))
    elif args[:2] == ["bundle", "check"]:
        sys.exit(C.get("bundle_check", 0))
    elif args[:1] == ["--prefix"]:
        out(os.path.dirname(os.path.dirname(sys.argv[0])) + "\n")
elif name == "npm":
    if args[:3] == ["config", "get", "allow-scripts"]:
        out(C.get("allow_scripts", "null") + "\n")
    elif args[:2] == ["install", "-g"] and C.get("install_fixes"):
        opencode_works()
elif name == "node":
    if C.get("postinstall_fixes"):
        opencode_works()
elif name == "ps":
    out("\n".join(C.get("ps") or ["/sbin/launchd", "-zsh"]) + "\n")
elif name == "pgrep":
    pat = args[-1]
    said = (C.get("pgrep_lines") or {}).get(pat)
    if said:
        out(said + "\n"); sys.exit(0)
    hits = [h for h in C.get("pgrep_hits") or [] if h in pat]
    if hits:
        out("4242 %s\n" % hits[0]); sys.exit(0)
    sys.exit(1)
elif name == "pmset":
    out(C.get("pmset", "Now drawing from 'AC Power'\n"))
elif name == "ioreg":
    out('"HIDIdleTime" = %d\n' % int(C.get("idle_ns", 0)))
elif name == "curl":
    sys.exit(C.get("curl", 0))
elif name == "launchctl":
    have = loaded()
    if args[:1] == ["print"]:
        label = args[1].split("/")[-1]
        if label not in have:
            sys.exit(113)
        wd = (C.get("wd") or {}).get(label)
        out("%s = {\n\tworking directory = %s\n}\n" % (args[1], wd) if wd else "x = {}\n")
    elif args[:1] == ["bootstrap"]:
        label = os.path.basename(args[2])[:-6]
        if label not in have:
            have.append(label)
        save_loaded(have)
    elif args[:1] == ["bootout"]:
        label = args[1].split("/")[-1]
        save_loaded([l for l in have if l != label])
elif name == "defaults":
    tp = os.path.join(D, "terminal.plist")
    if args[:2] == ["export", "com.apple.Terminal"]:
        if not os.path.exists(tp):
            sys.exit(1)
        out(open(tp).read())
    elif args[:2] == ["import", "com.apple.Terminal"]:
        with open(tp, "w") as fh:
            fh.write(stdin)
    elif args[:1] == ["read"]:
        v = (C.get("defaults") or {}).get(args[1] + " " + args[2])
        if v is None:
            sys.exit(1)
        out(v + "\n")
elif name == "xcode-select":
    out(C.get("xcode_select", os.path.join(os.environ["UPKEEP_APPLICATIONS"], "Xcode.app",
                                           "Contents", "Developer")) + "\n")
elif name == "mas":
    out("\n".join(C.get("mas") or []) + "\n")
elif name == "code":
    if args[:1] == ["--list-extensions"]:
        out("\n".join(C.get("extensions") or []) + "\n")
elif name == "flutter":
    if args[:1] == ["config"]:
        d = os.path.join(os.environ["HOME"], ".config", "flutter")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "settings"), "w") as fh:
            json.dump({"android-sdk": args[2], "jdk-dir": args[4]}, fh)
    elif args[:2] == ["--version", "--machine"]:
        out(json.dumps({"frameworkVersion": C.get("flutter_version", "3.47.9")}))
    elif args[:1] == ["doctor"]:
        out(C.get("doctor", "[✓] Flutter (Channel stable, 3.47.9)\n"
                             "[✓] Android toolchain\n"))
elif name == "sdkmanager":
    if "--list" in args:
        out(C.get("sdk_list", ""))
sys.exit(0)
'''

SDK_LIST = """Installed packages:
  Path                 | Version | Description            | Location
  -------              | ------- | -------                | -------
  platform-tools       | 37.0.1  | Android SDK Platform-Tools | platform-tools
  platforms;android-36 | 2       | Android SDK Platform 36 | platforms/android-36

Available Packages:
  Path                       | Version | Description
  -------                    | ------- | -------
  build-tools;36.0.0         | 36.0.0  | Android SDK Build-Tools 36
  build-tools;37.0.0         | 37.0.0  | Android SDK Build-Tools 37
  build-tools;38.0.0-rc1     | 38.0.0 rc1 | Android SDK Build-Tools 38-rc1
  cmdline-tools;latest       | 23.0    | Android SDK Command-line Tools (latest)
  platforms;android-36       | 2       | Android SDK Platform 36
  platforms;android-36-ext18 | 1       | Android SDK Platform 36-ext18
  platforms;android-37.0     | 1       | Android SDK Platform 37.0
  platforms;android-Baklava  | 1       | Android SDK Platform Baklava
"""

DOCTOR_BAD = (u"[✓] Flutter (Channel stable, 3.47.9)\n"
              u"[!] Xcode - develop for iOS and macOS\n"
              u"    ✗ Xcode installation is incomplete; a full installation is necessary.\n"
              u"    • CocoaPods version 1.17.0\n"
              u"[✓] Chrome - develop for the web\n")

VSCODE = """{
  // keep this comment
  "editor.fontSize": 12,
  "window.zoomLevel": 1, // and this one
  "[json]": {"editor.tabSize": 2,},
}
"""


class Box(object):
    """One fake machine: HOME, a brew prefix whose bin/ holds every fake, a
    fixture repo carrying a copy of upkeep/, and the scenario file."""

    def __init__(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="upkeep-test-"))
        self.home = os.path.join(self.root, "home")
        self.prefix = os.path.join(self.root, "prefix")
        self.bin = os.path.join(self.prefix, "bin")
        self.apps = os.path.join(self.root, "Applications")
        self.fake = os.path.join(self.root, "fake")
        self.repo = os.path.join(self.root, "repo")
        self.root_status = os.path.join(self.root, "root-status.json")
        for d in (self.home, self.bin, self.apps, self.fake):
            os.makedirs(d)
        fake = os.path.join(self.root, "fake.py")
        with open(fake, "w") as fh:
            fh.write(FAKE)
        os.chmod(fake, 0o755)
        for p in PROGRAMS:
            os.symlink(fake, os.path.join(self.bin, p))
        # The machine's own directories follow the fakes, so a script that puts
        # them in front only when they are missing cannot reach the real ones.
        self.path = os.pathsep.join([self.bin, "/opt/homebrew/bin", "/usr/local/bin",
                                     os.path.join(self.home, ".local", "bin"),
                                     "/usr/bin", "/bin", "/usr/sbin", "/sbin"])
        for p in PROGRAMS:
            got = shutil.which(p, path=self.path)
            if got != os.path.join(self.bin, p):
                raise SystemExit("REFUSED: %s resolves to %s, not the fake" % (p, got))
        self.env = dict(os.environ, HOME=self.home, PATH=self.path, FAKE_DIR=self.fake,
                        UPKEEP_APPLICATIONS=self.apps, UPKEEP_ROOT_STATUS=self.root_status)
        for k in ("XPC_SERVICE_NAME", "DEEPSEEK_API_KEY", "UPKEEP_HOME",
                  "UPKEEP_STATE_DIR", "UPKEEP_REEXEC", "PYTHONPATH"):
            self.env.pop(k, None)
        self.make_repo(self.repo)
        self.scenario({})
        self.share = os.path.join(self.home, ".local", "share", "upkeep")
        self.state_dir = os.path.join(self.home, ".local", "state", "upkeep")

    def make_repo(self, root, version=None, hook=True):
        shutil.copytree(HERE, os.path.join(root, "upkeep"),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "opencode"))
        if version is not None:
            with open(os.path.join(root, "upkeep", "VERSION"), "w") as fh:
                fh.write("%d\n" % version)
        if hook:
            self.write(os.path.join(root, "upkeep.d", "hook"),
                       '#!/bin/bash\necho "$1 dry=$UPKEEP_DRY_RUN" >>"%s/hook.log"\n'
                       'f="%s/hook-$1.out"; [ -f "$f" ] && cat "$f"\n'
                       'c="%s/hook-$1.code"; [ -f "$c" ] && exit "$(cat "$c")"\nexit 0\n'
                       % (self.fake, self.fake, self.fake), 0o755)
        return root

    def write(self, path, text, mode=None):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        if mode:
            os.chmod(path, mode)

    def read(self, path):
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return ""

    def scenario(self, data):
        self.write(os.path.join(self.fake, "scenario.json"), json.dumps(data))

    def calls(self, prog=None):
        out = []
        for line in self.read(os.path.join(self.fake, "calls.jsonl")).splitlines():
            rec = json.loads(line)
            if prog is None or rec["prog"] == prog:
                out.append(rec)
        return out

    def argv(self, prog):
        return [" ".join(c["args"]) for c in self.calls(prog)]

    def clear_calls(self):
        for name in ("calls.jsonl", "hook.log"):
            try:
                os.remove(os.path.join(self.fake, name))
            except OSError:
                pass

    def loaded(self):
        try:
            return json.loads(self.read(os.path.join(self.fake, "loaded.json")))
        except ValueError:
            return []

    def set_loaded(self, labels):
        self.write(os.path.join(self.fake, "loaded.json"), json.dumps(labels))

    def upkeep(self, *args, script=None, env=None):
        e = dict(self.env)
        e.update(env or {})
        p = subprocess.run([PY, script or os.path.join(self.share, "upkeep.py")] + list(args),
                           env=e, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True, timeout=120, cwd=self.root)
        return p.returncode, p.stdout

    def install(self, repo=None):
        return self.upkeep("install", "--repo", repo or self.repo,
                           script=os.path.join(repo or self.repo, "upkeep", "upkeep.py"))

    def state(self):
        try:
            return json.loads(self.read(os.path.join(self.state_dir, "state.json")))
        except ValueError:
            return {}

    def log(self):
        return self.read(os.path.join(self.state_dir, "upkeep.log"))

    def green(self):
        """A machine with nothing wrong: Xcode, Android Studio's JBR, the root
        helper, App Store updates on, a key, flutter configured."""
        os.makedirs(os.path.join(self.apps, "Xcode.app"), exist_ok=True)
        os.makedirs(U_jbr(self.apps), exist_ok=True)
        self.write(self.root_status, json.dumps({"at": U.stamp(), "result": "ok"}))
        self.write(os.path.join(self.home, ".config", "api-keys", "deepseek_key"),
                   "sk-test-key\n", 0o600)
        sdk = os.path.join(self.home, "Library", "Android", "sdk")
        self.write(os.path.join(self.home, ".config", "flutter", "settings"),
                   json.dumps({"android-sdk": sdk, "jdk-dir": U_jbr(self.apps)}))
        self.write(os.path.join(self.bin, "opencode"), "#!/bin/sh\necho 1.19.5\n", 0o755)

    def done(self):
        shutil.rmtree(self.root, ignore_errors=True)


def U_jbr(apps):
    return os.path.join(apps, "Android Studio.app", "Contents", "jbr", "Contents", "Home")


class Case(unittest.TestCase):
    def setUp(self):
        self.b = Box()

    def tearDown(self):
        self.b.done()


# ------------------------------------------------------------------ JSONC

class JSONC(unittest.TestCase):
    def test_load_comments_and_trailing_commas(self):
        self.assertEqual(U.jsonc_load(VSCODE), {"editor.fontSize": 12, "window.zoomLevel": 1,
                                                "[json]": {"editor.tabSize": 2}})
        self.assertEqual(U.jsonc_load('{"a": "// not a comment", "b": "x\\"/*y"}'),
                         {"a": "// not a comment", "b": 'x"/*y'})

    def test_set_keeps_comments_order_and_other_keys(self):
        new = U.jsonc_set(VSCODE, "editor.fontSize", 24)
        self.assertIn("// keep this comment", new)
        self.assertIn("// and this one", new)
        self.assertEqual(U.jsonc_load(new)["editor.fontSize"], 24)
        self.assertEqual(U.jsonc_load(new)["[json]"], {"editor.tabSize": 2})
        added = U.jsonc_set(new, "editor.fontLigatures", False)
        data = U.jsonc_load(added)
        self.assertIs(data["editor.fontLigatures"], False)
        self.assertEqual(list(data)[-1], "editor.fontLigatures")
        self.assertTrue(added.rstrip().endswith("}"))
        self.assertIn('  "editor.fontLigatures": false,', added)

    def test_set_in_every_shape(self):
        self.assertEqual(U.jsonc_load(U.jsonc_set("{}", "k", 1)), {"k": 1})
        self.assertEqual(U.jsonc_set('{"a":1}', "k", "v"), '{"a":1, "k": "v"}')
        four = U.jsonc_set('{\n    "a": 1 // n\n}\n', "k", True)
        self.assertEqual(four, '{\n    "a": 1, // n\n    "k": true\n}\n')
        self.assertEqual(U.jsonc_load(U.jsonc_set('{"p": {"x": 1}}', "p", {"*": "allow"})),
                         {"p": {"*": "allow"}})

    def test_bad_input_raises_and_writes_nothing(self):
        for bad in ('{"a": 1', '{"a": /* open', "[1, 2]", '{"a": tru e}', ""):
            with self.assertRaises(ValueError):
                U.jsonc_set(bad, "k", 1)


# ------------------------------------------------------------------- gate

class Gate(unittest.TestCase):
    def setUp(self):
        self.saved = dict((n, getattr(U, n)) for n in
                          ("now", "battery", "idle_seconds", "network_ok"))
        self.clock = datetime(2026, 11, 2, 4, 30)
        U.now = lambda: self.clock
        U.battery = lambda: (False, True, None)
        U.idle_seconds = lambda: 0
        U.network_ok = lambda: True

    def tearDown(self):
        for n, f in self.saved.items():
            setattr(U, n, f)

    def at(self, hour):
        self.clock = self.clock.replace(hour=hour)

    def test_in_window_runs_and_twenty_hours_apart(self):
        self.assertTrue(U.gate({})[0])
        recent = U.stamp(self.clock - timedelta(hours=19))
        go, why = U.gate({"last_attempt": recent})
        self.assertFalse(go)
        self.assertIn("every 20h", why)

    def test_desktop_never_outside_window(self):
        self.at(14)
        go, why = U.gate({"last_success": "2020-01-01T00:00:00"})
        self.assertFalse(go)
        self.assertIn("no battery", why)

    def test_laptop_rule(self):
        self.at(14)
        old = U.stamp(self.clock - timedelta(hours=50))
        U.battery = lambda: (True, True, 90)
        self.assertFalse(U.gate({"last_success": U.stamp(self.clock - timedelta(hours=30))})[0])
        U.idle_seconds = lambda: 60
        self.assertEqual(U.gate({"last_success": old}), (False, "overdue, but in use"))
        U.idle_seconds = lambda: 1500
        self.assertTrue(U.gate({"last_success": old})[0])
        U.battery = lambda: (True, False, 90)
        self.assertEqual(U.gate({"last_success": old}), (False, "overdue, but on battery"))

    def test_battery_floor_and_network(self):
        U.battery = lambda: (True, False, 30)
        self.assertIn("on battery at 30%", U.gate({})[1])
        U.battery = lambda: (True, False, 80)
        self.assertTrue(U.gate({})[0])
        U.network_ok = lambda: False
        self.assertEqual(U.gate({}), (False, "formulae.brew.sh unreachable"))


class Parsers(unittest.TestCase):
    def test_sdk_list_and_newest_stable(self):
        have, avail = U.sdk_packages(SDK_LIST)
        self.assertEqual(have, {"platform-tools", "platforms;android-36"})
        allp = have | avail
        self.assertEqual(U.newest(allp, r"^platforms;android-(\d+)(?:\.(\d+))?$"),
                         "platforms;android-37.0")
        self.assertEqual(U.newest(allp, r"^build-tools;(\d+)\.(\d+)\.(\d+)$"),
                         "build-tools;37.0.0")

    def test_flutter_doctor_lines(self):
        self.assertEqual(U.flutter_doctor_problems(DOCTOR_BAD), [
            u"flutter doctor: [!] Xcode - develop for iOS and macOS: Xcode installation is "
            u"incomplete; a full installation is necessary."])
        self.assertEqual(U.flutter_doctor_problems(u"[✓] Flutter\n"), [])


# ---------------------------------------------------------------- install

class Install(Case):
    def test_install_copies_registers_links_and_loads(self):
        b = self.b
        code, out = b.install()
        self.assertEqual(code, 0, out)
        self.assertEqual(U.version_of(b.share), U.version_of(HERE))
        self.assertEqual(json.loads(b.read(os.path.join(b.home, ".config", "upkeep",
                                                        "repos.json"))), [b.repo])
        link = os.path.join(b.home, ".local", "bin", "upkeep")
        self.assertEqual(os.readlink(link), os.path.join(b.share, "upkeep.py"))
        self.assertEqual(sorted(b.loaded()), [U.DOCTOR_LABEL, U.LABEL])
        plist = os.path.join(b.home, "Library", "LaunchAgents", U.LABEL + ".plist")
        with open(plist, "rb") as fh:
            job = plistlib.load(fh)
        self.assertEqual(job["ProgramArguments"],
                         ["/usr/bin/python3", os.path.join(b.share, "upkeep.py"), "run"])
        self.assertNotIn("@", b.read(plist))
        self.assertTrue(job["EnvironmentVariables"]["PATH"].startswith(
            os.path.join(b.home, ".local", "bin") + ":" + b.bin))
        zp = b.read(os.path.join(b.home, ".zprofile"))
        self.assertIn(U.MANAGED_BEGIN, zp)
        self.assertIn('export ANDROID_HOME="$HOME/Library/Android/sdk"', zp)
        self.assertIn("opencode/shell.zsh", zp)

    def test_second_install_changes_nothing(self):
        b = self.b
        b.install()
        b.clear_calls()
        mtime = os.path.getmtime(os.path.join(b.home, ".zprofile"))
        code, out = b.install()
        self.assertEqual(code, 0, out)
        self.assertFalse([a for a in b.argv("launchctl") if a.startswith("bootstrap")])
        self.assertEqual(os.path.getmtime(os.path.join(b.home, ".zprofile")), mtime)

    def test_zprofile_block_replaced_in_place(self):
        b = self.b
        zp = os.path.join(b.home, ".zprofile")
        b.write(zp, "export A=1\n%s\nold stuff\n%s\nexport B=2\n" % (U.MANAGED_BEGIN,
                                                                     U.MANAGED_END))
        b.install()
        text = b.read(zp)
        self.assertTrue(text.startswith("export A=1\n" + U.MANAGED_BEGIN))
        self.assertTrue(text.endswith(U.MANAGED_END + "\nexport B=2\n"))
        self.assertNotIn("old stuff", text)
        self.assertEqual(text.count(U.MANAGED_BEGIN), 1)

    def test_retires_atlas_brew_upgrade(self):
        b = self.b
        old = os.path.join(b.home, "Library", "LaunchAgents", "atlas.brew-upgrade.plist")
        b.write(old, "<plist/>")
        b.set_loaded(["atlas.brew-upgrade"])
        code, out = b.install()
        self.assertIn("atlas.brew-upgrade retired", out)
        self.assertFalse(os.path.exists(old))
        self.assertNotIn("atlas.brew-upgrade", b.loaded())

    def test_lower_version_never_overwrites_and_gone_repo_dropped(self):
        b = self.b
        high = b.make_repo(os.path.join(b.root, "high"), version=900)
        low = b.make_repo(os.path.join(b.root, "low"), version=1)
        b.install(high)
        code, out = b.install(low)
        self.assertEqual(U.version_of(b.share), 900)
        self.assertIn("stays", out)
        shutil.rmtree(high)
        code, out = b.upkeep("status")
        self.assertEqual(json.loads(b.read(os.path.join(b.home, ".config", "upkeep",
                                                        "repos.json"))), [low])

    def test_parity_layer_agent_is_loaded_when_present(self):
        b = self.b
        oc = os.path.join(b.repo, "upkeep", "opencode")
        b.write(os.path.join(oc, "launchd", "com.mikeyferguson.opencode-serve.plist"),
                plistlib.dumps({"Label": "com.mikeyferguson.opencode-serve",
                                "ProgramArguments": ["@PREFIX@/bin/opencode", "serve"],
                                "KeepAlive": True}).decode())
        b.install()
        self.assertIn("com.mikeyferguson.opencode-serve", b.loaded())
        with open(os.path.join(b.home, "Library", "LaunchAgents",
                               "com.mikeyferguson.opencode-serve.plist"), "rb") as fh:
            self.assertEqual(plistlib.load(fh)["ProgramArguments"][0],
                             os.path.join(b.prefix, "bin", "opencode"))


# -------------------------------------------------------------------- run

def full_scenario(b, **extra):
    s = {"outdated": {"formulae": [
        {"name": "jq", "installed_versions": ["1.7"], "current_version": "1.8"},
        {"name": "pinme", "installed_versions": ["1"], "current_version": "2", "pinned": True},
        {"name": "guarded", "installed_versions": ["1"], "current_version": "2"}],
        "casks": [{"name": "iterm2", "installed_versions": ["3"], "current_version": "4"},
                  {"name": "slack", "installed_versions": ["1"], "current_version": "2"}]},
        "casks_installed": ["flutter", "iterm2", "slack"],
        "greedy_outdated": {"formulae": [], "casks": [
            {"name": "flutter", "installed_versions": ["3.47.8"],
             "current_version": "3.47.9"}]},
        "cask_info": [{"token": "slack", "artifacts": [{"app": ["Slack.app"]}]},
                      {"token": "iterm2", "artifacts": [{"app": ["iTerm.app"]}]}],
        "pgrep_hits": ["Slack"], "sdk_list": SDK_LIST, "bundle_check": 1,
        "allow_scripts": "esbuild", "doctor": DOCTOR_BAD, "mas": ["497799835 Xcode (27.3)"],
        "defaults": {"/Library/Preferences/com.apple.commerce AutoUpdate": "1"}}
    s.update(extra)
    b.scenario(s)


class FullRun(Case):
    def setUp(self):
        Case.setUp(self)
        b = self.b
        b.green()
        b.install()
        b.write(os.path.join(b.fake, "hook-protected-casks.out"), "guarded\n")
        extra = os.path.join(b.root, "Extra.Brewfile")
        b.write(extra, 'brew "jq"  # dup\nbrew "texlive"\ntap "x/y"\n')
        b.write(os.path.join(b.fake, "hook-brewfiles.out"), extra + "\n")
        b.write(os.path.join(b.fake, "hook-status.out"), "repo thing is wrong\n")
        b.write(os.path.join(b.home, "Library", "Application Support", "Code", "User",
                             "settings.json"), VSCODE)
        full_scenario(b)
        b.clear_calls()

    def test_phases_in_order_with_holds(self):
        b = self.b
        code, out = b.upkeep("run", "--force")
        self.assertEqual(code, 0, out)
        brew = b.argv("brew")
        self.assertEqual(brew[0], "update")
        self.assertIn("upgrade --formula jq", brew)
        self.assertFalse([a for a in brew if "pinme" in a or "guarded" in a and "upgrade" in a])
        self.assertIn("upgrade --cask iterm2", brew)
        self.assertFalse([a for a in brew if a.startswith("upgrade") and "slack" in a])
        self.assertIn("upgrade --cask --greedy-auto-updates flutter", brew)
        self.assertTrue(any(a.startswith("bundle install --no-upgrade --file=") for a in brew))
        self.assertFalse([a for a in brew if "--cleanup" in a or "autoremove" in a])
        self.assertEqual(brew[-1], "cleanup --prune=7")
        st = b.state()
        self.assertEqual(sorted(st["held"]), ["guarded", "pinme"])
        self.assertEqual(st["cask_defers"], {"slack": 1})
        union = b.read(os.path.join(b.state_dir, "Brewfile.all"))
        self.assertEqual(union.count('brew "jq"'), 1)
        self.assertLess(union.index('tap "x/y"'), union.index('brew "python"'))
        self.assertIn('brew "texlive"', union)
        npm = b.argv("npm")
        self.assertIn("config set allow-scripts=esbuild,opencode-ai --location=user", npm)
        self.assertIn("update -g", npm)
        self.assertLess(npm.index("config set allow-scripts=esbuild,opencode-ai "
                                  "--location=user"), npm.index("update -g"))
        self.assertEqual(b.read(os.path.join(b.fake, "hook.log")).split(),
                         ["protected-casks", "dry=", "brewfiles", "dry=", "after-brew",
                          "dry=", "toolchain", "dry=", "status", "dry="])

    def test_android_flutter_xcode_appearance(self):
        b = self.b
        b.upkeep("run", "--force")
        sdk = os.path.join(b.home, "Library", "Android", "sdk")
        sdkm = b.argv("sdkmanager")
        self.assertEqual(sdkm[0], "--sdk_root=%s --update" % sdk)
        self.assertIn("--sdk_root=%s cmdline-tools;latest platforms;android-37.0 "
                      "build-tools;37.0.0" % sdk, sdkm)
        lic = [c for c in b.calls("sdkmanager") if "--licenses" in c["args"]]
        self.assertTrue(lic and all(c["stdin"] > 0 for c in lic))
        flutter = b.argv("flutter")
        self.assertIn("precache", flutter)
        self.assertIn("doctor -v", flutter)
        st = b.state()
        self.assertIn(u"flutter doctor: [!] Xcode - develop for iOS and macOS: Xcode "
                      u"installation is incomplete; a full installation is necessary.",
                      st["problems"])
        self.assertEqual(st["flutter_version"], "3.47.9")
        self.assertEqual(st["app_store_outdated"], ["497799835 Xcode (27.3)"])
        self.assertEqual(st["hooks"], {b.repo: ["repo thing is wrong"]})
        settings = b.read(os.path.join(b.home, "Library", "Application Support", "Code",
                                       "User", "settings.json"))
        data = U.jsonc_load(settings)
        self.assertEqual(data["editor.fontSize"], 24)
        self.assertIs(data["editor.fontLigatures"], False)
        self.assertEqual(data["window.zoomLevel"], 1)
        self.assertIn("// keep this comment", settings)
        self.assertEqual(data["markdown.preview.fontFamily"],
                         "OpenDyslexic, -apple-system, sans-serif")
        prefs = plistlib.loads(b.read(os.path.join(b.fake, "terminal.plist")).encode())
        self.assertEqual(prefs["Default Window Settings"], "Comic Mono 24pt")
        self.assertEqual(prefs["Startup Window Settings"], "Comic Mono 24pt")
        with open(os.path.join(HERE, "appearance", "Comic Mono 24pt.terminal"), "rb") as fh:
            self.assertEqual(prefs["Window Settings"]["Comic Mono 24pt"], plistlib.load(fh))
        self.assertIn("--install-extension Dart-Code.flutter", b.argv("code"))

    def test_second_run_is_quiet(self):
        b = self.b
        b.upkeep("run", "--force")
        first = len(b.calls("osascript"))
        self.assertGreater(first, 0)
        settings = os.path.join(b.home, "Library", "Application Support", "Code", "User",
                                "settings.json")
        before = b.read(settings)
        b.clear_calls()
        full_scenario(b, extensions=["dart-code.flutter"],
                      doctor=u"[✓] Flutter\n", bundle_check=0)
        b.write(os.path.join(b.fake, "hook-status.out"), "repo thing is wrong\n")
        b.upkeep("run", "--force")
        self.assertEqual(b.calls("osascript"), [], "a line already heard is not repeated")
        self.assertFalse([a for a in b.argv("defaults") if a.startswith("import")])
        self.assertEqual(b.read(settings), before)
        self.assertFalse([a for a in b.argv("code") if "--install" in a])
        self.assertFalse([a for a in b.argv("flutter") if a == "precache"])
        self.assertFalse([a for a in b.argv("brew") if a.startswith("bundle install")])
        self.assertEqual(b.state()["cask_defers"], {"slack": 2})
        b.upkeep("run", "--force")
        self.assertIn("slack", b.state()["held"], "held after three running ticks")

    def test_status_reports_and_exits_one(self):
        b = self.b
        b.upkeep("run", "--force")
        code, out = b.upkeep("status")
        self.assertEqual(code, 1, out)
        self.assertIn("PROBLEM   repo: repo thing is wrong", out)
        self.assertIn("PROBLEM   upkeep: pinme 1 -> 2 is held", out)
        self.assertIn("APP STORE 497799835 Xcode (27.3)", out)

    def test_failing_step_is_recorded_and_the_rest_runs(self):
        b = self.b
        full_scenario(b, exit={"brew upgrade --formula": 1})
        b.write(os.path.join(b.fake, "hook-toolchain.code"), "3")
        b.upkeep("run", "--force")
        st = b.state()
        self.assertEqual(st["last_result"], "partial")
        self.assertIn("formulae", st["failed"])
        self.assertIn("hook repo toolchain", st["failed"])
        self.assertIn("cleanup --prune=7", b.argv("brew"))
        self.assertNotIn("last_success", st)

    def test_dry_run_changes_nothing(self):
        b = self.b
        code, out = b.upkeep("run", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(os.path.join(b.state_dir, "state.json")))
        brew = b.argv("brew")
        self.assertNotIn("update", brew)
        self.assertFalse([a for a in brew if a.startswith(("upgrade", "bundle install",
                                                           "cleanup"))])
        self.assertNotIn("update -g", b.argv("npm"))
        self.assertFalse([a for a in b.argv("defaults") if a.startswith("import")])
        self.assertIn("would run", out)
        self.assertIn("dry=1", b.read(os.path.join(b.fake, "hook.log")))

    def test_fonts_copied_by_hand_move_aside(self):
        b = self.b
        fonts = os.path.join(b.home, "Library", "Fonts")
        b.write(os.path.join(fonts, "ComicMono.ttf"), "hand copy")
        full_scenario(b, cask_info=[{"token": "font-comic-mono", "artifacts": [
            {"font": ["comic-mono-font-master/ComicMono.ttf"],
             "target": os.path.join(fonts, "ComicMono.ttf")}]}])
        b.upkeep("run", "--force")
        self.assertFalse(os.path.exists(os.path.join(fonts, "ComicMono.ttf")))
        self.assertEqual(b.read(os.path.join(fonts, ".before-upkeep", "ComicMono.ttf")),
                         "hand copy")
        brew = b.argv("brew")
        self.assertLess(brew.index("install --cask --force font-comic-mono"),
                        [i for i, a in enumerate(brew) if a.startswith("bundle install")][0])

    def test_fonts_come_back_when_the_cask_fails(self):
        b = self.b
        fonts = os.path.join(b.home, "Library", "Fonts")
        b.write(os.path.join(fonts, "ComicMono.ttf"), "hand copy")
        full_scenario(b, cask_info=[{"token": "font-comic-mono", "artifacts": [
            {"font": ["comic-mono-font-master/ComicMono.ttf"],
             "target": os.path.join(fonts, "ComicMono.ttf")}]}],
            exit={"brew install --cask --force font-comic-mono": 1})
        b.upkeep("run", "--force")
        self.assertEqual(b.read(os.path.join(fonts, "ComicMono.ttf")), "hand copy")
        self.assertFalse(os.path.exists(os.path.join(fonts, ".before-upkeep",
                                                     "ComicMono.ttf")))
        self.assertIn("cask font-comic-mono", b.state()["failed"])

    def test_hand_installed_app_is_left_out_of_the_bundle(self):
        b = self.b
        os.makedirs(os.path.join(b.apps, "Visual Studio Code.app"))
        full_scenario(b, cask_info=[{"token": "visual-studio-code", "artifacts": [
            {"app": ["Visual Studio Code.app"]}]}])
        b.upkeep("run", "--force")
        union = b.read(os.path.join(b.state_dir, "Brewfile.all"))
        self.assertNotIn("visual-studio-code", union)
        self.assertIn('cask "flutter"', union)
        self.assertIn("installed by hand; brew bundle leaves it", b.log())
        self.assertFalse([a for a in b.argv("brew") if a.startswith(("install", "upgrade"))
                          and "visual-studio-code" in a])

    def test_gate_refusal_rechecks_problems_report_only(self):
        b = self.b
        b.upkeep("run", "--force")
        st = b.state()
        st["checked_at"] = U.stamp(datetime.now() - timedelta(hours=2))
        b.write(os.path.join(b.state_dir, "state.json"), json.dumps(st))
        b.clear_calls()
        full_scenario(b, doctor=u"[✓] Flutter\n")
        b.write(os.path.join(b.fake, "hook-status.out"), "")
        b.upkeep("run")
        self.assertFalse([a for a in b.argv("brew") if a.startswith(("update", "upgrade"))])
        self.assertFalse([a for a in b.argv("sdkmanager") if "--update" in a])
        self.assertIn("doctor -v", b.argv("flutter"))
        st = b.state()
        self.assertFalse([p for p in st["problems"] if p.startswith("flutter doctor")])
        self.assertEqual(st["hooks"], {b.repo: []})

    def test_busy_skips_the_tick(self):
        b = self.b
        full_scenario(b, pgrep_lines={"brew[-_]upgrade": "77 /usr/bin/python3 "
                                      "/x/Open-Code-Doctor/brew_upgrade.py"})
        b.upkeep("run", "--force")
        self.assertFalse([a for a in b.argv("brew") if a.startswith(("update", "upgrade"))])
        self.assertIn("skipped: another brew upgrader is running", b.log())
        b.clear_calls()
        full_scenario(b, pgrep_lines={"brew[-_]upgrade": "78 /usr/bin/python3 "
                                      "/a/Atlas/scripts/brew-upgrade.py status",
                                      "/Library/Homebrew/brew\\.(rb|sh)": ""})
        b.upkeep("run", "--force")
        self.assertIn("update", b.argv("brew"), "Atlas's hook is no upgrader")
        b.clear_calls()
        full_scenario(b, pgrep_lines={"brew[-_]upgrade": "80 /Applications/Xcode.app/"
                                      "Contents/Developer/Library/Frameworks/Python3."
                                      "framework/Versions/3.9/Resources/Python.app/"
                                      "Contents/MacOS/Python pg/brew_upgrade.py"})
        b.upkeep("run", "--force")
        self.assertNotIn("update", b.argv("brew"), "Xcode's Python, capital P")
        b.clear_calls()
        full_scenario(b, pgrep_lines={"/Library/Homebrew/brew\\.(rb|sh)":
                                      "79 /opt/homebrew/Library/Homebrew/brew.rb"})
        b.upkeep("run", "--force")
        self.assertNotIn("update", b.argv("brew"))
        self.assertIn("skipped: a brew is running", b.log())

    def test_off_and_on(self):
        b = self.b
        b.upkeep("off")
        b.clear_calls()
        code, _ = b.upkeep("run", "--force")
        self.assertEqual(code, 0)
        self.assertEqual(b.calls(), [])
        b.upkeep("doctor")
        self.assertEqual(b.calls(), [])
        b.upkeep("on")
        b.upkeep("run", "--force")
        self.assertIn("update", b.argv("brew"))


class Legacy(Case):
    def setUp(self):
        Case.setUp(self)
        b = self.b
        b.green()
        b.install()
        self.wd = os.path.join(b.root, "Open-Code-Doctor")
        os.makedirs(os.path.join(self.wd, "state"))
        b.set_loaded(b.loaded() + [U.LEGACY_BREW])
        full_scenario(b, wd={U.LEGACY_BREW: self.wd})
        b.clear_calls()

    def legacy_success(self, hours):
        self.b.write(os.path.join(self.wd, "state", "brew_upgrade.json"), json.dumps(
            {"last_success": U.stamp(datetime.now() - timedelta(hours=hours))}))

    def test_skip_decision(self):
        b = self.b
        restore = U_configure(b)
        try:
            self.legacy_success(3)
            legacy = U.legacy_brew()
            self.assertEqual(legacy["dir"], self.wd)
            self.assertIn("succeeded", U.legacy_skip(legacy))
            self.legacy_success(30)
            self.assertIsNone(U.legacy_skip(U.legacy_brew()))
            b.write(os.path.join(self.wd, "state", "brew_upgrade.lock"), "1 now")
            self.assertIn("lock", U.legacy_skip(U.legacy_brew()))
        finally:
            restore()

    def test_forced_run_with_fresh_lock_leaves_brew_alone(self):
        b = self.b
        b.write(os.path.join(self.wd, "state", "brew_upgrade.lock"), "1 now")
        b.upkeep("run", "--force")
        st = b.state()
        self.assertTrue(st["phases"]["brew"].startswith("skipped"), st["phases"])
        self.assertEqual(st["brew_by"], U.LEGACY_BREW)
        self.assertFalse([a for a in b.argv("brew") if a.startswith(("update", "upgrade",
                                                                     "bundle", "cleanup"))])
        self.assertNotIn("update -g", b.argv("npm"))
        self.assertIn("doctor -v", b.argv("flutter"))

    def test_forced_run_leaves_brew_to_a_recent_legacy_job(self):
        b = self.b
        self.legacy_success(3)
        b.upkeep("run", "--force")
        st = b.state()
        self.assertTrue(st["phases"]["brew"].startswith("skipped"), st["phases"])
        self.assertEqual(st["brew_by"], U.LEGACY_BREW)
        self.assertFalse([a for a in b.argv("brew") if a.startswith(("update", "upgrade",
                                                                     "bundle", "cleanup"))])

    def test_legacy_doctor_makes_doctor_a_noop(self):
        b = self.b
        b.set_loaded(b.loaded() + [U.LEGACY_DOCTOR])
        os.remove(os.path.join(b.bin, "opencode"))
        b.upkeep("doctor")
        self.assertEqual(b.calls("npm"), [])


def U_configure(b):
    """Point the imported module at the box, in process; the restore."""
    saved = dict(os.environ)
    os.environ.update({"PATH": b.path, "FAKE_DIR": b.fake, "HOME": b.home,
                       "UPKEEP_APPLICATIONS": b.apps})
    U.configure(dict(b.env))

    def restore():
        os.environ.clear()
        os.environ.update(saved)
        U.configure()
    return restore


# ----------------------------------------------------------------- doctor

class Doctor(Case):
    def setUp(self):
        Case.setUp(self)
        b = self.b
        b.install()
        self.pkg = os.path.join(b.prefix, "lib", "node_modules", "opencode-ai")
        b.write(os.path.join(self.pkg, "postinstall.mjs"), "// links the binary\n")
        self.cfg = os.path.join(b.home, ".config", "opencode", "opencode.jsonc")
        b.clear_calls()

    def placeholder(self):
        b = self.b
        b.write(os.path.join(b.bin, "opencode"),
                "echo 'opencode: postinstall script was not run'\n", 0o755)

    def test_placeholder_repaired_by_postinstall(self):
        b = self.b
        self.placeholder()
        b.scenario({"postinstall_fixes": True})
        b.upkeep("doctor")
        log = b.log()
        self.assertIn("opencode binary broken and not running; repairing with its "
                      "postinstall (npm's placeholder: postinstall script was not run)", log)
        self.assertNotIn("reinstalling", log)
        self.assertEqual(b.argv("node"), [os.path.join(self.pkg, "postinstall.mjs")])

    def test_dead_binary_reinstalled(self):
        b = self.b
        b.write(os.path.join(b.bin, "opencode"), "#!/bin/sh\nexit 3\n", 0o755)
        b.scenario({"install_fixes": True})
        b.upkeep("doctor")
        self.assertIn("opencode binary broken and not running; reinstalling (exit 3: "
                      "no output)", b.log())
        self.assertEqual(b.argv("npm")[-4:], [
            "config set ignore-scripts false", "uninstall -g opencode-ai",
            "cache clean --force",
            "install -g opencode-ai --foreground-scripts --allow-scripts=opencode-ai"])
        self.assertEqual(json.loads(b.read(os.path.join(b.state_dir, "doctor.json")))
                         ["problems"], [])

    def test_running_opencode_is_left_alone(self):
        b = self.b
        self.placeholder()
        b.scenario({"ps": ["/opt/homebrew/lib/node_modules/opencode-ai/bin/opencode"]})
        b.upkeep("doctor")
        self.assertEqual(b.calls("npm"), [])
        self.assertEqual(b.calls("node"), [])

    def test_upgrade_lock_holds_the_doctor(self):
        b = self.b
        self.placeholder()
        import fcntl
        os.makedirs(b.state_dir, exist_ok=True)
        fd = os.open(os.path.join(b.state_dir, "upkeep.lock"), os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            b.upkeep("doctor")
        finally:
            os.close(fd)
        self.assertEqual(b.calls("npm"), [])
        self.assertFalse(os.path.exists(self.cfg))

    def test_jsonc_config_kept_and_permission_set(self):
        b = self.b
        b.write(os.path.join(b.bin, "opencode"), "#!/bin/sh\necho 1\n", 0o755)
        b.write(self.cfg, '{\n  // DeepSeek is the model\n  "model": "deepseek/deepseek-flash",\n'
                '  "provider": {"deepseek": {},},\n}\n')
        b.upkeep("doctor")
        text = b.read(self.cfg)
        self.assertIn("// DeepSeek is the model", text)
        data = U.jsonc_load(text)
        self.assertEqual(data["model"], "deepseek/deepseek-flash")
        self.assertEqual(data["permission"], "allow")
        self.assertEqual(data["$schema"], U.OPENCODE_SCHEMA)

    def test_permission_object_kept(self):
        b = self.b
        b.write(os.path.join(b.bin, "opencode"), "#!/bin/sh\necho 1\n", 0o755)
        body = ('{"$schema": "x", "permission": {"*": "allow", "doom_loop": "allow"}}\n')
        b.write(self.cfg, body)
        b.upkeep("doctor")
        self.assertEqual(b.read(self.cfg), body)
        b.write(self.cfg, '{"$schema": "x", "permission": {"*": "ask", "bash": "allow"}}\n')
        b.upkeep("doctor")
        self.assertEqual(U.jsonc_load(b.read(self.cfg))["permission"],
                         {"*": "allow", "bash": "allow"})

    def test_unparseable_config_left_alone_and_named(self):
        b = self.b
        b.write(os.path.join(b.bin, "opencode"), "#!/bin/sh\necho 1\n", 0o755)
        body = '{\n  "model": "deepseek/deepseek-flash",\n  "provider": {\n'
        b.write(self.cfg, body)
        b.upkeep("doctor")
        self.assertEqual(b.read(self.cfg), body, "never replaced with a partial dict")
        probs = json.loads(b.read(os.path.join(b.state_dir, "doctor.json")))["problems"]
        self.assertTrue(probs and "does not parse" in probs[0], probs)
        code, out = b.upkeep("status")
        self.assertIn("opencode.jsonc does not parse", out)

    def test_coder_matches_parity_template_and_aliases_go(self):
        b = self.b
        b.write(os.path.join(b.bin, "opencode"), "#!/bin/sh\necho 1\n", 0o755)
        b.write(os.path.join(b.share, "opencode", "coder"), "#!/bin/bash\nexec oc-new\n")
        b.write(os.path.join(b.home, "bin", "coder"), "#!/bin/bash\nexec opencode --auto\n")
        b.write(os.path.join(b.home, ".zshrc"), "export X=1\nalias coder='npx opencode'\n")
        b.upkeep("doctor")
        self.assertEqual(b.read(os.path.join(b.home, "bin", "coder")),
                         "#!/bin/bash\nexec oc-new\n")
        self.assertTrue(os.access(os.path.join(b.home, "bin", "coder"), os.X_OK))
        self.assertEqual(b.read(os.path.join(b.home, ".zshrc")), "export X=1\n")

    def test_coder_without_parity_layer_uses_builtin(self):
        b = self.b
        b.write(os.path.join(b.bin, "opencode"), "#!/bin/sh\necho 1\n", 0o755)
        b.upkeep("doctor")
        self.assertEqual(b.read(os.path.join(b.home, "bin", "coder")), U.CODER_TEMPLATE)

    def test_allow_scripts_already_named_is_left(self):
        b = self.b
        b.write(os.path.join(b.bin, "opencode"), "#!/bin/sh\necho 1\n", 0o755)
        b.scenario({"allow_scripts": "opencode-ai@*,esbuild"})
        b.upkeep("doctor")
        self.assertFalse([a for a in b.argv("npm") if a.startswith("config set")])


# -------------------------------------------------------------- the key

class Key(Case):
    def setUp(self):
        Case.setUp(self)
        b = self.b
        b.green()
        os.remove(os.path.join(b.home, ".config", "api-keys", "deepseek_key"))
        b.install()
        full_scenario(b, outdated={"formulae": [], "casks": []})
        self.keys_env = os.path.join(b.home, ".config", "tutor-board", "keys.env")
        self.auth = os.path.join(b.home, ".local", "share", "opencode", "auth.json")
        self.file = os.path.join(b.home, ".config", "api-keys", "deepseek_key")

    def test_keys_env_spreads_to_the_others(self):
        b = self.b
        b.write(self.keys_env, "OTHER=1\nDEEPSEEK_API_KEY=sk-from-atlas\n")
        b.write(self.auth, json.dumps({"openrouter": {"type": "api", "key": "or"}}))
        b.upkeep("run", "--force")
        self.assertEqual(b.read(self.file), "sk-from-atlas\n")
        self.assertEqual(oct(os.stat(self.file).st_mode & 0o777), "0o600")
        auth = json.loads(b.read(self.auth))
        self.assertEqual(auth["deepseek"], {"type": "api", "key": "sk-from-atlas"})
        self.assertEqual(auth["openrouter"]["key"], "or")
        self.assertNotIn("sk-from-atlas", b.log())
        self.assertNotIn("sk-from-atlas", b.read(os.path.join(b.state_dir, "state.json")))

    def test_env_wins_and_rewrites_keys_env(self):
        b = self.b
        b.write(self.file, "sk-old\n")
        b.write(self.keys_env, "A=1\nexport DEEPSEEK_API_KEY='sk-old'\nB=2\n")
        b.upkeep("run", "--force", env={"DEEPSEEK_API_KEY": "sk-new"})
        self.assertEqual(b.read(self.file), "sk-new\n")
        self.assertEqual(b.read(self.keys_env), "A=1\nDEEPSEEK_API_KEY=sk-new\nB=2\n")
        self.assertFalse(os.path.exists(self.auth), "no opencode dir, no auth.json made")

    def test_no_key_is_a_problem(self):
        b = self.b
        b.upkeep("run", "--force")
        self.assertIn("no DeepSeek key: put it in ~/.config/api-keys/deepseek_key",
                      b.state()["problems"])


# ----------------------------------------------------------- self-update

class SelfUpdate(Case):
    def test_run_copies_in_the_highest_version_and_reexecs(self):
        b = self.b
        b.green()
        b.install()
        newer = b.make_repo(os.path.join(b.root, "newer"), version=U.version_of(HERE) + 5)
        repos = os.path.join(b.home, ".config", "upkeep", "repos.json")
        b.write(repos, json.dumps([b.repo, newer]))
        full_scenario(b)
        b.upkeep("run", "--force")
        self.assertEqual(U.version_of(b.share), U.version_of(HERE) + 5)
        self.assertIn("self-update: upkeep %d copied in" % (U.version_of(HERE) + 5), b.log())
        self.assertEqual(b.state()["version"], U.version_of(HERE) + 5)

    def test_parity_install_runs_and_its_problems_count(self):
        b = self.b
        b.green()
        b.write(os.path.join(b.repo, "upkeep", "opencode", "install.py"),
                "import sys\nprint('parity: 2 things')\nsys.exit(2)\n")
        b.install()
        full_scenario(b)
        b.upkeep("run", "--force")
        self.assertIn("the opencode parity layer reports 2 problem(s); see "
                      "~/.local/state/upkeep/upkeep.log", b.state()["problems"])
        self.assertIn("parity: 2 things", b.log())

    def test_absent_parity_layer_is_skipped_cleanly(self):
        b = self.b
        b.green()
        b.install()
        full_scenario(b)
        b.upkeep("run", "--force")
        self.assertEqual(b.state()["phases"].get("opencode parity"), "skipped: absent")
        self.assertNotIn("opencode", b.state()["failed"])


class Misc(Case):
    def test_log_trimmed_past_two_megabytes(self):
        b = self.b
        b.install()
        log = os.path.join(b.state_dir, "upkeep.log")
        b.write(log, "x" * 99 + "\n" * 1 + ("y" * 99 + "\n") * 25000)
        full_scenario(b)
        b.upkeep("run", "--force")
        self.assertLess(os.path.getsize(log), U.LOG_MAX)

    def test_usage(self):
        code, out = self.b.upkeep("bogus", script=os.path.join(HERE, "upkeep.py"))
        self.assertEqual(code, 2)
        code, out = self.b.upkeep("run", "--nope", script=os.path.join(HERE, "upkeep.py"))
        self.assertEqual(code, 2)

    def test_status_clean_machine_exits_zero(self):
        b = self.b
        b.install()
        st = {"last_attempt": U.stamp(), "last_success": U.stamp(), "last_result": "ok",
              "failed": {}, "held": {}, "problems": [], "hooks": {}}
        b.write(os.path.join(b.state_dir, "state.json"), json.dumps(st))
        code, out = b.upkeep("status")
        self.assertEqual(code, 0, out)
        self.assertIn("last run:  ok", out)

    def test_runs_on_python39_syntax(self):
        p = subprocess.run([PY, "-c", "import ast,sys; ast.parse(open(sys.argv[1]).read())",
                            os.path.join(HERE, "upkeep.py")])
        self.assertEqual(p.returncode, 0)

    def test_setup_mac_never_puts_brew_first(self):
        text = self.b.read(os.path.join(HERE, "setup-mac.sh"))
        self.assertNotIn('PATH="$d:$PATH"', text)
        self.assertIn('PATH="$PATH:$d"', text)

    def test_setup_mac_prints_owner_steps(self):
        b = self.b
        if 'PATH="$d:$PATH"' in b.read(os.path.join(HERE, "setup-mac.sh")):
            self.fail("REFUSED: setup-mac.sh would put the real brew before the fakes")
        full_scenario(b)
        p = subprocess.run(["bash", os.path.join(b.repo, "upkeep", "setup-mac.sh")],
                           env=dict(b.env, PATH=b.path), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True, timeout=300)
        out = p.stdout
        self.assertEqual(p.returncode, 3, out)
        self.assertIn("Install Xcode", out)
        self.assertIn("sudo bash %s/upkeep/root/install.sh" % b.repo, out)
        self.assertIn("~/.config/api-keys/deepseek_key", out)
        self.assertIn("update", b.argv("brew"), "the forced first run ran")
        b.green()
        p = subprocess.run(["bash", os.path.join(b.repo, "upkeep", "setup-mac.sh")],
                           env=dict(b.env, PATH=b.path), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True, timeout=300)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("nothing: open a new terminal", p.stdout)

    def test_brewfile_has_what_flutter_doctor_checks(self):
        casks = re.findall(r'^cask "([^"]+)"', self.b.read(os.path.join(HERE, "Brewfile")),
                           re.M)
        for c in ("flutter", "android-studio", "android-commandlinetools", "google-chrome"):
            self.assertIn(c, casks)

    def test_setup_mac_homebrew_only(self):
        b = self.b
        if 'PATH="$d:$PATH"' in b.read(os.path.join(HERE, "setup-mac.sh")):
            self.fail("REFUSED: setup-mac.sh would put the real brew before the fakes")
        b.clear_calls()
        p = subprocess.run(["bash", os.path.join(b.repo, "upkeep", "setup-mac.sh"),
                            "--homebrew"],
                           env=dict(b.env, PATH=b.path), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertNotIn("upkeep install", p.stdout)
        self.assertFalse(b.argv("brew"), "brew is there: nothing runs")
        self.assertFalse(b.argv("curl"), "and no installer is fetched")


if __name__ == "__main__":
    unittest.main(verbosity=1)
