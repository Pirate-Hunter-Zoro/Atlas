"""Tests for plugins/parity.ts, run under node with a stub OpenCode client and a temp state dir.

    python3 -m unittest upkeep/opencode/test_parity.py

Skipped when node (22.6 or newer, for TypeScript type stripping) is missing.
"""
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
NODE = shutil.which("node")


def node_ok():
    if not NODE:
        return False
    out = subprocess.run([NODE, "--version"], capture_output=True, text=True).stdout.strip().lstrip("v")
    major, minor = (int(x) for x in out.split(".")[:2])
    return (major, minor) >= (22, 6)


STUB_PLUGIN = """
const chain = new Proxy(function () {}, { get: () => chain, apply: () => chain });
export function tool(def) { return def; }
tool.schema = chain;
"""

# Shared by every script: loads the plugin and builds a stub client that logs each call.
LIB = r"""
import { appendFileSync, existsSync, readFileSync } from "node:fs";
export const CALLS = process.env.CALLS;
export function record(o) { appendFileSync(CALLS, JSON.stringify({ pid: process.pid, ...o }) + "\n"); }
export function makeClient() {
  let n = 0;
  return {
    session: {
      promptAsync: async (r) => { record({ op: "prompt", id: r.path.id, text: r.body.parts[0].text }); return { response: { status: 204 } }; },
      create: async () => ({ data: { id: `child${process.pid}x${++n}` } }),
      status: async () => ({ data: {} }),
      messages: async () => ({ data: [{ info: { role: "assistant", time: { created: Date.now(), completed: Date.now() } },
        parts: [{ type: "text", text: "done" }] }] }),
      abort: async () => ({}),
      children: async () => ({ data: [] }),
    },
    tui: {},
  };
}
export async function load(directory) {
  const { ParityPlugin } = await import(process.env.PLUGIN);
  return ParityPlugin({ client: makeClient(), directory, worktree: directory });
}
export function ctx(directory, sessionID = "parent") {
  return { sessionID, messageID: "m1", agent: "build", directory, abort: new AbortController().signal };
}
export function jobs() {
  try { return JSON.parse(readFileSync(process.env.PARITY_STATE_DIR + "/jobs.json", "utf-8")); } catch { return []; }
}
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
export async function until(path) { while (!existsSync(path)) await sleep(50); }
"""


