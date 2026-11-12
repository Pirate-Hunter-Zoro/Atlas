#!/usr/bin/env python3
"""Install the OpenCode parity layer into ~/.config/opencode.

    python3 upkeep/opencode/install.py [--dry-run] [--home DIR]

Copies the plugin, agents, commands and capabilities.md; merges the managed keys of
config.json into opencode.jsonc (JSONC-aware, every other key kept); pins the plugin SDK in
package.json; copies skills from ~/.claude/skills and ~/.agents/skills into
~/.config/opencode/skills (not hidden directories, not Claude-only skills) without deleting
anything; installs ~/bin/coder. Prints one line per
change, then `changed: N`, the count (`would: ` before each under --dry-run). Exit
status = number of problems. Stdlib only, Python 3.9.
"""
import argparse
import filecmp
import json
import os
import plistlib
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEAD_PROVIDERS = ("openrouter", "groq", "cloudflare")
# V4 Pro is retired: no config this installer writes or merges leaves it selectable.
FORBIDDEN_MODEL_MARKER = "v4-pro"
# A skill that names a Claude-only surface would send DeepSeek after tools it does not have.
CLAUDE_ONLY = re.compile(
    r"mcp__claude|mcp__computer-use|mcp__Claude_Browser|mcp__remote-devices|Claude desktop app"
    r"|Claude's memory|surface=cowork", re.I)
SERVE_LABEL = "com.mikeyferguson.opencode-serve"


# ------------------------------------------------------------------ JSONC

