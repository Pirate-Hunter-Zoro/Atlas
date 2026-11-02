"""Tests for install.py. HOME is always a temp dir.  python3 -m unittest upkeep/opencode/test_install.py"""
import io
import json
import os
import plistlib
import re
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
                    "agents/reviewer.md", "agents/structured.md", "commands/loop.md",
                    "commands/ultracode.md", "commands/review.md", "commands/simplify.md"):
            self.assertTrue((self.cfg / rel).is_file(), rel)
        self.assertFalse((self.cfg / "config.json").exists(), "config.json in the config dir would load as config")
        c = self.config()
        self.assertEqual(c["model"], "deepseek/deepseek-flash")
        self.assertEqual(c["small_model"], "deepseek/deepseek-flash")
        self.assertEqual(c["enabled_providers"], ["deepseek"])
        self.assertEqual(c["subagent_depth"], 3)
        self.assertEqual(c["permission"], "allow")
        self.assertEqual(c["agent"]["build"]["permission"], {"doom_loop": "allow", "external_directory": "allow"})
        for m in ("deepseek-flash", "deepseek-v4-pro"):
            self.assertEqual(c["provider"]["deepseek"]["models"][m]["variants"]["nothink"], {"thinking": {"type": "disabled"}})
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
        self.run_install()
        before = (self.cfg / "opencode.jsonc").read_text()
        rc, out, inst = self.run_install()
        self.assertEqual(rc, 0)
        self.assertEqual(inst.changes, [])
        self.assertIn("up to date", out)
        self.assertEqual((self.cfg / "opencode.jsonc").read_text(), before)

    def test_dry_run_writes_nothing(self):
        rc, out, inst = self.run_install(dry=True)
        self.assertEqual(rc, 0)
        self.assertTrue(inst.changes)
        self.assertTrue(out.startswith("would: "))
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
        text = (HERE / "capabilities.md").read_text().lower()
        for vendor in ("claude", "anthropic", "openai", "codex", "deepseek", "gemini"):
            self.assertNotIn(vendor, text)


if __name__ == "__main__":
    unittest.main()