@unittest.skipUnless(node_ok(), "node 22.6+ not found")
class Plugin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "plugins").mkdir()
        shutil.copy(HERE / "plugins" / "parity.ts", self.root / "plugins" / "parity.ts")
        shutil.copy(HERE / "capabilities.md", self.root / "capabilities.md")
        stub = self.root / "node_modules" / "@opencode-ai" / "plugin"
        stub.mkdir(parents=True)
        (stub / "package.json").write_text('{"name": "@opencode-ai/plugin", "type": "module", "main": "index.js"}')
        (stub / "index.js").write_text(STUB_PLUGIN)
        (self.root / "package.json").write_text('{"type": "module"}')
        (self.root / "lib.mjs").write_text(LIB)
        self.state = self.root / "state"
        self.calls = self.root / "calls.jsonl"
        self.calls.touch()
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            if p.poll() is None:
                p.kill()
            p.communicate()
        self.tmp.cleanup()

    def env(self, **extra):
        env = dict(os.environ, PARITY_STATE_DIR=str(self.state), CALLS=str(self.calls),
                   PLUGIN=str(self.root / "plugins" / "parity.ts"), PARITY_SYNC_MS="200", PARITY_BROWSER_MCP="0")
        env.pop("PARITY_PRIMARY", None)
        env.update(extra)
        return env

    def script(self, name, body):
        path = self.root / f"{name}.mjs"
        path.write_text('import { load, ctx, jobs, sleep, until, record } from "./lib.mjs";\n' + body)
        return path

    def argv(self, path, *args):
        return [NODE, "--experimental-strip-types", "--no-warnings", str(path), *args]

    def run_node(self, name, body, *args, **env):
        p = subprocess.run(self.argv(self.script(name, body), *args), cwd=self.root, env=self.env(**env),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def start_node(self, name, body, *args, **env):
        p = subprocess.Popen(self.argv(self.script(name, body), *args), cwd=self.root, env=self.env(**env),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.procs.append(p)
        return p

    def calls_list(self):
        return [json.loads(x) for x in self.calls.read_text().splitlines() if x.strip()]

    def jobs(self):
        try:
            return json.loads((self.state / "jobs.json").read_text())
        except (OSError, ValueError):
            return []

    def wait_for(self, cond, what, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            if cond():
                return
            time.sleep(0.05)
        self.fail(f"timed out waiting for {what}")

    # ---------------------------------------------------------------- cron

    def test_cron_day_of_week_seven_is_sunday(self):
        out = self.run_node("cron", r"""
const P = await load(process.cwd());
const res = {};
for (const expr of ["0 9 * * 1-7", "0 9 * * 5-7", "0 9 * * 7", "0 9 * * 0-6", "0 9 * * sun", "0 9 * * 8", "0 9 * * 6-5"]) {
  try { res[expr] = await P.tool.cron_create.execute({ cron: expr, prompt: "x", durable: false }, ctx(process.cwd())); }
  catch (e) { res[expr] = "ERR " + e.message; }
}
console.log(JSON.stringify(res));
process.exit(0);
""")
        res = json.loads(out)
        for expr in ("0 9 * * 1-7", "0 9 * * 5-7", "0 9 * * 7", "0 9 * * 0-6", "0 9 * * sun"):
            self.assertTrue(res[expr].startswith("Cron "), (expr, res[expr]))
        self.assertTrue(res["0 9 * * 8"].startswith("ERR"))
        self.assertTrue(res["0 9 * * 6-5"].startswith("ERR"))

    def test_cron_next_times(self):
        out = self.run_node("cronnext", r"""
const P = await load(process.cwd());
const out = {};
for (const expr of ["0 9 * * 5-7", "0 9 * * 7", "30 6 * * 1-7"]) {
  await P.tool.cron_create.execute({ cron: expr, prompt: expr }, ctx(process.cwd()));
}
for (const j of jobs()) out[j.cron] = j.next_at;
console.log(JSON.stringify(out));
process.exit(0);
""")
        nxt = {k: datetime.fromtimestamp(v / 1000) for k, v in json.loads(out).items()}
        self.assertIn(nxt["0 9 * * 5-7"].isoweekday(), (5, 6, 7))
        self.assertEqual(nxt["0 9 * * 7"].isoweekday(), 7)
        self.assertEqual((nxt["30 6 * * 1-7"].hour, nxt["30 6 * * 1-7"].minute), (6, 30))
        self.assertLess((nxt["30 6 * * 1-7"] - datetime.now()).total_seconds(), 86400 + 60)

    # ---------------------------------------------------------------- agents

    def test_background_agent_reported_once_with_two_instances(self):
        out = self.run_node("dup", r"""
const A = process.cwd() + "/A", B = process.cwd() + "/B";
const PA = await load(A);
const r = await PA.tool.agent_spawn.execute({ prompt: "p", description: "d", worktree: B }, ctx(A));
const child = r.match(/Agent (\S+) started/)[1];
const PB = await load(B);
const ev = { event: { type: "session.idle", properties: { sessionID: child } } };
await PA.event(ev);
await PB.event(ev);
await sleep(300);
console.log(child);
process.exit(0);
""")
        child = out.strip()
        to_parent = [c for c in self.calls_list() if c["id"] == "parent"]
        self.assertEqual(len(to_parent), 1, to_parent)
        self.assertIn(f'<task id="{child}" state="completed">', to_parent[0]["text"])

    # ---------------------------------------------------------------- several processes

    SERVER = r"""
const P = await load(process.cwd());
globalThis.P = P;
const m = await P.tool.monitor.execute({ command: "while true; do sleep 0.2; done", description: "spin" }, ctx(process.cwd(), "s1"));
const w = await P.tool.wakeup.execute({ delay_seconds: 3600, prompt: "later" }, ctx(process.cwd(), "s1"));
record({ op: "ready", monitor: m.match(/Monitor (\S+)/)[1] });
setInterval(() => {}, 1000);
"""

    def start_server(self, name="server"):
        p = self.start_node(name, self.SERVER, "serve")
        self.wait_for(lambda: any(c["op"] == "ready" and c["pid"] == p.pid for c in self.calls_list()), "server ready")
        mon = next(c["monitor"] for c in self.calls_list() if c["op"] == "ready" and c["pid"] == p.pid)
        return p, mon

    def job(self, kind):
        return next((j for j in self.jobs() if j["kind"] == kind), None)

    def test_second_process_leaves_the_servers_jobs_alone(self):
        server, mon = self.start_server()
        pid = self.job("monitor")["pid"]
        out = self.run_node("tui", r"""
const P = await load(process.cwd());
await sleep(600);
await P.tool.wakeup.execute({ delay_seconds: 7200, prompt: "mine" }, ctx(process.cwd(), "t1"));
const list = await P.tool.cron_list.execute({}, ctx(process.cwd(), "s1"));
console.log(JSON.stringify({ list }));
process.exit(0);
""")
        self.assertIn("later", json.loads(out)["list"], "a listing shows the server's wakeup")
        mj = self.job("monitor")
        self.assertEqual(mj["pid"], pid, "the monitor was not restarted")
        self.assertEqual(mj["owner"]["pid"], server.pid)
        os.kill(pid, 0)
        prompts = [c for c in self.calls_list() if c["op"] == "prompt" and c["pid"] != server.pid]
        self.assertEqual(prompts, [], "the second process delivered nothing")
        # The TUI exited; the server adopts its wakeup.
        self.wait_for(lambda: any(j["prompt"] == "mine" and j["owner"]["pid"] == server.pid
                                  for j in self.jobs() if j["kind"] == "wakeup"), "server adopts the orphaned wakeup")
        self.assertEqual(len([j for j in self.jobs() if j["kind"] == "wakeup"]), 2)

    def test_delete_from_another_process_stops_the_owners_job(self):
        server, mon = self.start_server()
        pid = self.job("monitor")["pid"]
        wid = self.job("wakeup")["id"]
        self.run_node("killer", f"""
const P = await load(process.cwd());
console.log(await P.tool.bg_kill.execute({{ id: "{mon}" }}, ctx(process.cwd(), "s1")));
console.log(await P.tool.cron_delete.execute({{ id: "{wid}" }}, ctx(process.cwd(), "s1")));
process.exit(0);
""", "run")

        def dead():
            try:
                os.kill(pid, 0)
                return False
            except OSError:
                return True
        self.wait_for(dead, "the owner kills its monitor")
        time.sleep(0.6)
        self.assertEqual(self.jobs(), [])
        self.assertEqual([c for c in self.calls_list() if c["op"] == "prompt"], [], "a stopped job reports nothing")

    def test_run_never_adopts_and_a_new_server_does(self):
        server, mon = self.start_server()
        server.send_signal(signal.SIGKILL)
        server.wait()
        self.run_node("oneshot", "await load(process.cwd()); await sleep(600); process.exit(0);\n", "run")
        self.assertEqual(self.job("wakeup")["owner"]["pid"], server.pid, "opencode run did not adopt")
        server2, _ = self.start_server("server2")
        self.wait_for(lambda: all(j["owner"]["pid"] == server2.pid for j in self.jobs()) and len(self.jobs()) == 4,
                      "the new server adopts the dead server's jobs")
        restarted = [c for c in self.calls_list() if c["op"] == "prompt" and 'event="restarted"' in c["text"]]
        self.assertEqual(len(restarted), 1)

    # ---------------------------------------------------------------- hooks

    def test_capabilities_and_browser_mcp_come_from_the_plugin(self):
        out = self.run_node("hooks", r"""
const P = await load(process.cwd());
const o = { system: [] };
await P["experimental.chat.system.transform"]({}, o);
const cfg = {};
await P.config(cfg);
const kept = { mcp: { playwright: { type: "remote", url: "x" } } };
await P.config(kept);
console.log(JSON.stringify({ system: o.system, cfg, kept }));
process.exit(0);
""", PARITY_BROWSER_MCP="1")
        r = json.loads(out)
        self.assertEqual(r["system"], [(HERE / "capabilities.md").read_text().strip()])
        self.assertEqual(r["cfg"]["mcp"]["playwright"]["command"][-1], "@playwright/mcp@latest")
        self.assertEqual(r["kept"]["mcp"]["playwright"], {"type": "remote", "url": "x"})


if __name__ == "__main__":
    unittest.main()