def strip_comments(text):
    """Remove // and /* */ comments outside strings."""
    out, i, n = [], 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            if j < 0:
                raise ValueError("unterminated /* comment")
            i = j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def strip_jsonc(text):
    """JSONC to JSON: comments out, then trailing commas before } or ] out."""
    s = strip_comments(text)
    res, i, n, in_str = [], 0, len(s), False
    while i < n:
        c = s[i]
        if in_str:
            res.append(c)
            if c == "\\" and i + 1 < n:
                res.append(s[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
        elif c == ",":
            j = i + 1
            while j < n and s[j] in " \t\r\n":
                j += 1
            if j < n and s[j] in "}]":
                i += 1
                continue
        res.append(c)
        i += 1
    return "".join(res)


def has_comments(text):
    return strip_comments(text) != text


def load_jsonc(path):
    text = path.read_text(encoding="utf-8")
    data = json.loads(strip_jsonc(text)) if text.strip() else {}
    if not isinstance(data, dict):
        raise ValueError("top level is not an object")
    return data, text


# ------------------------------------------------------------------ merge

def expand_home(value, home):
    if isinstance(value, str) and value.startswith("~/"):
        return str(home / value[2:])
    return value


def deep_merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def union(existing, extra):
    out = list(existing) if isinstance(existing, list) else []
    for x in extra:
        if x not in out:
            out.append(x)
    return out


def merge_config(cfg, managed, home, cfg_dir):
    """Apply the managed keys to a parsed opencode config in place."""
    cfg.setdefault("$schema", managed.get("$schema", "https://opencode.ai/config.json"))
    for key in ("model", "small_model", "enabled_providers", "subagent_depth"):
        cfg[key] = managed[key]
    # Top-level permission stays the string "allow" (MO's legacy opencodedoctor resets any other
    # value every minute). doom_loop and external_directory, which default to "ask" even then,
    # are allowed per agent in `agent`, which nothing else rewrites.
    perm = cfg.get("permission")
    if isinstance(perm, dict):
        if "*" not in perm:
            cfg["permission"] = {"*": "allow", **perm}
    elif perm is None:
        cfg["permission"] = managed["permission"]
    agents = cfg.get("agent") if isinstance(cfg.get("agent"), dict) else {}
    for name, spec in managed["agent"].items():
        if not isinstance(agents.get(name), dict):
            agents[name] = {}
        if not isinstance(agents[name].get("permission"), dict):
            agents[name]["permission"] = {}
        agents[name]["permission"].update(spec["permission"])
    cfg["agent"] = agents
    prov = cfg.get("provider") if isinstance(cfg.get("provider"), dict) else {}
    for dead in DEAD_PROVIDERS:
        prov.pop(dead, None)
    cfg["provider"] = deep_merge(prov, managed["provider"])
    for spec in cfg["provider"].values():
        models = spec.get("models") if isinstance(spec, dict) else None
        if not isinstance(models, dict):
            continue
        for name in [n for n in models if FORBIDDEN_MODEL_MARKER in n]:
            models.pop(name, None)
    exp = cfg.get("experimental") if isinstance(cfg.get("experimental"), dict) else {}
    exp["primary_tools"] = union(exp.get("primary_tools"), managed["experimental"]["primary_tools"])
    cfg["experimental"] = exp
    # capabilities.md reaches the model through the plugin, so `opencode --pure` never sees it.
    if isinstance(cfg.get("instructions"), list):
        ours = str(cfg_dir / "capabilities.md")
        cfg["instructions"] = [p for p in cfg["instructions"] if expand_home(p, home) != ours]
        if not cfg["instructions"]:
            cfg.pop("instructions")
    # Plugins in plugin/ or plugins/ load automatically; naming them again loads them twice.
    if isinstance(cfg.get("plugin"), list):
        kept = []
        for entry in cfg["plugin"]:
            name = entry if isinstance(entry, str) else (entry[0] if isinstance(entry, list) and entry else "")
            p = Path(expand_home(name, home))
            if not p.is_absolute():
                p = cfg_dir / p
            scanned = p.parent.resolve() in {(cfg_dir / "plugin").resolve(), (cfg_dir / "plugins").resolve()}
            if scanned and p.suffix in (".ts", ".js") and p.exists():
                continue
            kept.append(entry)
        if kept:
            cfg["plugin"] = kept
        else:
            cfg.pop("plugin")
    return cfg


# ------------------------------------------------------------------ installer

class Installer:
    def __init__(self, home, source=HERE, dry_run=False, out=sys.stdout):
        self.home = Path(home)
        self.src = Path(source)
        self.dry = dry_run
        self.out = out
        self.cfg_dir = self.home / ".config" / "opencode"
        self.changes = []
        self.problems = []

    def say(self, line):
        print(("would: " if self.dry else "") + line, file=self.out)

    def change(self, line):
        self.changes.append(line)
        self.say(line)

    def problem(self, line):
        self.problems.append(line)
        print(f"problem: {line}", file=self.out)

    def write(self, path, data, mode=None):
        if self.dry:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".upkeep-tmp")
        if isinstance(data, bytes):
            tmp.write_bytes(data)
        else:
            tmp.write_text(data, encoding="utf-8")
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)

    def copy(self, src, dst, mode=None, quiet=False):
        """Copy src over dst when the contents differ; True when it did."""
        if dst.exists() and not dst.is_symlink() and filecmp.cmp(src, dst, shallow=False):
            if mode is not None and (dst.stat().st_mode & 0o777) != mode and not self.dry:
                os.chmod(dst, mode)
            return False
        if not quiet:
            self.change(f"install {dst}")
        if not self.dry and dst.is_symlink():
            dst.unlink()
        self.write(dst, src.read_bytes(), mode)
        return True

    # -- steps

    def files(self):
        self.copy(self.src / "plugins" / "parity.ts", self.cfg_dir / "plugins" / "parity.ts")
        self.copy(self.src / "capabilities.md", self.cfg_dir / "capabilities.md")
        for sub in ("agents", "commands"):
            for f in sorted((self.src / sub).glob("*.md")):
                self.copy(f, self.cfg_dir / sub / f.name)

    def package_json(self):
        path = self.cfg_dir / "package.json"
        ours = json.loads((self.src / "package.json").read_text())
        data = {}
        if path.exists():
            try:
                data = json.loads(path.read_text() or "{}")
                if not isinstance(data, dict):
                    raise ValueError("top level is not an object")
            except ValueError as e:
                self.problem(f"{path} is not valid JSON ({e}); left alone")
                return
        deps = data.get("dependencies") if isinstance(data.get("dependencies"), dict) else {}
        new = dict(deps, **ours["dependencies"])
        if new != deps or "dependencies" not in data:
            data["dependencies"] = new
            self.change(f"pin {', '.join(f'{k}@{v}' for k, v in ours['dependencies'].items())} in {path}")
            self.write(path, json.dumps(data, indent=2) + "\n")

    def config(self):
        managed = json.loads((self.src / "config.json").read_text())
        path = self.cfg_dir / "opencode.jsonc"
        if not path.exists() and (self.cfg_dir / "opencode.json").exists():
            path = self.cfg_dir / "opencode.json"
        cfg, text = {}, ""
        if path.exists():
            try:
                cfg, text = load_jsonc(path)
            except ValueError as e:
                self.problem(f"{path} does not parse as JSONC ({e}); left alone")
                return
        before = json.dumps(cfg, sort_keys=True)
        merge_config(cfg, managed, self.home, self.cfg_dir)
        if json.dumps(cfg, sort_keys=True) == before and path.exists():
            return
        if text and has_comments(text):
            backup = path.with_name(path.name + ".before-upkeep")
            if not backup.exists():
                self.change(f"keep the commented original as {backup}")
                self.write(backup, text)
        self.change(f"merge managed keys into {path}")
        self.write(path, json.dumps(cfg, indent=2) + "\n")

    def skills(self):
        dest_root = self.cfg_dir / "skills"
        seen = {}
        for root in (self.home / ".claude" / "skills", self.home / ".agents" / "skills"):
            if not root.is_dir():
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                # Hidden directories (.trash) hold deleted skills.
                dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
                if "SKILL.md" not in filenames:
                    continue
                dirnames[:] = []
                skill = Path(dirpath)
                name = skill.name
                if name in seen:
                    continue
                seen[name] = skill
                text = (skill / "SKILL.md").read_text(encoding="utf-8", errors="replace")
                if CLAUDE_ONLY.search(text):
                    continue
                self.copy_tree(skill, dest_root / name)

    def copy_tree(self, src, dst):
        copied = 0
        for dirpath, _dirs, filenames in os.walk(src):
            rel = Path(dirpath).relative_to(src)
            for fn in filenames:
                s = Path(dirpath) / fn
                if s.is_symlink() or not s.is_file():
                    continue
                copied += self.copy(s, dst / rel / fn, quiet=True)
        if copied:
            self.change(f"copy skill {dst.name} ({copied} files) to {dst}")

    def coder(self):
        self.copy(self.src / "coder", self.home / "bin" / "coder", mode=0o755)

    def state_dirs(self):
        d = self.home / ".local" / "state" / "opencode"
        if not d.is_dir():
            self.change(f"create {d}")
            if not self.dry:
                d.mkdir(parents=True, exist_ok=True)

    def run(self):
        for step in (self.files, self.package_json, self.config, self.skills, self.coder, self.state_dirs):
            try:
                step()
            except OSError as e:
                self.problem(f"{step.__name__}: {e}")
        if not self.changes and not self.problems:
            self.say("opencode parity layer up to date")
        self.say(f"changed: {len(self.changes)}")
        return len(self.problems)


# ------------------------------------------------------------------ helpers for upkeep.py

def read_env(path=HERE / "env"):
    env = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def render_serve_plist(home, source=HERE):
    """The opencode-serve LaunchAgent with @HOME@ filled in, as bytes."""
    text = (Path(source) / "launchd" / f"{SERVE_LABEL}.plist").read_text()
    data = text.replace("@HOME@", str(home)).encode()
    plistlib.loads(data)
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--home", default=os.path.expanduser("~"))
    a = ap.parse_args(argv)
    return Installer(a.home, dry_run=a.dry_run).run()


if __name__ == "__main__":
    sys.exit(main())
