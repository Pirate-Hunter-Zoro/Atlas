"""Tests for install.py. HOME is always a temp dir.  python3 -m unittest upkeep/opencode/test_install.py"""
import io
import json
import os
import plistlib
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import install  # noqa: E402

LIVE_LIKE = """{
  "$schema": "https://opencode.ai/config.json",
  "permission": "allow",
  "plugin": [
    "./plugin/vision-bridge.ts"
  ],
  "model": "deepseek/deepseek-flash",
  "theme": "dracula",
  "provider": {
    "openrouter": {"npm": "@ai-sdk/openai-compatible", "options": {"baseURL": "https://openrouter.ai/api/v1"}},
    "groq": {"npm": "x"},
    "cloudflare": {"npm": "y"}
  }
}
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = self.home / ".config" / "opencode"

    def tearDown(self):
        self.tmp.cleanup()

    def run_install(self, dry=False):
        out = io.StringIO()
        inst = install.Installer(self.home, dry_run=dry, out=out)
        rc = inst.run()
        return rc, out.getvalue(), inst

    def config(self):
        return json.loads(install.strip_jsonc((self.cfg / "opencode.jsonc").read_text()))


class FreshHome(Base):
    def test_installs_everything(self):
        rc, out, _ = self.run_install()
        self.assertEqual(rc, 0, out)
        for rel in ("plugins/parity.ts", "capabilities.md", "agents/worker.md", "agents/deep.md",
                    "agents/reviewer.md", "agents/structured.md", "agents/verifier.md", "agents/fixer.md",
                    "commands/loop.md", "commands/ultracode.md", "commands/review.md", "commands/simplify.md"):
            self.assertTrue((self.cfg / rel).is_file(), rel)
        self.assertFalse((self.cfg / "config.json").exists(), "config.json in the config dir would load as config")
        c = self.config()
        self.assertEqual(c["model"], "deepseek/deepseek-flash")
        self.assertEqual(c["small_model"], "deepseek/deepseek-flash")
        self.assertEqual(c["enabled_providers"], ["deepseek"])
        self.assertEqual(c["subagent_depth"], 3)
        self.assertEqual(c["permission"], "allow")
        self.assertEqual(c["agent"]["build"]["permission"], {"doom_loop": "allow", "external_directory": "allow"})
        self.assertEqual(c["provider"]["deepseek"]["models"]["deepseek-flash"]["variants"]["nothink"],
                         {"thinking": {"type": "disabled"}})
        self.assertNotIn("deepseek-v4-pro", c["provider"]["deepseek"]["models"],
                         "V4 Pro must never be selectable")
        self.assertEqual(c["experimental"]["primary_tools"], ["wakeup", "cron_create", "cron_delete", "monitor", "workflow"])
        self.assertNotIn("instructions", c)
        pkg = json.loads((self.cfg / "package.json").read_text())
        self.assertEqual(pkg["dependencies"]["@opencode-ai/plugin"], "1.19.5")
        self.assertEqual(pkg["dependencies"]["@opencode-ai/sdk"], "1.19.5")
        coder = self.home / "bin" / "coder"
        self.assertTrue(os.access(coder, os.X_OK))
        self.assertIn("exec opencode --auto", coder.read_text())
        self.assertTrue((self.home / ".local/state/opencode").is_dir())

    def test_second_run_changes_nothing(self):
        _, first, inst = self.run_install()
        self.assertEqual(first.splitlines()[-1], f"changed: {len(inst.changes)}")
        self.assertGreater(len(inst.changes), 0)
        before = (self.cfg / "opencode.jsonc").read_text()
        rc, out, inst = self.run_install()
        self.assertEqual(rc, 0)
        self.assertEqual(inst.changes, [])
        self.assertIn("up to date", out)
        self.assertEqual(out.splitlines()[-1], "changed: 0")
        self.assertEqual((self.cfg / "opencode.jsonc").read_text(), before)

    def test_dry_run_writes_nothing(self):
        rc, out, inst = self.run_install(dry=True)
        self.assertEqual(rc, 0)
        self.assertTrue(inst.changes)
        self.assertTrue(out.startswith("would: "))
        self.assertEqual(out.splitlines()[-1], f"would: changed: {len(inst.changes)}")
        self.assertFalse(self.home.joinpath(".config").exists())
        self.assertFalse(self.home.joinpath("bin").exists())


class ExistingConfig(Base):
    def write_cfg(self, text, name="opencode.jsonc"):
        self.cfg.mkdir(parents=True)
        (self.cfg / name).write_text(text)

    def test_live_like_config(self):
        self.write_cfg(LIVE_LIKE)
        (self.cfg / "plugin").mkdir()
        (self.cfg / "plugin" / "vision-bridge.ts").write_text("export const V = async () => ({})\n")
        rc, out, _ = self.run_install()
        self.assertEqual(rc, 0, out)
        c = self.config()
        self.assertEqual(c["theme"], "dracula")
        self.assertEqual(list(c["provider"]), ["deepseek"])
        self.assertNotIn("plugin", c, "a plugin under plugin/ is scanned; listing it loads it twice")
        self.assertEqual(c["permission"], "allow", "MO's legacy doctor resets any other value")
        for name in ("build", "plan", "general", "explore"):
            self.assertEqual(c["agent"][name]["permission"], {"doom_loop": "allow", "external_directory": "allow"})
        self.assertNotIn("instructions", c, "capabilities reach the model through the plugin, not instructions")
        self.assertNotIn("mcp", c, "the browser MCP comes from the plugin, so --pure never starts it")

    def test_existing_v4_pro_model_is_pruned(self):
        self.write_cfg(json.dumps({"provider": {"deepseek": {"models": {
            "deepseek-flash": {"name": "flash"},
            "deepseek-v4-pro": {"name": "DeepSeek V4 Pro"},
            "deepseek-v4-pro-0813": {"name": "snapshot"},
        }}}}))
        self.run_install()
        models = self.config()["provider"]["deepseek"]["models"]
        self.assertEqual(sorted(models), ["deepseek-flash"], "no V4 Pro id survives a merge")

    def test_legacy_doctor_and_install_agree(self):
        # MO's opencodedoctor sets permission to the string "allow" whenever it is anything else.
        self.write_cfg(LIVE_LIKE)
        self.run_install()
        text = (self.cfg / "opencode.jsonc").read_text()
        data = json.loads(text)
        self.assertEqual(data.get("permission"), "allow", "the doctor would rewrite this file")
        rc, out, inst = self.run_install()
        self.assertEqual(inst.changes, [], out)
        self.assertEqual((self.cfg / "opencode.jsonc").read_text(), text)

    def test_old_capabilities_instruction_removed(self):
        self.write_cfg(json.dumps({"instructions": ["~/notes.md", "~/.config/opencode/capabilities.md"]}))
        self.run_install()
        self.assertEqual(self.config()["instructions"], ["~/notes.md"])

    def test_agent_settings_kept(self):
        self.write_cfg(json.dumps({"agent": {"build": {"model": "x/y", "permission": {"bash": "ask"}}, "mine": {"mode": "subagent"}}}))
        self.run_install()
        a = self.config()["agent"]
        self.assertEqual(a["build"]["model"], "x/y")
        self.assertEqual(a["build"]["permission"], {"bash": "ask", "doom_loop": "allow", "external_directory": "allow"})
        self.assertEqual(a["mine"], {"mode": "subagent"})

    def test_explicit_plugin_elsewhere_is_kept(self):
        self.write_cfg('{"plugin": ["opencode-foo", "./plugin/missing.ts"]}')
        self.run_install()
        self.assertEqual(self.config()["plugin"], ["opencode-foo", "./plugin/missing.ts"])

    def test_jsonc_comments_and_trailing_commas(self):
        self.write_cfg('{\n  // my theme\n  "theme": "nord", /* keep */\n  "mcp": {"x": {"type": "local", "command": ["a"],},},\n  "instructions": ["~/notes.md",],\n}\n')
        rc, out, _ = self.run_install()
        self.assertEqual(rc, 0, out)
        c = self.config()
        self.assertEqual(c["theme"], "nord")
        self.assertEqual(c["mcp"]["x"]["command"], ["a"])
        self.assertEqual(c["instructions"], ["~/notes.md"])
        backup = self.cfg / "opencode.jsonc.before-upkeep"
        self.assertIn("// my theme", backup.read_text())

    def test_unparseable_config_left_alone(self):
        bad = '{"theme": "nord", "model": }'
        self.write_cfg(bad)
        rc, out, _ = self.run_install()
        self.assertEqual(rc, 1)
        self.assertIn("left alone", out)
        self.assertEqual((self.cfg / "opencode.jsonc").read_text(), bad)

    def test_opencode_json_is_used_when_no_jsonc(self):
        self.write_cfg('{"theme": "x"}', name="opencode.json")
        self.run_install()
        self.assertFalse((self.cfg / "opencode.jsonc").exists())
        self.assertEqual(json.loads((self.cfg / "opencode.json").read_text())["model"], "deepseek/deepseek-flash")

    def test_permission_object_keeps_other_rules(self):
        self.write_cfg('{"permission": {"bash": {"rm -rf /": "deny"}, "doom_loop": "ask"}}')
        self.run_install()
        p = self.config()["permission"]
        self.assertEqual(list(p), ["*", "bash", "doom_loop"], "* first, so the specific rules still win")
        self.assertEqual(p["bash"], {"rm -rf /": "deny"})
        self.assertEqual(p["doom_loop"], "ask")

    def test_package_json_keeps_other_deps(self):
        self.cfg.mkdir(parents=True)
        (self.cfg / "package.json").write_text('{"dependencies": {"@opencode-ai/plugin": "1.18.18", "left-pad": "1.0.0"}}')
        self.run_install()
        deps = json.loads((self.cfg / "package.json").read_text())["dependencies"]
        self.assertEqual(deps, {"@opencode-ai/plugin": "1.19.5", "left-pad": "1.0.0", "@opencode-ai/sdk": "1.19.5"})

    def test_bad_package_json_is_a_problem(self):
        self.cfg.mkdir(parents=True)
        (self.cfg / "package.json").write_text("{nope")
        rc, _, _ = self.run_install()
        self.assertEqual(rc, 1)
        self.assertEqual((self.cfg / "package.json").read_text(), "{nope")

    def test_symlinked_file_is_replaced_with_a_copy(self):
        self.cfg.mkdir(parents=True)
        target = self.home / "elsewhere.md"
        target.write_text("old")
        (self.cfg / "capabilities.md").symlink_to(target)
        self.run_install()
        self.assertFalse((self.cfg / "capabilities.md").is_symlink())
        self.assertEqual(target.read_text(), "old")


class Skills(Base):
    def test_nested_skills_copied_and_nothing_deleted(self):
        src = self.home / ".claude/skills/synced/abc/pdf"
        src.mkdir(parents=True)
        (src / "SKILL.md").write_text("---\nname: pdf\n---\n")
        (src / "scripts").mkdir()
        (src / "scripts" / "x.py").write_text("print(1)\n")
        trash = self.home / ".claude/skills/.trash/old-skill"
        trash.mkdir(parents=True)
        (trash / "SKILL.md").write_text("old\n")
        agents = self.home / ".agents/skills/tool"
        agents.mkdir(parents=True)
        (agents / "SKILL.md").write_text("tool\n")
        mine = self.cfg / "skills/describe-image"
        mine.mkdir(parents=True)
        (mine / "SKILL.md").write_text("mine\n")
        (self.cfg / "skills/pdf").mkdir(parents=True)
        (self.cfg / "skills/pdf/local-note.txt").write_text("keep\n")
        rc, out, _ = self.run_install()
        self.assertEqual(rc, 0, out)
        sk = self.cfg / "skills"
        self.assertTrue((sk / "pdf/SKILL.md").is_file())
        self.assertTrue((sk / "pdf/scripts/x.py").is_file())
        self.assertTrue((sk / "pdf/local-note.txt").is_file())
        self.assertFalse((sk / "old-skill").exists(), "skills in .trash are deleted ones")
        self.assertTrue((sk / "tool/SKILL.md").is_file())
        self.assertEqual((mine / "SKILL.md").read_text(), "mine\n")

    def test_claude_only_skills_skipped(self):
        for name, text in (("chrome-browser", "tools named mcp__claude-in-chrome__*"),
                           ("import-memory", "into Claude's memory"),
                           ("computer-use", "through the Claude desktop app"),
                           ("docx", "Word documents")):
            d = self.home / ".claude/skills/synced/x" / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {text}\n---\n")
        self.run_install()
        self.assertEqual(sorted(p.name for p in (self.cfg / "skills").iterdir()), ["docx"])


class Templates(unittest.TestCase):
    def test_plist_env_matches_env_file(self):
        data = plistlib.loads(install.render_serve_plist("/Users/x"))
        env = dict(data["EnvironmentVariables"])
        env.pop("PATH")
        self.assertEqual(env.pop("PARITY_PRIMARY"), "1", "the server adopts orphaned jobs")
        self.assertEqual(env, install.read_env())
        self.assertEqual(data["Label"], install.SERVE_LABEL)
        self.assertTrue(data["KeepAlive"])
        cmd = data["ProgramArguments"][-1]
        self.assertIn("--port 4096", cmd)
        self.assertIn("--hostname 127.0.0.1", cmd)
        self.assertNotIn("@HOME@", json.dumps(data))

    def test_env_does_not_turn_on_every_experiment(self):
        self.assertNotIn("OPENCODE_EXPERIMENTAL", install.read_env())

    def test_plugin_exports_only_the_plugin(self):
        # OpenCode calls every exported function of a plugin module as a plugin.
        src = (HERE / "plugins" / "parity.ts").read_text()
        self.assertEqual(re.findall(r"^export\s+(?:const|function|async function|default)\s*(\w*)", src, re.M), ["ParityPlugin"])

    def test_plugin_never_names_v4_pro(self):
        src = (HERE / "plugins" / "parity.ts").read_text()
        self.assertNotIn("deepseek-v4-pro", src, "a model override must never resolve to V4 Pro")
        self.assertIn("const RETIRED_MODEL = /v4-pro/i;", src)

    def test_plugin_has_every_tool(self):
        src = (HERE / "plugins" / "parity.ts").read_text()
        for name in ("wakeup", "cron_create", "cron_list", "cron_delete", "bg_shell", "bg_output", "bg_kill",
                     "monitor", "agent_spawn", "agent_send", "agent_stop", "agent_list", "fork", "workflow",
                     "worktree_create", "worktree_remove", "notify"):
            self.assertRegex(src, rf"\n      {name}: tool\(", name)

    def test_shell_and_coder_attach_with_dir(self):
        sh = (HERE / "shell.zsh").read_text()
        self.assertIn('opencode attach "$OPENCODE_SERVER_URL" --dir "$PWD"', sh)
        self.assertIn('opencode run --attach "$OPENCODE_SERVER_URL" --dir "$PWD"', sh)
        coder = (HERE / "coder").read_text()
        self.assertIn('--dir "$PWD"', coder)
        self.assertIn("exec opencode --auto", coder)

    def test_capabilities_name_no_vendor(self):
        text = (HERE / "capabilities.md").read_text()
        self.assertIn("~/.claude/CLAUDE.md", text, "the fallback for the owner's style rules")
        self.assertEqual(vendors(text), [])

    def test_a_vendor_outside_the_style_path_is_caught(self):
        self.assertEqual(vendors("Read ~/.claude/CLAUDE.md first."), [])
        self.assertEqual(vendors("Read ~/.claude/CLAUDE.md, as Claude does."), ["claude"])
        self.assertEqual(vendors("Read ~/.claude/skills."), ["claude"])
        self.assertEqual(vendors("Unlike Codex, you can wait."), ["codex"])


def vendors(text):
    """Vendor names in a prompt, the one style path (~/.claude/CLAUDE.md) excepted."""
    text = text.replace("~/.claude/CLAUDE.md", "").lower()
    return [v for v in ("claude", "anthropic", "openai", "codex", "deepseek", "gemini") if v in text]


# ------------------------------------------------------------------ agents and commands

def frontmatter(path):
    """The YAML front matter of an agent or command file, for the subset these files use:
    nested maps by two-space indent, plain or double-quoted keys, scalar values."""
    lines = path.read_text().split("\n")
    assert lines[0] == "---", path
    end = lines.index("---", 1)
    root, stack = {}, [(-1, None)]
    stack[0] = (-1, root)
    for line in lines[1:end]:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        m = re.match(r'\s*("(?:[^"\\]|\\.)*"|[^:]+):\s*(.*)$', line)
        assert m, f"{path}: {line!r}"
        key = json.loads(m.group(1)) if m.group(1).startswith('"') else m.group(1).strip()
        value = m.group(2).strip()
        while stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if value:
            parent[key] = value
        else:
            parent[key] = {}
            stack.append((indent, parent[key]))
    return root


def wildcard(text, pattern):
    """OpenCode 1.19.5's permission glob: backslashes read as slashes, * is anything, ? one
    character, and a trailing " *" also matches nothing, so "git diff *" matches "git diff"."""
    text, pattern = text.replace("\\", "/"), pattern.replace("\\", "/")
    r = re.sub(r"[.+^${}()|\[\]\\]", lambda m: "\\" + m.group(0), pattern).replace("*", ".*").replace("?", ".")
    if r.endswith(" .*"):
        r = r[:-3] + "( .*)?"
    return re.fullmatch(r, text, re.S) is not None


def bash_action(rules, command):
    """The action for one simple command: the last matching rule wins, as in OpenCode."""
    action = "ask"
    for pattern, act in rules.items():
        if wildcard(command, pattern):
            action = act
    return action


READ_ONLY = ("reviewer", "verifier")
ALLOWED = ("git diff HEAD", "git diff", "git log --oneline -5", "git show HEAD:board/README.md",
           "git status --short", "git rev-parse --show-toplevel", "cat board/README.md", "ls",
           "grep -rn key_sync upkeep", "head -20 x", "wc -l x", "cd board", "git diff main -- board/x.py",
           "git log --format=%h -3", "git branch --show-current",
           "python3 -m unittest upkeep/opencode/test_install.py", "python3 board/test/run.py sync",
           "ruby -c Brewfile", "plutil -lint x.plist", "brew list --formula", "uniq -c")
REFUSED = ("touch x", "rm -rf board", "mv a b", "cp a b", "mkdir d", "tee x", "echo x > f",
           "cat a >> b", "git diff 2>&1", "ls 2>/dev/null", "git add -A", "git add board/x.py",
           "git commit -m diff", "git commit -am diff", "git stash", "git checkout -- x",
           "git reset --hard", "git merge main", "git push", "git diff --output=x",
           "find . -delete", "find . -exec rm {} ;", "find . -execdir rm {} ;", "sed -i '' s/a/b/ f",
           "sed -n -i '' 1p f", "sort -o out in", "python3 -c 'open(\"x\",\"w\")'", "node -e 1",
           "curl -s http://127.0.0.1:8778/sessions.json", "env", "printenv", "brew upgrade",
           "brew bundle --file x", "mise install", "upkeep run --force", "chmod +x f",
           # Read commands whose arguments write or run a program.
           "sed -n '1w /tmp/x' a.txt", "sed -n w/tmp/out in.txt", "sed -n 1,40p upkeep/upkeep.py",
           "rg --pre rm hello board", "rg -n verdict upkeep", "find . -name '*.md'",
           "sort --compress-program=sh x", "jq -n env", "file -C -m x",
           "node --test --import data:text/javascript,1 x.test.js", "node --test x.test.js",
           "bash -n +n -c 'touch x'", "zsh -n +n -c 'touch x'", "bash -n scripts/setup.sh",
           # Programs that evaluate a config as code.
           "brew bundle check --file Brewfile", "brew bundle list --file Brewfile", "brew info ./x.rb",
           "brew list ./x.rb", "mise ls", "mise current",
           # unittest calls any zero-argument callable it is named, and gzip.main gzips its argv.
           "python3 -m unittest a.txt gzip.main", "python3 -m unittest ensurepip.bootstrap",
           "python3 -m unittest -v a.py", "python3 -m unittest 'a.txt gzip.main x.py'",
           # git flags that write or run a program, and the shapes that hide one from the matcher.
           "git log -1 --output o", "git show --output=o HEAD", "git diff --outp=x", "git grep -Ovim x",
           "git grep -iO'touch x' foo", "git grep -n verdict",
           "git grep --open-files-in-pager=vim x", "git diff --ext-diff", "git log --o{utput=x,}",
           "git log $A", "git log `cat f`", "git log --oneline $(cat f)", "cat $HOME/x")


class AgentFiles(unittest.TestCase):
    def agent(self, name):
        return frontmatter(HERE / "agents" / f"{name}.md")

    def test_models(self):
        for name in ("deep", "reviewer", "verifier", "worker", "fixer", "structured"):
            self.assertEqual(self.agent(name)["model"], "deepseek/deepseek-flash", name)
        self.assertEqual(frontmatter(HERE / "commands" / "ultracode.md")["model"], "deepseek/deepseek-flash")
        self.assertNotIn("agent", frontmatter(HERE / "commands" / "ultracode.md"),
                         "a subagent would run /ultracode as a subtask, which ends before its workflows report")

    def test_read_only_agents_deny_every_write_tool(self):
        for name in READ_ONLY + ("structured",):
            perm = self.agent(name)["permission"]
            for key in ("edit", "write", "apply_patch", "task"):
                self.assertEqual(perm.get(key), "deny", f"{name} {key}")
        for name in READ_ONLY:
            perm = self.agent(name)["permission"]
            for key in ("bg_shell", "monitor", "wakeup", "cron_create", "agent_spawn", "agent_send",
                        "fork", "workflow", "worktree_create", "worktree_remove"):
                self.assertEqual(perm.get(key), "deny", f"{name} {key} would run a command or a writer")

    def test_writers_may_edit(self):
        for name in ("worker", "fixer", "deep"):
            self.assertNotEqual(self.agent(name)["permission"].get("edit"), "deny", name)

    def test_read_only_bash_starts_by_denying_everything(self):
        for name in READ_ONLY:
            rules = self.agent(name)["permission"]["bash"]
            self.assertEqual(next(iter(rules.items())), ("*", "deny"), name)
            self.assertEqual(rules, self.agent("reviewer")["permission"]["bash"], "one rule set for both")

    def test_read_only_bash_allows_reads(self):
        for name in READ_ONLY:
            rules = self.agent(name)["permission"]["bash"]
            for cmd in ALLOWED:
                self.assertEqual(bash_action(rules, cmd), "allow", f"{name}: {cmd}")

    def test_read_only_bash_refuses_writes(self):
        for name in READ_ONLY:
            rules = self.agent(name)["permission"]["bash"]
            for cmd in REFUSED:
                self.assertEqual(bash_action(rules, cmd), "deny", f"{name}: {cmd}")

    def test_wildcard_matches_opencode(self):
        self.assertTrue(wildcard("git diff", "git diff *"))
        self.assertTrue(wildcard("git diff HEAD", "git diff *"))
        self.assertFalse(wildcard("git difftool", "git diff *"))
        self.assertTrue(wildcard("a > b", "*>*"))
        self.assertFalse(wildcard("git log", "git status *"))
        self.assertTrue(wildcard("a\\b", "a/b"), "OpenCode reads a backslash as a slash")
        self.assertFalse(wildcard("python3 -m unittest a.py", "python3 -m unittest * ?*"))
        self.assertTrue(wildcard("python3 -m unittest -v a.py", "python3 -m unittest * ?*"))

    def test_shell_line_names_only_allowed_commands(self):
        for name in READ_ONLY:
            rules = self.agent(name)["permission"]["bash"]
            body = (HERE / "agents" / f"{name}.md").read_text().split("---", 2)[2]
            line = next(x for x in body.splitlines() if "Your shell runs only read commands" in x)
            named = re.findall(r"`([a-z][^`]*)`", line.split("It refuses")[0])
            self.assertIn("git diff", named)
            for cmd in named:
                cmd = cmd.replace("<file>", "upkeep/x")
                self.assertEqual(bash_action(rules, cmd), "allow", f"{name} names {cmd!r}, which its rules refuse")
            self.assertNotIn("any command containing", body, "OpenCode never checks cd, so that claim is false")

    # The pattern OpenCode 1.19.5 checks for a line: each command node's text, plus its redirect
    # only when the redirect is on that command (ShellTool.collect and its helper in the binary).
    COMPOUND = {"(cat a) > out": "cat a", "{ cat a; } > ~/x": "cat a",
                "for i in 1; do cat a; done > out": "cat a", "cat a > out": "cat a > out"}

    def test_a_redirect_on_a_compound_statement_passes_the_bash_rules(self):
        for name in READ_ONLY:
            rules = self.agent(name)["permission"]["bash"]
            for line, pattern in self.COMPOUND.items():
                want = "deny" if line == pattern else "allow"
                self.assertEqual(bash_action(rules, pattern), want, f"{name}: {line}")
        row = next(x for x in (HERE / "README.md").read_text().splitlines() if x.startswith("| `agents/*.md`"))
        self.assertIn("cannot make it read-only", row, "the README must not claim the bash rules suffice")
        self.assertIn("under `--pure` these two agents can write", row)
        self.assertNotIn("raw text", row)

    def test_fixer_owns_only_its_files(self):
        text = (HERE / "agents" / "fixer.md").read_text()
        self.assertIn("Edit only the files your brief lists", text)


class Prompts(unittest.TestCase):
    def test_capabilities_list_every_command_and_agent(self):
        text = (HERE / "capabilities.md").read_text()
        self.assertEqual(self.missing(text), [])

    def test_a_dropped_agent_is_caught(self):
        text = (HERE / "capabilities.md").read_text().replace("`@fixer`", "`fixer`")
        self.assertEqual(self.missing(text), ["@fixer"])

    @staticmethod
    def missing(text):
        typed = text.split("## What the user can type", 1)[1]
        names = [f"/{p.stem}" for p in sorted((HERE / "commands").glob("*.md"))]
        names += [f"@{p.stem}" for p in sorted((HERE / "agents").glob("*.md"))
                  if frontmatter(p).get("hidden") != "true"]
        return [n for n in names if f"`{n}" not in typed]

    def test_capabilities_document_the_workflow_api_and_rules(self):
        text = (HERE / "capabilities.md").read_text()
        for needle in ("verify_until_pass(fixStage, verifyStage, {max: 3})", "readonly: true",
                       "verbatim request", "word for word", "git rev-parse --show-toplevel",
                       "Threat model", "~/.config/opencode/AGENTS.md", "at most 6 lines",
                       "## How work is judged", "Guards"):
            self.assertIn(needle, text)

    def test_capabilities_name_the_tools_and_shapes(self):
        text = (HERE / "capabilities.md").read_text()
        self.assertEqual(missing_needles(text, CAPABILITY_NEEDLES), [])
        for needle in CAPABILITY_NEEDLES:
            self.assertEqual(missing_needles(text.replace(needle, ""), CAPABILITY_NEEDLES), [needle])

    def test_capabilities_claim_no_more_than_the_guard_does(self):
        text = (HERE / "capabilities.md").read_text()
        for claim in ("any shell write", "any write under"):
            self.assertNotIn(claim, text, "the read-only and worktree guards refuse the writes they detect")
        self.assertIn("best-effort, not a sandbox", text)

    def test_sh_line_matches_its_guard(self):
        text = (HERE / "capabilities.md").read_text()
        code = (HERE / "plugins" / "parity.ts").read_text()
        self.assertEqual(sh_claim_problems(text, code), [])
        claim = "with the `bash` tool's guards except the `/ultracode` read budget"
        overclaim = text.replace(claim, "with the same guards as the `bash` tool")
        self.assertEqual(sh_claim_problems(overclaim, code), ["sh() skips the read budget"])
        budgeted = code.replace("directory: cwd }, client, false)", "directory: cwd }, client)")
        self.assertEqual(sh_claim_problems(text, budgeted), ["sh() keeps the read budget"])

    def test_worktree_cleanup_rule(self):
        for rel in ("capabilities.md", "commands/ultracode.md"):
            text = (HERE / rel).read_text()
            self.assertEqual(missing_needles(text, PROMPT_WORKTREE_NEEDLES), [], rel)
            line = next(x for x in text.splitlines() if "git merge <branch>" in x)
            self.assertEqual(missing_needles(text.replace(line, ""), PROMPT_WORKTREE_NEEDLES),
                             list(PROMPT_WORKTREE_NEEDLES), rel)
        code = (HERE / "plugins" / "parity.ts").read_text()
        self.assertIn("pruneMergedWorktree(m.dir, m.branch)", code, "the plugin does what the prompts say")

    def test_ultracode_frontmatter(self):
        fm = frontmatter(HERE / "commands" / "ultracode.md")
        self.assertEqual(command_problems(fm), [])
        self.assertEqual(command_problems({**fm, "subtask": "true"}), ["subtask"])
        self.assertEqual(command_problems({**fm, "model": "deepseek/deepseek-v4-pro"}), ["model"])
        self.assertEqual(command_problems({**fm, "agent": "deep"}), ["agent"])

    def test_verifier_fails_a_brief_without_the_request(self):
        text = (HERE / "agents" / "verifier.md").read_text().split("---", 2)[2]
        rule = "A brief without the owner's verbatim request or the Done-when list gets `fail`"
        self.assertIn(rule, text)
        self.assertNotIn(rule, text.replace("gets `fail`", "gets `pass`"))

    def test_readme_agents_row_says_no_sandbox(self):
        row = next(x for x in (HERE / "README.md").read_text().splitlines() if x.startswith("| `agents/*.md`"))
        self.assertIn("neither layer is a sandbox", row)
        self.assertNotIn("is a sandbox", row.replace("neither layer is a sandbox", ""))

    def test_ultracode_plans_against_real_artifacts_and_reverifies(self):
        text = (HERE / "commands" / "ultracode.md").read_text()
        for needle in ("owner's own examples", "threat model", "verify_until_pass", 'agent: "verifier"',
                       'agent: "fixer"', "verbatim", "never the builder's summary", "at most 6 lines",
                       "word for word", "readonly: true"):
            self.assertIn(needle, text)


CAPABILITY_NEEDLES = (
    "`session_read`", "pipefail", "~/.claude/CLAUDE.md", "`agent(prompt, {readonly: true})`",
    "`verify_until_pass(fixStage, verifyStage, {max: 3})`", "`verifyStage({round, failures})`",
    "`fixStage(failures, {round, verdicts})`", "`{passed, verdicts, failures, rounds}`",
    "Only live verdicts from read-only verify agents count",
    "`verifyStage` must return what its agents returned",
)
WORKTREE_NEEDLES = ("git worktree remove", "delete its branch", "parent directory", "24")
# The parity prompts: the plugin removes a merged worktree, so they name the merge that triggers it.
PROMPT_WORKTREE_NEEDLES = ("git merge <branch>", "deletes the branch", "parent directory", "worktree_remove")


def sh_claim_problems(text, code):
    """Whether the capabilities line on workflow sh() says what its guardCall does with the read budget."""
    line = next(x for x in text.splitlines() if x.startswith("- `sh(cmd"))
    call = next(x for x in code.splitlines() if "guardCall(" in x and 'tool: "bash"' in x and "cwd" in x)
    skips = call.rstrip().endswith("client, false);")
    says = "except the `/ultracode` read budget" in line
    if skips and not says:
        return ["sh() skips the read budget"]
    if says and not skips:
        return ["sh() keeps the read budget"]
    return []


def missing_needles(text, needles):
    return [n for n in needles if n not in text]


def command_problems(fm):
    """What keeps /ultracode on flash in the session it was typed in."""
    bad = [k for k in ("subtask", "agent") if k in fm]
    if fm.get("model") != "deepseek/deepseek-flash":
        bad.append("model")
    return bad


def repo_root():
    r = subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(r.stdout.strip()) if r.returncode == 0 else None


ROOT = repo_root()


@unittest.skipUnless(ROOT and (ROOT / "board" / "tutorboard").is_dir(), "Atlas only; MO carries its own AGENTS.md")
class AtlasAgents(unittest.TestCase):
    def test_names_the_rules(self):
        text = (ROOT / "AGENTS.md").read_text()
        for needle in ("board/scripts/save-and-push.sh", "git add -A", "~/Developer/Atlas-wt/",
                       "python3 board/test/run.py", "auth.json", "keys.env", "rclone", "SSH keys",
                       "DeepSeek through OpenCode", "public", "README.md", "HANDOFF.md",
                       "board/README.md", "git rev-parse --show-toplevel"):
            self.assertIn(needle, text)

    def test_worktree_cleanup_rule(self):
        text = (ROOT / "AGENTS.md").read_text()
        self.assertEqual(missing_needles(text, WORKTREE_NEEDLES), [])
        self.assertIn("in any repository", text)

    def test_every_link_resolves(self):
        text = (ROOT / "AGENTS.md").read_text()
        links = re.findall(r"\]\(([^)]+)\)", text)
        self.assertTrue(links)
        for link in links:
            self.assertTrue((ROOT / link).exists(), link)

    def test_present_tense(self):
        text = (ROOT / "AGENTS.md").read_text().lower()
        for word in ("used to", "no longer", "formerly", "until ", "was "):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
