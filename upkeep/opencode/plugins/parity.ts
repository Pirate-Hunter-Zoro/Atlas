// parity: the long-running half of an agent harness, as OpenCode tools.
//
// Wakeups, cron, background shells, monitors, background agents, forks, workflow scripts,
// worktrees and notifications. Every job reports back by posting a message into the session
// that started it (client.session.promptAsync), so the model can end its turn and be woken.
// That only works while an opencode process stays alive: run `opencode serve` (the
// com.mikeyferguson.opencode-serve LaunchAgent) and attach to it.
//
// State: $PARITY_STATE_DIR, else $XDG_STATE_HOME/opencode/parity, else
// ~/.local/state/opencode/parity. jobs.json holds every durable job of every opencode process.
//
// Several opencode processes share jobs.json (the server, a plain TUI, `opencode run`, any
// subcommand that loads plugins). Each job records the process that owns it, and only the owner
// arms it. Another process never touches a job whose owner is alive; it reads it for listings
// and deletes it from the file, and the owner cancels it on its next sync. A job whose owner has
// died is adopted by the server (opencode serve, or PARITY_PRIMARY=1), or by a TUI when no server
// is up; `opencode run` and other subcommands never adopt. Within one process the registry is
// global (globalThis), so plugin instances for several directories share it.
import { tool } from "@opencode-ai/plugin";
import { AsyncLocalStorage } from "node:async_hooks";
import { spawn, execFile, execFileSync } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import {
  appendFileSync, existsSync, mkdirSync, readFileSync, readdirSync, realpathSync, renameSync, rmdirSync, statSync, writeFileSync,
  openSync, readSync, closeSync,
} from "node:fs";
import { homedir, uptime } from "node:os";
import { basename, dirname, isAbsolute, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const z = tool.schema;

// ---------------------------------------------------------------- state and registry

const STATE_DIR =
  process.env.PARITY_STATE_DIR ||
  join(process.env.XDG_STATE_HOME || join(homedir(), ".local", "state"), "opencode", "parity");
const JOBS_FILE = join(STATE_DIR, "jobs.json");
const LOCK_DIR = join(STATE_DIR, "jobs.lock");
const PRIMARY_FILE = join(STATE_DIR, "primary.json");
const LOG_FILE = join(STATE_DIR, "parity.log");
const MAX_TIMEOUT = 2 ** 31 - 1;
const SYNC_MS = Number(process.env.PARITY_SYNC_MS) || 10000;

type Owner = { pid: number; started: number };
type Job = Record<string, any> & { id: string; kind: string; session: string; directory: string; owner?: Owner };

// This process. `started` tells a live owner from a reused pid after a reboot.
const ME: Owner = { pid: process.pid, started: Math.round(Date.now() - process.uptime() * 1000) };
const BOOTED_AT = Date.now() - uptime() * 1000;
const COMMAND = process.argv.slice(2).find((a) => !a.startsWith("-"));
const NOT_TUI = new Set(["run", "debug", "mcp", "auth", "models", "agent", "upgrade", "uninstall", "stats",
  "export", "import", "github", "pr", "session", "acp", "attach", "generate", "plugin", "db"]);
const PRIMARY = process.env.PARITY_PRIMARY === "1" || COMMAND === "serve" || COMMAND === "web";
const MAY_ADOPT = PRIMARY || COMMAND === undefined || !NOT_TUI.has(COMMAND);

type Registry = {
  loaded: boolean;
  jobs: Map<string, Job>; // jobs this process owns and has armed
  written: Set<string>; // owned jobs this process has put in jobs.json
  reported: Set<string>; // agent rounds already delivered ("id#round")
  timers: Map<string, { cancel: () => void }>;
  procs: Map<string, any>;
  waiters: Map<string, Array<(e: { error?: string }) => void>>;
  clients: Map<string, any>;
  runs: Map<string, { abort: AbortController }>;
  seq: number;
};

const G: Registry = ((globalThis as any).__parity ??= {
  loaded: false,
  jobs: new Map(),
  written: new Set(),
  reported: new Set(),
  timers: new Map(),
  procs: new Map(),
  waiters: new Map(),
  clients: new Map(),
  runs: new Map(),
  seq: 0,
});

function log(msg: string) {
  try {
    mkdirSync(STATE_DIR, { recursive: true });
    appendFileSync(LOG_FILE, `${new Date().toISOString()} ${msg}\n`);
  } catch {}
}

function newId(prefix: string) {
  return `${prefix}${Date.now().toString(36)}${randomBytes(2).toString("hex")}`;
}

function sameOwner(a?: Owner, b: Owner = ME) {
  return !!a && a.pid === b.pid && a.started === b.started;
}

function ownerAlive(o?: Owner) {
  if (!o?.pid) return false;
  if (sameOwner(o)) return true;
  if (o.started && o.started < BOOTED_AT - 60000) return false;
  return pidAlive(o.pid);
}

function sleepSync(ms: number) {
  try {
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
  } catch {
    const end = Date.now() + ms;
    while (Date.now() < end) {}
  }
}

// jobs.json is read, changed and written under a lock directory (mkdir is atomic). A lock older
// than 10 s belongs to a dead process and is broken.
function withLock<T>(fn: () => T): T {
  mkdirSync(STATE_DIR, { recursive: true });
  const until = Date.now() + 5000;
  let held = false;
  while (!held) {
    try {
      mkdirSync(LOCK_DIR);
      held = true;
    } catch (e: any) {
      if (e?.code !== "EEXIST") throw e;
      try {
        if (Date.now() - statSync(LOCK_DIR).mtimeMs > 10000) { rmdirSync(LOCK_DIR); continue; }
      } catch {}
      if (Date.now() > until) { log("jobs.lock busy for 5 s; going ahead without it"); break; }
      sleepSync(20);
    }
  }
  try {
    return fn();
  } finally {
    if (held) try { rmdirSync(LOCK_DIR); } catch {}
  }
}

function loadJobs(): Job[] {
  try {
    const data = JSON.parse(readFileSync(JOBS_FILE, "utf-8"));
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

function writeJobs(jobs: Job[]) {
  const text = JSON.stringify(jobs, null, 2);
  try { if (readFileSync(JOBS_FILE, "utf-8") === text) return; } catch {}
  const tmp = `${JOBS_FILE}.${process.pid}.tmp`;
  writeFileSync(tmp, text);
  renameSync(tmp, JOBS_FILE);
}

// Writes this process's jobs into jobs.json, keeps every other process's, and cancels any job of
// ours that another process deleted from the file (or that a live process now owns).
function save() {
  const lost: Job[] = [];
  withLock(() => {
    const disk = loadJobs();
    const onDisk = new Set(disk.map((j) => j.id));
    const out: Job[] = [];
    for (const d of disk) {
      const mine = G.jobs.get(d.id);
      if (mine) {
        if (d.owner && !sameOwner(d.owner) && ownerAlive(d.owner)) { lost.push(mine); out.push(d); }
        else if (mine.durable !== false) out.push(mine);
      } else if (!sameOwner(d.owner)) {
        out.push(d);
      }
    }
    for (const j of G.jobs.values()) {
      if (onDisk.has(j.id) || j.durable === false) continue;
      if (G.written.has(j.id)) lost.push(j);
      else out.push(j);
    }
    for (const j of out) {
      if (G.jobs.get(j.id) === j) { j.owner = { ...ME }; G.written.add(j.id); }
    }
    writeJobs(out);
  });
  for (const j of lost) cancelLocal(j, "deleted or taken by another opencode process");
}

function putJob(job: Job) {
  G.jobs.set(job.id, job);
  save();
}

function dropJob(id: string) {
  G.timers.get(id)?.cancel();
  G.timers.delete(id);
  G.written.delete(id);
  if (G.jobs.delete(id)) save();
}

// Stops a job here without reporting it: another process deleted or owns it.
function cancelLocal(j: Job, why: string) {
  G.timers.get(j.id)?.cancel();
  G.timers.delete(j.id);
  G.jobs.delete(j.id);
  G.written.delete(j.id);
  if (j.kind === "monitor") {
    j.stopped = true;
    const child = G.procs.get(j.id);
    if (child?.pid) killGroup(child.pid);
  } else if (j.kind === "workflow") {
    G.runs.get(j.id)?.abort.abort();
  }
  log(`job ${j.id} stopped here: ${why}`);
}

// Jobs other live processes own, read from jobs.json.
function foreignJobs(): Job[] {
  return loadJobs().filter((j) => !G.jobs.has(j.id));
}

function allJobs(): Job[] {
  return [...G.jobs.values(), ...foreignJobs()];
}

// Deletes another process's job from jobs.json; its owner cancels it on its next sync.
function removeForeign(id: string): Job | undefined {
  let found: Job | undefined;
  withLock(() => {
    const disk = loadJobs();
    const i = disk.findIndex((j) => j.id === id);
    if (i < 0) return;
    found = disk[i];
    disk.splice(i, 1);
    writeJobs(disk);
  });
  return found;
}

function primaryAlive() {
  try {
    const p = JSON.parse(readFileSync(PRIMARY_FILE, "utf-8"));
    return !sameOwner(p) && ownerAlive(p);
  } catch {
    return false;
  }
}

// Takes over jobs whose owner died, and arms them here.
function adoptOrphans() {
  if (!MAY_ADOPT || (!PRIMARY && primaryAlive())) return;
  const adopted: Job[] = [];
  withLock(() => {
    const disk = loadJobs();
    for (const j of disk) {
      if (G.jobs.has(j.id) || ownerAlive(j.owner)) continue;
      j.owner = { ...ME };
      adopted.push(j);
    }
    if (adopted.length) writeJobs(disk);
  });
  for (const j of adopted) {
    G.jobs.set(j.id, j);
    G.written.add(j.id);
  }
  for (const j of adopted) rearm(j);
  if (adopted.length) log(`adopted ${adopted.length} jobs`);
}

// setTimeout caps at 2^31 ms (about 24.8 days); longer delays are chained.
function longTimeout(id: string, ms: number, fn: () => void) {
  let handle: any;
  let cancelled = false;
  const step = (left: number) => {
    if (cancelled) return;
    if (left > MAX_TIMEOUT) handle = setTimeout(() => step(left - MAX_TIMEOUT), MAX_TIMEOUT);
    else handle = setTimeout(() => { G.timers.delete(id); fn(); }, Math.max(0, left));
  };
  G.timers.get(id)?.cancel();
  G.timers.set(id, { cancel: () => { cancelled = true; clearTimeout(handle); } });
  step(ms);
}

function clip(text: string, max: number) {
  if (text.length <= max) return text;
  return `[... ${text.length - max} earlier characters cut ...]\n` + text.slice(text.length - max);
}

function esc(v: unknown) {
  return String(v).replace(/"/g, "'").replace(/\n/g, " ");
}

function tailFile(path: string, lines: number, maxBytes = 256 * 1024): string {
  try {
    const size = statSync(path).size;
    const start = Math.max(0, size - maxBytes);
    const fd = openSync(path, "r");
    const buf = Buffer.alloc(size - start);
    readSync(fd, buf, 0, buf.length, start);
    closeSync(fd);
    const all = buf.toString("utf-8").split("\n");
    if (all.length && all[all.length - 1] === "") all.pop();
    return all.slice(-lines).join("\n");
  } catch {
    return "";
  }
}

function pidAlive(pid: number) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function killGroup(pid: number) {
  for (const target of [-pid, pid]) {
    try { process.kill(target, "SIGTERM"); } catch {}
  }
  setTimeout(() => {
    for (const target of [-pid, pid]) {
      try { process.kill(target, "SIGKILL"); } catch {}
    }
  }, 5000).unref?.();
}

// ---------------------------------------------------------------- delivery

function clientFor(directory: string) {
  return G.clients.get(directory) ?? G.clients.values().next().value;
}

// Every job reports through here: one message into the session that owns it. A busy session
// queues it; an idle one starts a new turn.
async function deliver(job: { session: string; directory: string; agent?: string }, text: string) {
  const client = clientFor(job.directory);
  if (!client) {
    log(`deliver: no client for ${job.directory}`);
    return false;
  }
  try {
    const body: any = { parts: [{ type: "text", text }] };
    if (job.agent) body.agent = job.agent;
    sentByUs(text);
    const r = await client.session.promptAsync({
      path: { id: job.session },
      query: { directory: job.directory },
      body,
    });
    const status = r?.response?.status;
    if (status && status >= 400) {
      log(`deliver: ${job.session} HTTP ${status}`);
      return false;
    }
    return true;
  } catch (e: any) {
    log(`deliver: ${job.session} failed: ${e?.message ?? e}`);
    return false;
  }
}

function tag(kind: string, attrs: Record<string, unknown>, body: string) {
  const a = Object.entries(attrs)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => ` ${k}="${esc(v)}"`)
    .join("");
  return `<${kind}${a}>\n${body}\n</${kind}>`;
}

// ---------------------------------------------------------------- cron

const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
const DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
const ALIASES: Record<string, string> = {
  "@yearly": "0 0 1 1 *", "@annually": "0 0 1 1 *", "@monthly": "0 0 1 * *",
  "@weekly": "0 0 * * 0", "@daily": "0 0 * * *", "@midnight": "0 0 * * *", "@hourly": "0 * * * *",
};

function cronField(spec: string, lo: number, hi: number, names?: string[]): Set<number> {
  const out = new Set<number>();
  const val = (s: string) => {
    const i = names ? names.indexOf(s.toLowerCase()) : -1;
    const n = i >= 0 ? i + lo : Number(s);
    if (!Number.isInteger(n)) throw new Error(`bad cron value "${s}"`);
    return n;
  };
  for (const part of spec.split(",")) {
    const [range, stepS] = part.split("/");
    const step = stepS ? Number(stepS) : 1;
    if (!Number.isInteger(step) || step < 1) throw new Error(`bad cron step "${part}"`);
    let a = lo, b = hi;
    if (range !== "*") {
      const [x, y] = range.split("-");
      a = val(x);
      b = y !== undefined ? val(y) : stepS ? hi : a;
    }
    if (a < lo || b > hi || a > b) throw new Error(`cron value out of range "${part}"`);
    for (let n = a; n <= b; n += step) out.add(n);
  }
  return out;
}

function parseCron(expr: string) {
  const e = ALIASES[expr.trim().toLowerCase()] ?? expr.trim();
  const f = e.split(/\s+/);
  if (f.length !== 5) throw new Error(`cron needs 5 fields (minute hour day-of-month month day-of-week), got "${expr}"`);
  // Day of week runs 0-7: 0 and 7 are both Sunday, so 1-7 and 5-7 are valid ranges.
  const dow = new Set([...cronField(f[4], 0, 7, DAYS)].map((d) => d % 7));
  return {
    min: cronField(f[0], 0, 59), hour: cronField(f[1], 0, 23), dom: cronField(f[2], 1, 31),
    mon: cronField(f[3], 1, 12, MONTHS), dow, domStar: f[2] === "*", dowStar: f[4] === "*",
  };
}

// Next local time strictly after `after` that matches. Day-of-month and day-of-week OR together
// when both are restricted, as in Vixie cron.
function nextCron(expr: string, after: Date = new Date()): Date {
  const c = parseCron(expr);
  const d = new Date(after.getTime());
  d.setSeconds(0, 0);
  d.setMinutes(d.getMinutes() + 1);
  for (let guard = 0; guard < 600000; guard++) {
    if (!c.mon.has(d.getMonth() + 1)) {
      d.setMonth(d.getMonth() + 1, 1);
      d.setHours(0, 0, 0, 0);
      continue;
    }
    const domOk = c.dom.has(d.getDate()), dowOk = c.dow.has(d.getDay());
    const dayOk = c.domStar && c.dowStar ? true : c.domStar ? dowOk : c.dowStar ? domOk : domOk || dowOk;
    if (!dayOk) {
      d.setDate(d.getDate() + 1);
      d.setHours(0, 0, 0, 0);
      continue;
    }
    if (!c.hour.has(d.getHours())) {
      d.setHours(d.getHours() + 1, 0, 0, 0);
      continue;
    }
    if (!c.min.has(d.getMinutes())) {
      d.setMinutes(d.getMinutes() + 1, 0, 0);
      continue;
    }
    return d;
  }
  throw new Error(`cron "${expr}" never fires`);
}

// ---------------------------------------------------------------- arming

function armWakeup(job: Job) {
  const late = Date.now() - job.fire_at;
  longTimeout(job.id, job.fire_at - Date.now(), async () => {
    dropJob(job.id);
    const lateBy = late > 60000 ? `${Math.round(late / 60000)}m (server was down)` : undefined;
    await deliver(job, tag("wakeup", { id: job.id, reason: job.reason, late_by: lateBy }, job.prompt));
  });
}

function armCron(job: Job) {
  let next = job.next_at;
  if (!next || next < Date.now() - 60000) {
    if (!job.recurring && next) {
      // A one-shot that came due while the server was down fires once, now.
      next = Date.now();
    } else {
      next = nextCron(job.cron).getTime();
    }
  }
  job.next_at = next;
  G.jobs.set(job.id, job);
  save();
  longTimeout(job.id, next - Date.now(), async () => {
    job.fired = (job.fired ?? 0) + 1;
    if (job.recurring) {
      job.next_at = nextCron(job.cron).getTime();
      armCron(job);
    } else {
      dropJob(job.id);
    }
    await deliver(job, tag("cron", { id: job.id, schedule: job.cron, fire: job.fired }, job.prompt));
  });
}

function shellPaths(id: string) {
  const dir = join(STATE_DIR, "shells");
  mkdirSync(dir, { recursive: true });
  return { log: join(dir, `${id}.log`), code: join(dir, `${id}.code`) };
}

// A background shell writes its exit code to a file, so its end is seen even across a server
// restart (the process is detached and survives one).
function watchShell(job: Job) {
  const { log: logPath, code } = shellPaths(job.id);
  const poll = setInterval(async () => {
    let exit: string | undefined;
    if (existsSync(code)) exit = readFileSync(code, "utf-8").trim();
    else if (!pidAlive(job.pid)) {
      await new Promise((r) => setTimeout(r, 500));
      exit = existsSync(code) ? readFileSync(code, "utf-8").trim() : "killed";
    }
    if (exit === undefined) return;
    clearInterval(poll);
    G.timers.delete(job.id);
    job.exit = exit;
    job.ended_at = Date.now();
    dropJob(job.id);
    if (job.notify === false) return;
    const tail = clip(tailFile(logPath, 40), 4000);
    const secs = Math.round((job.ended_at - job.started_at) / 1000);
    await deliver(job, tag("bg_shell", { id: job.id, state: "exited", exit_code: exit, seconds: secs, log: logPath },
      `$ ${job.command}\n--- last lines ---\n${tail || "(no output)"}`));
  }, 2000);
  G.timers.set(job.id, { cancel: () => clearInterval(poll) });
}

function startMonitor(job: Job, restarted = false) {
  const shell = "/bin/bash";
  const child = spawn(shell, ["-c", job.command], {
    cwd: job.workdir || job.directory,
    detached: true,
    stdio: ["ignore", "pipe", "pipe"],
    env: process.env,
  });
  job.pid = child.pid;
  job.started_at ??= Date.now();
  G.jobs.set(job.id, job);
  save();
  G.procs.set(job.id, child);
  let buf = "";
  let pending: string[] = [];
  let flushTimer: any = null;
  let deliveries: number[] = [];
  let dropped = 0;
  const stderr: string[] = [];
  const recent: string[] = (G as any).recent?.[job.id] ?? [];
  ((G as any).recent ??= {})[job.id] = recent;
  const flush = async () => {
    flushTimer = null;
    if (!pending.length) return;
    let lines = pending;
    pending = [];
    if (lines.length > 80) {
      dropped += lines.length - 80;
      lines = lines.slice(-80);
    }
    const note = dropped ? `[${dropped} earlier lines dropped]\n` : "";
    dropped = 0;
    deliveries.push(Date.now());
    await deliver(job, tag("monitor", { id: job.id, description: job.description, event: "output" },
      note + clip(lines.join("\n"), 6000)));
  };
  const window = () => {
    // Noisy monitors get wider batching windows instead of flooding the session.
    const now = Date.now();
    deliveries = deliveries.filter((t) => now - t < 300000);
    return deliveries.length >= 20 ? 30000 : 2000;
  };
  child.stdout.on("data", (chunk: Buffer) => {
    buf += chunk.toString("utf-8");
    const parts = buf.split("\n");
    buf = parts.pop() ?? "";
    for (const line of parts) if (line.trim()) { pending.push(line); recent.push(line); }
    if (recent.length > 50) recent.splice(0, recent.length - 50);
    if (pending.length && !flushTimer) flushTimer = setTimeout(flush, window());
  });
  child.stderr.on("data", (chunk: Buffer) => {
    stderr.push(...chunk.toString("utf-8").split("\n").filter(Boolean));
    if (stderr.length > 20) stderr.splice(0, stderr.length - 20);
  });
  let timeout: any = null;
  if (job.deadline && !job.persistent) {
    timeout = setTimeout(() => {
      job.timed_out = true;
      killGroup(child.pid!);
    }, Math.max(0, job.deadline - Date.now()));
  }
  child.on("exit", async (code: number | null, signal: string | null) => {
    if (timeout) clearTimeout(timeout);
    if (buf.trim()) pending.push(buf);
    buf = "";
    if (flushTimer) clearTimeout(flushTimer);
    await flush();
    G.procs.delete(job.id);
    if (job.stopped) return;
    dropJob(job.id);
    const state = job.timed_out ? "timed_out" : "exited";
    const err = stderr.length ? `\n--- stderr (last lines) ---\n${stderr.join("\n")}` : "";
    await deliver(job, tag("monitor", {
      id: job.id, description: job.description, event: state,
      exit_code: code ?? "", signal: signal ?? "",
      minutes: Math.round((Date.now() - job.started_at) / 60000),
    }, `The monitored command ended.${err}`));
  });
  if (restarted) {
    deliver(job, tag("monitor", { id: job.id, description: job.description, event: "restarted" },
      "The opencode server restarted, so this monitor's command was started again."));
  }
}

function stopMonitor(id: string) {
  const job = G.jobs.get(id);
  const child = G.procs.get(id);
  if (job) job.stopped = true;
  if (child?.pid) killGroup(child.pid);
  else if (job?.pid) killGroup(job.pid);
  dropJob(id);
}

// ---------------------------------------------------------------- sessions: waiting and results

function waitIdle(sessionID: string, directory: string, startedAt: number, signal?: AbortSignal) {
  return new Promise<{ error?: string }>((resolveWait) => {
    let done = false;
    const finish = (r: { error?: string }) => {
      if (done) return;
      done = true;
      clearInterval(poll);
      const list = G.waiters.get(sessionID) ?? [];
      G.waiters.set(sessionID, list.filter((f) => f !== finish));
      resolveWait(r);
    };
    const list = G.waiters.get(sessionID) ?? [];
    list.push(finish);
    G.waiters.set(sessionID, list);
    signal?.addEventListener("abort", () => finish({ error: "aborted" }));
    // Events can be missed (another instance, a reconnect); a slow poll closes the gap.
    const poll = setInterval(async () => {
      try {
        const client = clientFor(directory);
        const st = await client.session.status({ query: { directory } });
        const s = st?.data?.[sessionID];
        if (s && s.type !== "idle") return;
        const last = await lastAssistant(sessionID, directory);
        if (!startedAt || (last && (last.info.time?.created ?? 0) >= startedAt - 1000)) finish({});
      } catch {}
    }, 15000);
  });
}

// The newest assistant message, read around any schema prompt (readSession).
async function lastAssistant(sessionID: string, directory: string) {
  const isReply = (m: any) => m?.info?.role === "assistant";
  for (const want of [1, 16, 64]) {
    const { msgs, hidden, error } = await readSession(clientFor(directory), sessionID, directory, want, isReply);
    for (let i = msgs.length - 1; i >= 0; i--) if (isReply(msgs[i])) return msgs[i];
    if (error) throw new Error(`could not read session ${sessionID}: ${error}`);
    if (msgs.length + hidden < want) return undefined;
  }
  return undefined;
}

function textOf(msg: any) {
  if (!msg) return "";
  return (msg.parts ?? [])
    .filter((p: any) => p.type === "text" && !p.synthetic && !p.ignored)
    .map((p: any) => p.text)
    .join("\n")
    .trim();
}

function errorOf(msg: any) {
  const e = msg?.info?.error;
  if (!e) return undefined;
  return e.data?.message ?? e.name ?? "error";
}

function splitModel(model?: string) {
  if (!model) return undefined;
  const i = model.indexOf("/");
  if (i < 0) return { providerID: "deepseek", modelID: model };
  return { providerID: model.slice(0, i), modelID: model.slice(i + 1) };
}

async function finishAgent(job: Job) {
  // Once per round, and only while this process still tracks the job.
  const key = `${job.id}#${job.round}`;
  if (G.jobs.get(job.id) !== job || G.reported.has(key)) return;
  G.reported.add(key);
  let text = "", error: string | undefined;
  try {
    const last = await lastAssistant(job.id, job.directory);
    text = textOf(last);
    error = errorOf(last);
    if (!last || !(last.info.time?.completed)) error ??= "the agent stopped before finishing";
  } catch (e: any) {
    error = e?.message ?? String(e);
  }
  dropJob(job.id);
  const state = error ? "error" : "completed";
  const body = [
    `<summary>${state === "completed" ? "Background task completed" : "Background task failed"}: ${job.description}</summary>`,
    `<task_${state === "error" ? "error" : "result"}>`,
    clip(error ? `${error}\n${text}`.trim() : text || "(no text reply)", 30000),
    `</task_${state === "error" ? "error" : "result"}>`,
  ].join("\n");
  await deliver({ session: job.parent, directory: job.parent_directory ?? job.directory, agent: job.agent },
    `<task id="${job.id}" state="${state}">\n${body}\n</task>`);
}

function trackAgent(job: Job) {
  G.jobs.set(job.id, job);
  save();
  waitIdle(job.id, job.directory, job.started_at).then(() => finishAgent(job));
}

// ---------------------------------------------------------------- workflow runtime

type AgentOpts = {
  agent?: string; schema?: any; model?: string; variant?: string; label?: string;
  cwd?: string; think?: boolean; retries?: number; readonly?: boolean;
};

function hash(s: string) {
  return createHash("sha256").update(s).digest("hex").slice(0, 16);
}

// Light JSON-schema check for the think:true path: object/array/scalar types, required keys
// and enum. The server's json_schema format does the full job on the default path.
function checkSchema(value: any, schema: any, path = "$"): string | undefined {
  if (!schema || typeof schema !== "object") return undefined;
  const t = schema.type;
  const types = Array.isArray(t) ? t : t ? [t] : [];
  const kind = value === null ? "null" : Array.isArray(value) ? "array" : typeof value;
  if (types.length) {
    const ok = types.some((x: string) => x === kind || (x === "integer" && Number.isInteger(value)) ||
      (x === "number" && kind === "number"));
    if (!ok) return `${path} should be ${types.join("|")}, got ${kind}`;
  }
  if (schema.enum && !schema.enum.some((e: any) => JSON.stringify(e) === JSON.stringify(value)))
    return `${path} not in enum`;
  if (kind === "object") {
    for (const k of schema.required ?? []) if (!(k in value)) return `${path}.${k} missing`;
    for (const [k, sub] of Object.entries(schema.properties ?? {}))
      if (k in value) { const e = checkSchema(value[k], sub, `${path}.${k}`); if (e) return e; }
  }
  if (kind === "array" && schema.items)
    for (let i = 0; i < value.length; i++) { const e = checkSchema(value[i], schema.items, `${path}[${i}]`); if (e) return e; }
  return undefined;
}

function parseJsonText(text: string) {
  const fence = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  const body = (fence ? fence[1] : text).trim();
  try { return JSON.parse(body); } catch {}
  const a = body.search(/[\[{]/);
  if (a >= 0) {
    const closer = body[a] === "{" ? "}" : "]";
    const b = body.lastIndexOf(closer);
    if (b > a) return JSON.parse(body.slice(a, b + 1));
  }
  throw new Error("reply was not JSON");
}

async function runWorkflow(opts: {
  run: string; code: string; isModule: boolean; scriptPath?: string; args: any;
  session: string; directory: string; signal: AbortSignal; ledger: VerdictLedger;
}) {
  const runDir = join(STATE_DIR, "workflows", opts.run);
  mkdirSync(runDir, { recursive: true });
  const journalPath = join(runDir, "journal.jsonl");
  const logPath = join(runDir, "log.txt");
  const journal = new Map<string, any>();
  if (existsSync(journalPath)) {
    for (const line of readFileSync(journalPath, "utf-8").split("\n")) {
      if (!line.trim()) continue;
      try { const e = JSON.parse(line); if (e.ok) journal.set(e.key, e.result); } catch {}
    }
  }
  const seen = new Map<string, number>();
  const stats = { agents: 0, cached: 0, failed: 0 };
  // Where the script is: its phase, and whether it is in a verify_until_pass verify or fix
  // stage (and which call and round). Each parallel() thunk and each stage gets its own copy, so
  // concurrent units never see each other's phase or round.
  const scope = new AsyncLocalStorage<Marks>();
  const top: Marks = { phase: "", inVerify: false, inFix: false };
  const here = () => scope.getStore() ?? top;
  const within = <T>(over: Partial<Marks>, fn: () => T): T => scope.run({ ...here(), ...over }, fn);
  let loops = 0;
  const vt: VerifyTrail = { objects: new WeakSet(), json: new Set() };
  const ledger = opts.ledger;
  const client = clientFor(opts.directory);
  const children = new Set<string>();
  opts.signal.addEventListener("abort", () => {
    for (const id of children) client.session.abort({ path: { id }, query: { directory: opts.directory } }).catch(() => {});
  });
  const wlog = (...parts: any[]) => {
    const line = parts.map((p) => (typeof p === "string" ? p : JSON.stringify(p))).join(" ");
    appendFileSync(logPath, `${new Date().toISOString()} ${line}\n`);
  };
  const phase = (name: string) => { here().phase = String(name ?? ""); wlog(`== phase: ${name}`); };

  async function agent(prompt: string, o: AgentOpts = {}) {
    // A read-only agent (verdictAgent) outside a fix stage: any fail it returns counts. It is a
    // verify agent, whose pass counts too, inside a phase named verify or a verify stage. A
    // verifier or reviewer by type is judged as one wherever it runs: a reply naming no verdict,
    // or no reply, is a fail even outside a verify phase.
    const m = here();
    const judged = verdictAgent(o) && !m.inFix;
    const verifying = judged && (m.inVerify || verifyPhase(m.phase));
    const byType = judged && VERIFY_TYPES.has(agentName(o.agent));
    // The verify_until_pass call and round this agent belongs to, fixed when it starts.
    const at = verifying ? m.loop : undefined;
    try {
      // A verify agent always runs live: a verdict replayed from the journal is no verification.
      const { result, cached } = await runAgent(prompt, o, verifying);
      // A verify agent's reply that names no verdict is a fail: a verifier that cannot say pass
      // has not passed.
      if (verifying && !cached) ledger.add(noteVerifyResult(vt, m.round, replyVerdicts(result, true)), at?.id, at?.round);
      // Any other read-only agent's fail counts, replayed or not, and its pass never does.
      else if (judged) ledger.add(replyVerdicts(result, byType).filter((v) => !isPass(v)));
      return result;
    } catch (e: any) {
      if (verifying || byType) ledger.add([{ verdict: "fail", reason: `the verify agent did not finish: ${e?.message ?? e}` }], at?.id, at?.round);
      throw e;
    }
  }

  async function runAgent(prompt: string, o: AgentOpts, live: boolean): Promise<{ result: any; cached: boolean }> {
    if (opts.signal.aborted) throw new Error("workflow aborted");
    const base = hash(JSON.stringify([prompt, o.agent ?? "", o.schema ?? null, o.model ?? "", o.think ?? false, ...(o.readonly ? [true] : [])]));
    const n = (seen.get(base) ?? 0) + 1;
    seen.set(base, n);
    const key = `${base}#${n}`;
    const label = o.label ?? prompt.slice(0, 60).replace(/\s+/g, " ");
    if (journal.has(key) && !live) {
      stats.cached++;
      wlog(`agent (journal) ${label}`);
      return { result: journal.get(key), cached: true };
    }
    stats.agents++;
    const directory = o.cwd ? resolve(opts.directory, o.cwd) : opts.directory;
    const created = await client.session.create({
      body: { parentID: opts.session, title: `${label} (workflow ${opts.run})` },
      query: { directory },
    });
    const id = created?.data?.id;
    if (!id) throw new Error(`could not create agent session: ${JSON.stringify(created?.error ?? {})}`);
    children.add(id);
    guards.set(id, { ...guardOf(id), parent: opts.session, created: Date.now(), workflow: opts.run });
    const readonly = o.readonly ? "readonly: true" : READONLY_AGENTS.has(agentName(o.agent)) ? `@${agentName(o.agent)}` : undefined;
    if (readonly) markReadonly(id, readonly);
    const lead = readonly ? "You are read-only: every edit, file write and git write is refused. Read, run read-only checks, and report.\n\n" : "";
    const attempts = (o.retries ?? 2) + 1;
    let lastErr = "";
    for (let attempt = 1; attempt <= attempts; attempt++) {
      let text = lead + prompt;
      if (attempt > 1) text = `Your previous reply failed: ${lastErr}. Try again.\n\n${lead}${prompt}`;
      const body: any = { agent: o.agent ?? "general", parts: [{ type: "text", text }] };
      const model = splitModel(o.model);
      if (model) body.model = model;
      if (o.variant) body.variant = o.variant;
      if (o.schema && !o.think) {
        // opencode 1.19.5 cannot list a message sent with this format, so the plugin names the
        // message itself and records it: its own reads page around it (readSession).
        body.format = { type: "json_schema", schema: o.schema };
        body.variant = o.variant ?? "nothink";
        const mid = messageId();
        body.messageID = mid.id;
        noteSchemaPrompt(id, mid.id, mid.time);
      } else if (o.schema) {
        body.parts[0].text += `\n\nReply with only a JSON value matching this JSON schema, no prose:\n${JSON.stringify(o.schema)}`;
      }
      const started = Date.now();
      sentByUs(body.parts[0].text);
      wlog(`agent start ${label} session=${id} attempt=${attempt}`);
      const r = await client.session.promptAsync({ path: { id }, query: { directory }, body });
      if (r?.response?.status && r.response.status >= 400) throw new Error(`prompt rejected: HTTP ${r.response.status} ${JSON.stringify(r.error ?? {})}`);
      const w = await waitIdle(id, directory, started, opts.signal);
      if (w.error === "aborted") throw new Error("workflow aborted");
      const last = await lastAssistant(id, directory);
      const err = errorOf(last);
      let result: any;
      try {
        if (err) throw new Error(err);
        if (o.schema && !o.think) {
          result = last?.info?.structured;
          if (result === undefined) result = parseJsonText(textOf(last));
        } else if (o.schema) {
          result = parseJsonText(textOf(last));
        } else {
          result = textOf(last);
        }
        if (o.schema) {
          const bad = checkSchema(result, o.schema);
          if (bad) throw new Error(`schema mismatch: ${bad}`);
        }
      } catch (e: any) {
        lastErr = e?.message ?? String(e);
        wlog(`agent fail ${label}: ${lastErr}`);
        continue;
      }
      journal.set(key, result);
      appendFileSync(journalPath, JSON.stringify({ key, label, ok: true, session: id, result, prompt, schema: !!o.schema && !o.think }) + "\n");
      wlog(`agent done ${label}`);
      return { result, cached: false };
    }
    stats.failed++;
    appendFileSync(journalPath, JSON.stringify({ key, label, ok: false, session: id, error: lastErr, prompt, schema: !!o.schema && !o.think }) + "\n");
    throw new Error(`agent "${label}" failed: ${lastErr}`);
  }

  async function parallel<T>(thunks: Array<() => Promise<T>>, o: { limit?: number; settle?: boolean } = {}) {
    const limit = Math.max(1, o.limit ?? 8);
    const out: any[] = new Array(thunks.length);
    let next = 0;
    const worker = async () => {
      while (next < thunks.length) {
        const i = next++;
        try {
          out[i] = await within({}, () => thunks[i]());
        } catch (e: any) {
          if (!o.settle) throw e;
          out[i] = { error: e?.message ?? String(e) };
        }
      }
    };
    await Promise.all(Array.from({ length: Math.min(limit, thunks.length) }, worker));
    return out as T[];
  }

  async function pipeline(input: any, ...stages: Array<(x: any) => any>) {
    let v = input;
    for (const s of stages) v = await s(v);
    return v;
  }

  async function sh(cmd: string, o: { cwd?: string; timeout_ms?: number } = {}) {
    const cwd = o.cwd ? resolve(opts.directory, o.cwd) : opts.directory;
    let refused: string | undefined;
    try {
      refused = await guardCall({ tool: "bash", args: { command: cmd }, session: opts.session, directory: cwd }, client, false);
    } catch (e: any) {
      refused = GUARD_BROKE(e);
    }
    if (refused) {
      wlog(`sh refused: ${refused}`);
      return { code: 126, stdout: "", stderr: refused };
    }
    return new Promise<{ code: number; stdout: string; stderr: string }>((res) => {
      execFile("/bin/bash", ["-o", "pipefail", "-c", cmd], {
        cwd,
        timeout: o.timeout_ms ?? 0, maxBuffer: 64 * 1024 * 1024,
      }, (err: any, stdout, stderr) => {
        res({ code: err ? (typeof err.code === "number" ? err.code : 1) : 0, stdout: String(stdout), stderr: String(stderr) });
      });
    });
  }

  // Verify, and while any verdict fails: fix with the failures, then verify again with fresh
  // agents, for at most `max` fix rounds. Each round's verdicts go to the commit gate, and a
  // round that passes supersedes this call's earlier rounds, and nothing else.
  async function verify_until_pass(
    fixStage: (failures: any[], ctx: { round: number; verdicts: any[] }) => any,
    verifyStage: (ctx: { round: number; failures: any[] }) => any,
    o: { max?: number } = {},
  ) {
    if (typeof fixStage !== "function" || typeof verifyStage !== "function") {
      throw new Error("verify_until_pass(fixStage, verifyStage, {max}) takes two functions");
    }
    const max = Math.max(0, Math.floor(o.max ?? 3));
    const rounds: Array<{ round: number; verdicts: any[]; fix?: any }> = [];
    let failures: any[] = [], last: any[] = [];
    // Each stage runs in its own scope: the script's phase is untouched, and a call running
    // beside this one (parallel units) keeps its own round.
    const loop = ++loops;
    for (let round = 1; ; round++) {
      const mine: RoundTrail = { objects: new WeakSet(), json: new Map() };
      const name = `verify (round ${round})`;
      wlog(`== phase: ${name}`);
      const raw = collectVerdicts(await within({ phase: name, inVerify: true, round: mine, loop: { id: loop, round } },
        () => verifyStage({ round, failures })), true);
      // A fail counts from anywhere; a pass only when a verify agent returned it in this round.
      const verdicts = raw.filter((v) => !isPass(v) || fromRound(mine, v));
      if (raw.length > verdicts.length) wlog(`verify round ${round}: ${raw.length - verdicts.length} pass verdicts no verify agent returned were ignored`);
      // A verdict the plugin read from a verify agent's prose, or the fail it gave one that named
      // none, counts in this round whether or not the stage returned the reply.
      for (const e of ledger.entries) {
        if (e.loop === loop && e.round === round && MADE.has(e.v) && !verdicts.includes(e.v)) verdicts.push(e.v);
      }
      if (!verdicts.length) {
        throw new Error(`verify_until_pass: round ${round}'s verify stage returned no verdict from a verify agent; ` +
          `start read-only agents there (agent: "verifier" or readonly: true) and return the objects they returned, each with verdict: "pass" or "fail"`);
      }
      failures = verdicts.filter((v) => !isPass(v));
      ledger.add(verdicts, loop, round);
      ledger.roundDone(loop, round);
      last = verdicts;
      rounds.push({ round, verdicts });
      wlog(`verify round ${round}: ${verdicts.length - failures.length} pass, ${failures.length} fail`);
      if (!failures.length || round > max) break;
      wlog(`== phase: fix (round ${round})`);
      const fv = failures;
      rounds[rounds.length - 1].fix = await within({ phase: `fix (round ${round})`, inFix: true, inVerify: false, round: undefined, loop: undefined },
        () => fixStage(fv, { round, verdicts }));
    }
    return { passed: failures.length === 0, verdicts: last, failures, rounds };
  }

  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
  const api = { agent, parallel, pipeline, sh, log: wlog, phase, args: opts.args, sleep, run: opts.run, verify_until_pass };
  let result: any;
  if (opts.isModule && opts.scriptPath) {
    const mod = await import(pathToFileURL(opts.scriptPath).href + `?t=${Date.now()}`);
    const fn = mod.default ?? mod.run ?? mod.main;
    if (typeof fn !== "function") throw new Error("workflow module has no default export function");
    result = await fn(api);
  } else {
    const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
    const fn = new AsyncFunction(...Object.keys(api), opts.code);
    result = await fn(...Object.values(api));
  }
  return { result, stats, trail: vt };
}

// What verify agents returned in one run: the objects themselves and their verdicts as JSON
// (so a copied verdict is still known as theirs).
// RoundTrail: what verify agents returned in one verify_until_pass round; a copy counts once per
// verdict a verify agent returned, so an earlier round's pass cannot be replayed.
type RoundTrail = { objects: WeakSet<object>; json: Map<string, number> };
type VerifyTrail = { objects: WeakSet<object>; json: Set<string> };
// Where a workflow script is (runWorkflow's scope): loop is the verify_until_pass call and round
// whose verify stage is running, round what its verify agents returned so far.
type Marks = { phase: string; inVerify: boolean; inFix: boolean; round?: RoundTrail; loop?: { id: number; round: number } };

// Notes the verdicts a verify agent returned and gives them back.
function noteVerifyResult(vt: VerifyTrail, round: RoundTrail | undefined, out: any[]): any[] {
  for (const v of out) {
    vt.objects.add(v);
    vt.json.add(JSON.stringify(v));
    if (round) {
      round.objects.add(v);
      const j = JSON.stringify(v);
      round.json.set(j, (round.json.get(j) ?? 0) + 1);
    }
  }
  return out;
}

const fromVerifier = (vt: VerifyTrail, v: any) =>
  v !== null && typeof v === "object" && (vt.objects.has(v) || vt.json.has(JSON.stringify(v)));

function fromRound(r: RoundTrail, v: any): boolean {
  if (v === null || typeof v !== "object") return false;
  const j = JSON.stringify(v), n = r.json.get(j) ?? 0;
  if (n > 0) r.json.set(j, n - 1);
  return n > 0 || r.objects.has(v);
}

// A phase named verify: its name starts with verify, verification, verifier or re-verify.
// Hyphens and underscores read as spaces. What the phase also does is not judged here: only a
// read-only agent's verdict counts, and a read-only agent cannot build or fix.
function verifyPhase(name: string): boolean {
  return /^\W*(re\s?)?verif(y|ying|ication|ications|ier|iers|ies)\b/i.test(String(name).replace(/[-_]+/g, " "));
}

// The agents whose verdict can count: read-only by type or by readonly: true. A builder or
// fixer type never counts, even when started read-only, because it is briefed to change files.
const VERDICT_AGENTS = new Set(["verifier", "reviewer", "structured"]);
const BUILDER_AGENTS = new Set(["worker", "fixer", "build"]);
// Verify agents by type: briefed to judge, so a reply naming no verdict is a fail in any phase.
const VERIFY_TYPES = new Set(["verifier", "reviewer"]);
function verdictAgent(o: AgentOpts): boolean {
  const name = agentName(o.agent);
  if (BUILDER_AGENTS.has(name)) return false;
  return o.readonly === true || VERDICT_AGENTS.has(name);
}

// One workflow run's verify verdicts, as the commit gate reads them. Each verify agent's verdict
// is saved the moment it returns, so a run that throws, is cancelled or crashes afterwards keeps
// it. A verdict stands unless a later round of the same verify_until_pass call passed: phases,
// units and separate calls never supersede each other. A resumed run is a new run here. The run
// is done once it returns; until then (and for ever, if it throws, is cancelled or crashes) its
// record decides over no other run's fail, though its own fails hold.
type Entry = { v: any; loop?: number; round?: number; at: number };
class VerdictLedger {
  entries: Entry[] = [];
  // verify_until_pass call -> its newest round that finished with every verdict pass.
  passed = new Map<number, number>();
  start: number;
  done = false;
  exec: string;
  session: string;
  run: string;
  constructor(session: string, run: string, start = Date.now()) {
    this.session = session;
    this.run = run;
    this.start = start;
    this.exec = `${run}@${this.start}@${Math.random().toString(36).slice(2, 8)}`;
  }

  finish() {
    this.done = true;
    this.save();
  }

  holds(v: any, loop?: number, round?: number, any = false) {
    const j = JSON.stringify(v);
    return this.entries.some((e) => (any || (e.loop === loop && e.round === round)) && (e.v === v || JSON.stringify(e.v) === j));
  }

  add(vs: any[], loop?: number, round?: number) {
    const fresh = vs.filter((v) => v !== null && typeof v === "object" && !this.holds(v, loop, round));
    if (!fresh.length) return;
    const at = Date.now();
    for (const v of fresh) this.entries.push({ v, loop, round, at });
    this.save();
  }

  roundDone(loop: number, round: number) {
    const mine = this.entries.filter((e) => e.loop === loop && e.round === round);
    if (!mine.length || !mine.every((e) => isPass(e.v))) return;
    this.passed.set(loop, Math.max(round, this.passed.get(loop) ?? 0));
    this.save();
  }

  standingEntries() {
    return this.entries.filter((e) => e.loop === undefined || (this.passed.get(e.loop) ?? 0) <= e.round!);
  }

  standing() { return this.standingEntries().map((e) => e.v); }

  save() {
    if (!this.entries.length) return;
    const fails = this.standingEntries().filter((e) => !isPass(e.v));
    const rec: Verdicts = {
      at: fails.length ? Math.max(...fails.map((e) => e.at)) : this.start, start: this.start, run: this.run, exec: this.exec,
      pass: fails.length === 0, done: this.done, failed: fails.map((e) => verdictText(e.v, 2000)),
    };
    const g = guardOf(this.session, true);
    const all = [...(g.verdicts ?? []).filter((x) => x.exec !== this.exec), rec];
    // Every run that still holds the gate is kept; of the rest, the newest 20.
    const holding = all.filter((r) => holds(r, all));
    const rest = all.filter((r) => !holds(r, all)).sort((a, b) => (a.start ?? a.at) - (b.start ?? b.at)).slice(-20);
    g.verdicts = [...holding, ...rest];
    saveGuard(this.session, g);
  }
}

// result.json carries the run's standing verify verdicts. A fail the result carries that no
// verify agent returned is added to them. A pass in the result that no verify agent returned
// (the script's own value, a builder's or fixer's report) is ignored.
function settleVerdicts(result: any, ledger: VerdictLedger, vt: VerifyTrail) {
  const carried = collectVerdicts(Array.isArray(result?.verdicts) ? result.verdicts : result);
  const counted = (v: any) => fromVerifier(vt, v);
  const ignored = carried.filter((v) => isPass(v) && !counted(v)).length;
  ledger.add(carried.filter((v) => !isPass(v) && !counted(v) && !ledger.holds(v, undefined, undefined, true)));
  const verdicts = ledger.standing();
  if (verdicts.length) {
    const plain = result && typeof result === "object" && !Array.isArray(result);
    if (plain && !("verify_verdicts" in result)) result = { ...result, verify_verdicts: verdicts };
    else if (!plain) result = { result, verify_verdicts: verdicts };
  }
  const failed = verdicts.filter((v) => !isPass(v));
  return { result, verdict: verdicts.length ? (failed.length ? "fail" : "pass") : undefined, failed, ignored };
}

// ---------------------------------------------------------------- notify

function notifyDesktop(title: string, message: string) {
  const t = title.replace(/"/g, "'"), m = message.replace(/"/g, "'");
  execFile("/usr/bin/osascript", ["-e", `display notification "${m}" with title "${t}"`], () => {});
  const topic = process.env.PARITY_NTFY_TOPIC;
  if (topic) {
    fetch(`https://ntfy.sh/${encodeURIComponent(topic)}`, {
      method: "POST", body: message, headers: { Title: title },
    }).catch(() => {});
  }
}

// ---------------------------------------------------------------- guards
//
// tool.execute.before refuses a call by throwing; the message reaches the model as the tool's
// error, so each one names the right move. Every session is guarded, subagents included.
// Per-session state (agent, read-only, /ultracode read budget, verify verdicts) lives in
// guard/<session>.json, so the commit gate holds across processes and restarts.

// One run's standing verify verdicts (a workflow run, or one reply of a verifier subagent).
// at: when its newest standing fail arrived (an owner's "ship over it" after that lifts it);
// start: when the run started; done: the run returned.
type Verdicts = { at: number; start?: number; run?: string; exec?: string; round?: number; pass: boolean; done?: boolean; failed: string[] };

// Whether a run's record may decide over another run's fail: only a run that returned. One that
// threw, was cancelled or crashed (or is still going) never re-verified what it did not reach.
const decides = (s: Verdicts) => s.done === true;

// A run's standing fail holds the gate until a done run that started after it arrived produces
// a verify verdict: that run decides. A run started before the fail (a unit run beside it, in
// the background) never lifts it, however late its own verdicts arrive.
function holds(r: Verdicts, all: Verdicts[]): boolean {
  return !r.pass && !all.some((s) => s !== r && decides(s) && (s.exec === undefined || s.exec !== r.exec) && (s.start ?? s.at) >= r.at);
}
type Guard = {
  agent?: string; readonly?: string; ultracode?: boolean; reads?: number; planned?: boolean;
  parent?: string | null; verdicts?: Verdicts[]; override_at?: number; id?: string;
  // When the session was created; a workflow's own agent session (by run); when a verifier or
  // reviewer subagent was last prompted, until its reply is read.
  created?: number; workflow?: string; asked_at?: number;
};

const GUARD_DIR = join(STATE_DIR, "guard");
// Agents read-only by name, whatever their permissions say.
const READONLY_AGENTS = new Set(["reviewer", "verifier", "structured", "explore"]);
const agentName = (name: unknown) => String(name ?? "").trim().replace(/^@/, "").toLowerCase();
const READ_TOOLS = new Set(["read", "grep", "glob", "list", "lsp", "bash", "bg_shell", "monitor", "bg_output", "session_read",
  "webfetch", "websearch", "codesearch"]);
const READ_BUDGET = 5;
const EDIT_TOOLS = new Set(["edit", "write", "apply_patch", "patch", "multiedit"]);
// Tools a read-only agent may not use: they write, or start an agent that could.
const READONLY_DENIED = new Set([...EDIT_TOOLS, "worktree_create", "worktree_remove", "agent_spawn", "agent_send", "fork", "workflow"]);
const guards = ((G as any).guards ??= new Map<string, Guard>()) as Map<string, Guard>;
const ours = ((G as any).ours ??= new Set<string>()) as Set<string>;

function guardFile(session: string) {
  return join(GUARD_DIR, `${session.replace(/[^A-Za-z0-9_-]/g, "_")}.json`);
}

function guardOf(session: string, fresh = false): Guard {
  let g = guards.get(session);
  if (!g || fresh) {
    try { g = { ...(g ?? {}), ...JSON.parse(readFileSync(guardFile(session), "utf-8")) }; } catch { g ??= {}; }
    guards.set(session, g!);
  }
  return g!;
}

function saveGuard(session: string, g: Guard) {
  guards.set(session, g);
  try {
    mkdirSync(GUARD_DIR, { recursive: true });
    const tmp = `${guardFile(session)}.${process.pid}.tmp`;
    // The id, because the file name escapes it: the commit gate finds a descendant's verdicts here.
    writeFileSync(tmp, JSON.stringify({ ...g, id: session }));
    renameSync(tmp, guardFile(session));
  } catch (e: any) {
    log(`guard state for ${session} not saved: ${e?.message ?? e}`);
  }
}

function markReadonly(session: string, why: string) {
  const g = guardOf(session);
  if (g.readonly) return;
  g.readonly = why;
  saveGuard(session, g);
}

// Text the plugin itself sends into a session, so chat.message can tell it from the owner's.
function sentByUs(text: string) {
  ours.add(hash(text));
  if (ours.size > 500) ours.delete(ours.values().next().value!);
}

const home = () => process.env.HOME || homedir();
const atlasMain = () => join(home(), "Developer", "Atlas");

// ---- paths
//
// The Mac's volume is case-insensitive and a path may run through a symlink, so a guarded path
// is compared by canon(): symlinks resolved along its longest existing prefix, then lower-cased.

const GLOB_CHARS = /[*?[]/;
const realCache = new Map<string, string>();

function realish(p: string): string {
  const hit = realCache.get(p);
  if (hit !== undefined) return hit;
  const tail: string[] = [];
  let head = p, out = p;
  for (let k = 0; k < 64; k++) {
    try {
      const r = realpathSync.native(head);
      out = tail.length ? join(r, ...tail.reverse()) : r;
      break;
    } catch {}
    const parent = dirname(head);
    if (parent === head) break;
    tail.push(basename(head));
    head = parent;
  }
  if (realCache.size > 2000) realCache.clear();
  realCache.set(p, out);
  return out;
}

const canon = (p: string) => realish(p).toLowerCase();

function under(p: string, dir: string) {
  return p === dir || p.startsWith(dir.endsWith("/") ? dir : dir + "/");
}

// p is dir or inside it, on this Mac's filesystem.
const underC = (p: string, dir: string) => under(canon(p), canon(dir));

// Scratch a read-only agent may write: /tmp only, so a probe never lands in a real location.
function isTempPath(p: string) {
  const c = canon(p);
  return under(c, "/tmp") || under(c, "/private/tmp");
}

function globRegex(glob: string): RegExp {
  let re = "";
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === "*") {
      if (glob[i + 1] === "*") { re += ".*"; i++; if (glob[i + 1] === "/") i++; }
      else re += "[^/]*";
    } else if (c === "?") re += "[^/]";
    else if (c === "[") {
      const j = glob.indexOf("]", i + 2);
      const cls = j < 0 ? "" : "[" + glob.slice(i + 1, j).replace(/^!/, "^").replace(/\\/g, "\\\\") + "]";
      let ok = !!cls;
      if (ok) { try { new RegExp(cls); } catch { ok = false; } }
      if (ok) { re += cls; i = j; } else re += "\\[";
    } else re += c.replace(/[.+^${}()|\\\]]/g, "\\$&");
  }
  try {
    return new RegExp(`^${re}$`, "i");
  } catch {
    return new RegExp(`^${glob.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`, "i");
  }
}

// The existing files a shell glob names, as the shell expands it (a wildcard skips dot entries
// unless the segment starts with a dot). Bounded, so a sweeping pattern cannot stall a call.
function expandGlob(pattern: string, budget = 4000): string[] {
  let paths = ["/"];
  for (const seg of pattern.split("/").filter(Boolean)) {
    if (!paths.length || budget <= 0) break;
    if (!GLOB_CHARS.test(seg)) { paths = paths.map((p) => join(p, seg)); continue; }
    const next: string[] = [];
    const dot = seg.startsWith(".");
    if (seg === "**") {
      const stack = [...paths];
      while (stack.length && budget > 0) {
        const d = stack.pop()!;
        next.push(d);
        try {
          for (const e of readdirSync(d, { withFileTypes: true })) {
            if (--budget <= 0) break;
            if (e.isDirectory() && !e.name.startsWith(".")) stack.push(join(d, e.name));
          }
        } catch {}
      }
    } else {
      const re = globRegex(seg);
      for (const d of paths) {
        try {
          for (const n of readdirSync(d)) {
            if (--budget <= 0) break;
            if ((dot || !n.startsWith(".")) && re.test(n)) next.push(join(d, n));
          }
        } catch {}
      }
    }
    paths = next;
  }
  return paths.filter((p) => existsSync(p)).slice(0, 2000);
}

// A shell word with its braces expanded: {a,b} gives two words.
function braceExpand(word: string, cap = 64): string[] {
  let depth = 0, start = -1;
  for (let i = 0; i < word.length; i++) {
    const c = word[i];
    if (c === "{" && word[i - 1] !== "$") { if (depth++ === 0) start = i; }
    else if (c === "}" && depth > 0 && --depth === 0) {
      const inner = word.slice(start + 1, i);
      const parts: string[] = [];
      let d = 0, last = 0;
      for (let k = 0; k < inner.length; k++) {
        if (inner[k] === "{") d++;
        else if (inner[k] === "}") d--;
        else if (inner[k] === "," && d === 0) { parts.push(inner.slice(last, k)); last = k + 1; }
      }
      parts.push(inner.slice(last));
      if (parts.length < 2) continue;
      const out: string[] = [];
      for (const p of parts) {
        for (const e of braceExpand(word.slice(0, start) + p + word.slice(i + 1), cap)) {
          out.push(e);
          if (out.length >= cap) return out;
        }
      }
      return out;
    }
  }
  return [word];
}

type Vars = Map<string, string>;

// ~user is that user's home, as the shell finds it: /var/root for root, else /Users/<user>.
const userHome = (name: string) => (name === "root" ? "/var/root" : join("/Users", name));
const expandTilde = (w: string) => {
  if (w === "~" || w.startsWith("~/")) return home() + w.slice(1);
  const m = w.match(/^~([A-Za-z_][\w.-]*)(\/[\s\S]*)?$/);
  return m ? userHome(m[1]) + (m[2] ?? "") : w;
};
// A variable whose value the guard cannot know (a loop variable, `read` from a pipe).
const UNKNOWN = "$__parity_unknown__";

// A substitution that opens a word, $(...) or `...`: its text and where it ends.
function leadingSub(w: string): [string, number] | undefined {
  if (w.startsWith("$(") && !w.startsWith("$((")) {
    let depth = 1, q: string | null = null;
    for (let j = 2; j < w.length; j++) {
      const c = w[j];
      if (q) { if (c === q) q = null; else if (c === "\\" && q === '"') j++; continue; }
      if (c === "'" || c === '"') q = c;
      else if (c === "\\") j++;
      else if (c === "(") depth++;
      else if (c === ")" && --depth === 0) return [w.slice(2, j), j + 1];
    }
    return undefined;
  }
  if (w.startsWith("`")) {
    const k = w.indexOf("`", 1);
    return k > 0 ? [w.slice(1, k), k + 1] : undefined;
  }
  return undefined;
}

// A substitution that prints the home directory: a printer of it (echo, printf, realpath,
// readlink, cd ... pwd, eval, an interpreter's one-liner) whose text names it: ~ or ~$USER,
// $HOME in any form, a bare cd, or code asking for it (expanduser, homedir, Path.home).
const HOME_PRINTERS = /^\s*(echo|printf|realpath|readlink|cd|eval|python3?|node|perl|ruby|dscl|getent)\b/;
const HOMEISH = /(^|[\s=:'"(])~(?=$|[\s\/'")]|\$\{?(USER|LOGNAME)\b)|\$\{?HOME\b|^\s*cd\s*($|;|&&|\|\|)|\bexpanduser\b|\bhomedir\b|\bPath\.home\b|\bgetpwuid\b/;

// A shell word as a path: ~, ~user, ~+, $HOME and ${HOME...} in any form, $PWD, $(pwd),
// $(git rev-parse --show-toplevel), $(echo words), $(cd dir && pwd), a substitution that
// opens the word and names the home directory, and variables the same call assigned are
// expanded, and a relative word resolves against cwd. A word that still holds another variable
// cannot be resolved and comes back undefined.
function expandVars(word: string, cwd: string, vars?: Vars): string {
  let w = expandTilde(word);
  if (w === "~+" || w.startsWith("~+/")) w = cwd + w.slice(2);
  if (w === "~-" || w.startsWith("~-/")) w = "$OLDPWD" + w.slice(2);
  w = w.replace(/\$\(\s*pwd(\s+-[LP])?\s*\)|`\s*pwd(\s+-[LP])?\s*`/g, cwd);
  w = w.replace(/\$\(\s*git\s+rev-parse\s+--show-toplevel\s*\)|`\s*git\s+rev-parse\s+--show-toplevel\s*`/g, (m) => repoRoot(cwd) ?? m);
  w = w.replace(/\$\(\s*echo\s+([^()$`;|&<>]*)\)|`\s*echo\s+([^()$`;|&<>]*)`/g, (m, a, b) =>
    (tokenize(a ?? b)[0]?.words ?? []).filter((x) => x !== "-n").map(expandTilde).join(" "));
  w = w.replace(/\$\(\s*cd\s+([^()$`;|&<>\s]+)\s*(?:&&|;)\s*pwd\s*\)/g, (m, d) => {
    const e = expandVars(d, cwd, vars);
    return /[$`]/.test(e) ? m : resolve(cwd, e);
  });
  const lead = leadingSub(w);
  if (lead && HOME_PRINTERS.test(lead[0]) && HOMEISH.test(lead[0])) w = home() + w.slice(lead[1]);
  w = w.replace(/\$\{([A-Za-z_][A-Za-z0-9_]*)([^{}]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)/g, (m, braced, op, bare) => {
    const name = braced ?? bare;
    // HOME in any form (${HOME:-x}, ${HOME%/}, ${HOME/a/b}) is taken as HOME.
    if (name === "HOME") return home();
    const v = vars?.has(name) ? vars.get(name)! : name === "PWD" ? cwd :
      name === "TMPDIR" ? (process.env.TMPDIR || "/tmp").replace(/\/$/, "") : undefined;
    if (v === undefined) return m;
    if (!op) return v;
    return /^:?[-=?]/.test(op) && v !== "" ? v : m;
  });
  return expandTilde(w);
}

function wordPath(word: string, cwd: string, vars?: Vars): string | undefined {
  const w = expandVars(word, cwd, vars);
  if (/\$[{A-Za-z_(]/.test(w) || w.includes("`")) return undefined;
  if (!w) return undefined;
  const p = isAbsolute(w) ? resolve(w) : resolve(cwd, w);
  return p.includes(UNKNOWN) ? undefined : p;
}

const KEYISH = /<key>[^<]*(api[_-]?key|_key|token|secret|password|passwd|credential)[^<]*<\/key>/i;
const KEYISH_BIN = /(api[_-]?key|_KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)/;

function plistHoldsKeys(path: string) {
  try {
    if (statSync(path).size > 2 * 1024 * 1024) return false;
    const buf = readFileSync(path);
    const text = buf.toString("utf-8");
    return text.startsWith("bplist") ? KEYISH_BIN.test(buf.toString("latin1")) : KEYISH.test(text);
  } catch {
    return false;
  }
}

function keyPlistIn(dir: string, re?: RegExp) {
  try {
    for (const n of readdirSync(dir)) {
      const p = join(dir, n);
      if (n.toLowerCase().endsWith(".plist") && (!re || re.test(p.toLowerCase())) && plistHoldsKeys(p)) return p;
    }
  } catch {}
  return undefined;
}

// The homes a path may reach, canonical: the owner's, the one the path is in (/Users/<user>,
// /var/root), and every home when the path holds /Users or /var/root.
function homesNear(p?: string): string[] {
  const out = new Set([canon(home())]);
  if (p) {
    const m = p.match(/^\/users\/[^\/]+/) ?? p.match(/^(\/private)?\/var\/root(?=\/|$)/);
    if (m) out.add(m[0].startsWith("/var") ? "/private" + m[0] : m[0]);
    if (under("/users", p) || under("/private/var/root", p) || p === "/var") {
      out.add("/private/var/root");
      try { for (const n of readdirSync("/Users")) if (!n.startsWith(".")) out.add(canon(join("/Users", n))); } catch {}
    }
  }
  return [...out];
}

// Where credentials live, canonical, in every home near p. Each is a directory or file a model
// must never read, copy or print.
function credentialRoots(p?: string) {
  const auths: string[] = [], dirs: Array<[string, string]> = [];
  for (const h of homesNear(p)) {
    auths.push(join(h, ".local", "share", "opencode", "auth.json"));
    dirs.push([join(h, ".ssh"), "SSH keys"], [join(h, ".config", "rclone"), "rclone's config"],
      [join(h, ".config", "media-syncer"), "media-syncer's config"], [join(h, ".config", "api-keys"), "the API key store"]);
  }
  return { auths, dirs };
}

const AUTH_WHAT = "OpenCode's auth.json, which holds the DeepSeek key";
const SSH_PUBLIC = /^(known_hosts(\.old)?|config|authorized_keys|.*\.pub)$/;
const ENV_FILE = /(^|\.)env$/;
const SSH_KEY = /^id_(rsa|dsa|ecdsa|ed25519)(_sk)?$/;

// Names what a path holds when it is a credential, else undefined. A glob counts when its
// literal part names a credential, or when it expands to one on disk (expand=true).
function credentialOf(raw: string, expand = true): string | undefined {
  const real = realish(raw);
  const p = real.toLowerCase();
  const glob = GLOB_CHARS.test(p);
  const re = glob ? globRegex(p) : undefined;
  const { auths, dirs } = credentialRoots(p);
  if (auths.some((auth) => (re ? re.test(auth) : p === auth))) return AUTH_WHAT;
  const prefix = glob ? p.split(/[*?[]/)[0] : p;
  const base = basename(p);
  for (const [dir, what] of dirs) {
    const inside = re ? re.test(join(dir, "id_ed25519")) || re.test(join(dir, "rclone.conf")) || under(prefix, dir + "/") : under(p, dir);
    if (!inside) continue;
    if (what === "SSH keys" && !glob && p !== dir && SSH_PUBLIC.test(base)) continue;
    return what;
  }
  if (/(^|\/)backup-private(\/|$)/.test(p)) return "backup-private/";
  // A glob names a credential only through its literal characters: `*` alone names nothing.
  const literal = base.replace(/\[[^\]]*\]|[*?]/g, "");
  const named = (name: string) => (glob ? literal !== "" && globRegex(base).test(name) : base === name);
  if (!glob && ENV_FILE.test(base) && base !== "env") return `${basename(raw)}, an env file of keys`;
  if (glob && literal.includes("env") && (named("keys.env") || named("x.env") || named(".env"))) return "env files of keys";
  if (named("rclone.conf")) return "rclone.conf";
  if (glob ? literal.includes("id_") && ["id_rsa", "id_ed25519", "id_ecdsa", "id_dsa"].some(named) : SSH_KEY.test(base)) return "an SSH private key";
  if (!glob && base.endsWith(".plist") && plistHoldsKeys(real)) return `${basename(raw)}, a plist holding keys`;
  if (glob && base.endsWith(".plist")) {
    const hit = keyPlistIn(dirname(real.split(/[*?[]/)[0] + "x"), re);
    if (hit) return `${basename(hit)}, a plist holding keys`;
  }
  if (glob && expand) {
    for (const m of expandGlob(real)) {
      const what = credentialOf(m, false);
      if (what) return what;
    }
  }
  return undefined;
}

// A directory whose recursive read would sweep up a credential.
function holdsCredential(raw: string): string | undefined {
  if (GLOB_CHARS.test(raw)) {
    for (const m of expandGlob(realish(raw))) {
      const what = holdsCredential(m);
      if (what) return what;
    }
    return undefined;
  }
  const p = canon(raw);
  const { auths, dirs } = credentialRoots(p);
  for (const target of [...auths, ...dirs.map(([d]) => d)]) {
    if (under(target, p) && target !== p) return `${raw}, which holds ${credentialOf(target, false)}`;
  }
  const plist = keyPlistIn(realish(raw));
  if (plist) return `${raw}, which holds ${basename(plist)} (a plist with keys)`;
  return undefined;
}

const CRED_MOVE =
  "Never read, copy, upload or print it. Keys move only through upkeep's key_sync (upkeep/upkeep.py) " +
  "or the fleet's own modules; if a key is missing, ask the owner.";

// ---- shell parsing

type Redir = { op: string; target: string };
type Raw = { words: string[]; redirs: Redir[]; code: string[]; piped?: Raw };
// xargs: the command takes more arguments from stdin; stdin: text known to reach its stdin.
// scope: for find -exec, the roots its {} paths come from.
// feeder: the command piping into this one; opaque: it runs code from stdin the guard cannot
// read; assigns: NAME=value words stripped from its front; links: symlinks and hard links the
// call made, link -> what it names; written: text the call wrote to a file, by path.
// lister: for a command inside a shell that xargs runs, the command piping into that xargs.
type Shared = { links: Map<string, { named: string; seq: number }>; written: Map<string, string>; seq: number; aliases?: Map<string, string> };
type Cmd = {
  words: string[]; redirs: Redir[]; code: string[]; cwd: string; vars: Vars; xargs?: boolean; stdin: string[]; scope?: string[];
  feeder?: { words: string[]; cwd: string; vars: Vars }; opaque?: boolean; assigns: string[]; shared: Shared; seq?: number;
  argFiles?: string[]; reads?: string[]; lister?: { words: string[]; cwd: string; vars: Vars };
};

const KEYWORDS = new Set(["if", "then", "else", "elif", "while", "until", "do", "!", "{", "}", "fi", "done", "esac"]);
const ANSI_ESC: Record<string, string> = {
  n: "\n", t: "\t", r: "\r", a: "\x07", b: "\b", e: "\x1b", E: "\x1b", f: "\f", v: "\v", "\\": "\\", "'": "'", '"': '"', "?": "?",
};

// Splits a command line into simple commands. Handles quotes, escapes, ; && || | & and
// newlines, $(...), backticks and <(...) (parsed as commands of their own), redirections and
// here-documents (their body goes to the command as code). A command fed by a pipe records
// the command before it.
function tokenize(src: string): Raw[] {
  const out: Raw[] = [];
  let cur: Raw = { words: [], redirs: [], code: [] };
  let word: string | null = null;
  let pendingOp: string | null = null;
  let pipeFrom: Raw | null = null;
  const heredocs: Array<{ delim: string; strip: boolean; cmd: Raw }> = [];
  const subs: string[] = [];
  const endWord = () => {
    if (word === null) return;
    if (pendingOp) {
      if (pendingOp === "<<" || pendingOp === "<<-") heredocs.push({ delim: word, strip: pendingOp === "<<-", cmd: cur });
      else cur.redirs.push({ op: pendingOp, target: word });
      pendingOp = null;
    } else cur.words.push(word);
    word = null;
  };
  const endCmd = (op?: string) => {
    endWord();
    const pipe = op === "|" || op === "|&";
    if (cur.words.length || cur.redirs.length || cur.code.length) {
      if (pipeFrom) cur.piped = pipeFrom;
      out.push(cur);
      pipeFrom = pipe ? cur : null;
    } else if (!pipe) pipeFrom = null;
    cur = { words: [], redirs: [], code: [] };
  };
  // Reads a balanced (...) starting after the opening paren; returns the inner text and the end index.
  const balanced = (i: number): [string, number] => {
    let depth = 1, j = i, q: string | null = null;
    for (; j < src.length; j++) {
      const c = src[j];
      if (q) { if (c === q) q = null; else if (c === "\\" && q === '"') j++; continue; }
      if (c === "'" || c === '"') q = c;
      else if (c === "\\") j++;
      else if (c === "(") depth++;
      else if (c === ")" && --depth === 0) break;
    }
    return [src.slice(i, j), j];
  };
  let i = 0;
  while (i < src.length) {
    const c = src[i];
    if (c === "\\") {
      if (src[i + 1] === "\n") { i += 2; continue; }
      word = (word ?? "") + (src[i + 1] ?? "");
      i += 2;
      continue;
    }
    if (c === "'") {
      const j = src.indexOf("'", i + 1);
      const end = j < 0 ? src.length : j;
      word = (word ?? "") + src.slice(i + 1, end);
      i = end + 1;
      continue;
    }
    if (c === '"') {
      let j = i + 1, s = "";
      while (j < src.length && src[j] !== '"') {
        if (src[j] === "\\" && j + 1 < src.length) {
          const n = src[j + 1];
          if (n === "\n") { j += 2; continue; }
          s += '"\\$`'.includes(n) ? n : "\\" + n;
          j += 2;
          continue;
        }
        if (src[j] === "$" && src[j + 1] === "(" && src[j + 2] !== "(") {
          const [inner, end] = balanced(j + 2);
          subs.push(inner);
          s += src.slice(j, end + 1);
          j = end + 1;
          continue;
        }
        if (src[j] === "`") {
          const k = src.indexOf("`", j + 1);
          const end = k < 0 ? src.length : k;
          subs.push(src.slice(j + 1, end));
          s += src.slice(j, end + 1);
          j = end + 1;
          continue;
        }
        s += src[j++];
      }
      word = (word ?? "") + s;
      i = j + 1;
      continue;
    }
    // ANSI-C quoting: $'...' with its backslash escapes. $"..." reads as a double-quoted string.
    if (c === "$" && src[i + 1] === "'") {
      let j = i + 2, s = "";
      while (j < src.length && src[j] !== "'") {
        if (src[j] !== "\\" || j + 1 >= src.length) { s += src[j++]; continue; }
        const rest = src.slice(j + 1);
        const simple = ANSI_ESC[rest[0]];
        let m: RegExpMatchArray | null;
        if (simple !== undefined) { s += simple; j += 2; }
        else if ((m = rest.match(/^x([0-9a-fA-F]{1,2})/))) { s += String.fromCharCode(parseInt(m[1], 16)); j += 1 + m[0].length; }
        else if ((m = rest.match(/^([0-7]{1,3})/))) { s += String.fromCharCode(parseInt(m[1], 8)); j += 1 + m[0].length; }
        else if ((m = rest.match(/^u([0-9a-fA-F]{1,4})|^U([0-9a-fA-F]{1,8})/))) {
          try { s += String.fromCodePoint(parseInt(m[1] ?? m[2], 16)); } catch {}
          j += 1 + m[0].length;
        } else if ((m = rest.match(/^c(.)/))) { s += String.fromCharCode(m[1].toUpperCase().charCodeAt(0) & 31); j += 3; }
        else { s += "\\" + rest[0]; j += 2; }
      }
      word = (word ?? "") + s;
      i = j + 1;
      continue;
    }
    if (c === "$" && src[i + 1] === '"') { word ??= ""; i++; continue; }
    if (c === "$" && src[i + 1] === "(") {
      if (src[i + 2] === "(") {
        const k = src.indexOf("))", i + 3);
        const end = k < 0 ? src.length : k + 2;
        word = (word ?? "") + src.slice(i, end);
        i = end;
        continue;
      }
      const [inner, end] = balanced(i + 2);
      subs.push(inner);
      word = (word ?? "") + src.slice(i, end + 1);
      i = end + 1;
      continue;
    }
    if (c === "`") {
      const k = src.indexOf("`", i + 1);
      const end = k < 0 ? src.length : k;
      subs.push(src.slice(i + 1, end));
      word = (word ?? "") + src.slice(i, end + 1);
      i = end + 1;
      continue;
    }
    if ((c === "<" || c === ">") && src[i + 1] === "(") {
      const [inner, end] = balanced(i + 2);
      subs.push(inner);
      word = (word ?? "") + src.slice(i, end + 1);
      i = end + 1;
      continue;
    }
    if (c === "#" && word === null) {
      const k = src.indexOf("\n", i);
      i = k < 0 ? src.length : k;
      continue;
    }
    if (c === " " || c === "\t" || c === "\r") { endWord(); i++; continue; }
    if (c === "\n") {
      endCmd();
      i++;
      // Here-document bodies follow the line that opened them.
      while (heredocs.length) {
        const h = heredocs.shift()!;
        const delim = h.delim;
        const lines: string[] = [];
        while (i < src.length) {
          const k = src.indexOf("\n", i);
          const line = src.slice(i, k < 0 ? src.length : k);
          i = k < 0 ? src.length : k + 1;
          if ((h.strip ? line.replace(/^\t+/, "") : line) === delim) break;
          lines.push(line);
        }
        h.cmd.code.push(lines.join("\n"));
      }
      continue;
    }
    // Redirections: [n]> >> >| < <> << <<- <<< >& <& &> &>>
    const redir = src.slice(i).match(/^(&>>|&>|<<<|<<-|<<|<>|>>|>\||>&|<&|>|<)/);
    if (redir && (c !== "&" || word === null)) {
      if (word !== null && /^\d+$/.test(word)) word = null;
      endWord();
      pendingOp = redir[1];
      i += redir[1].length;
      continue;
    }
    const op = src.slice(i).match(/^(&&|\|\||\|&|;;|[;&|()])/);
    if (op) {
      if (op[1] === "(" && word !== null) { word += c; i++; continue; }
      endCmd(op[1]);
      i += op[1].length;
      continue;
    }
    word = (word ?? "") + c;
    i++;
  }
  endCmd();
  for (const h of heredocs) h.cmd.code.push("");
  for (const s of subs) out.push(...tokenize(s));
  return out;
}

const SHELLS = new Set(["bash", "sh", "zsh", "dash", "ksh"]);
const INTERPRETERS = /^(python(\d(\.\d+)?)?|node|nodejs|perl|ruby|bun|deno|osascript)$/;
const ASSIGN = /^[A-Za-z_][A-Za-z0-9_]*=/;

// Runners that run the command after their options: the options that take a value, and the
// ones that move the directory (chdir), read a file (reads), run a shell string (shell) or run
// a module (module). Ones marked tools take tool specs up to a `--` before the command.
type Runner = { sub?: string; valued: RegExp; chdir?: RegExp; reads?: RegExp; shell?: RegExp; module?: RegExp; tools?: boolean };
const RUNNERS: Record<string, Runner> = {
  uv: { sub: "run", valued: /^(--with|--with-editable|--with-requirements|-p|--python|--project|--directory|--package|--extra|--group|--only-group|--no-group|--index|--default-index|--index-url|--extra-index-url|-i|--find-links|-f|--env-file|--config-file|--cache-dir|--python-preference|--resolution|--prerelease|--exclude-newer|--index-strategy|--keyring-provider|--link-mode|--refresh-package|--reinstall-package|-P|--upgrade-package|--no-binary-package|--no-build-package|--color|--allow-insecure-host|-C|--config-setting)$/,
    chdir: /^--directory$/, reads: /^--env-file$/, module: /^(-m|--module)$/ },
  uvx: { valued: /^(--from|--with|--with-editable|--with-requirements|-p|--python|--index|--default-index|--index-url|--extra-index-url|-i|--find-links|-f|--cache-dir|--color|-C|--config-setting)$/ },
  mise: { sub: "exec|x", valued: /^(-C|--cd|-c|--command|-j|--jobs|-E|--env)$/, chdir: /^(-C|--cd)$/, shell: /^(-c|--command)$/, tools: true },
  poetry: { sub: "run", valued: /^(-C|--directory|-P|--project)$/, chdir: /^(-C|--directory)$/ },
  pipx: { sub: "run", valued: /^(--spec|--python|--pip-args|--index-url|--fetch-python)$/ },
  npx: { valued: /^(-p|--package|-c|--call|--prefix|--registry|--cache|-w|--workspace)$/, shell: /^(-c|--call)$/ },
  bunx: { valued: /^(-p|--package)$/ },
  pnpx: { valued: /^(--package)$/ },
  pnpm: { sub: "exec|dlx", valued: /^(--package|-C|--dir|--filter|-F)$/, chdir: /^(-C|--dir)$/, shell: /^(-c|--shell-mode)$/ },
  yarn: { sub: "dlx|exec", valued: /^(-p|--package)$/ },
  npm: { sub: "exec|x", valued: /^(-p|--package|-c|--call|-w|--workspace|--prefix)$/, shell: /^(-c|--call)$/ },
};

// Strips what runs a command without being it: NAME=value prefixes, sudo, env (its -S string
// is split into words), command, exec, nice, nohup, time, timeout, xargs, and the runners above
// (uv run, mise exec, poetry run, pipx run, npx, bunx and the like). Returns the assignments it
// stripped, the directory env -C, sudo -D or a runner moves to, the files xargs -a reads its
// arguments from (argFiles), and other files a wrapper reads (reads).
function unwrap(words: string[]): { words: string[]; xargs: boolean; chdir?: string; assigns: string[]; argFiles: string[]; reads: string[] } {
  let w = [...words];
  let xargs = false;
  let chdir: string | undefined;
  const assigns: string[] = [], argFiles: string[] = [], reads: string[] = [];
  const done = () => ({ words: w, xargs, chdir, assigns, argFiles, reads });
  for (let guard = 0; guard < 20 && w.length; guard++) {
    while (w.length && ASSIGN.test(w[0])) assigns.push(w.shift()!);
    while (w.length && KEYWORDS.has(w[0])) w.shift();
    if (!w.length) break;
    const prog = basename(w[0]);
    const skipOpts = (withValue: RegExp = /^$/) => {
      w.shift();
      while (w.length && w[0].startsWith("-") && w[0] !== "--") {
        const f = w.shift()!;
        if (/^(-D|--chdir)$/.test(f) && prog === "sudo" && w.length) { chdir = w.shift(); continue; }
        if (f.startsWith("--chdir=") && prog === "sudo") { chdir = f.slice(8); continue; }
        if (withValue.test(f) && w.length) w.shift();
      }
      if (w[0] === "--") w.shift();
    };
    const runner = RUNNERS[prog];
    if (runner && (!runner.sub || new RegExp(`^(${runner.sub})$`).test(w[1] ?? ""))) {
      w.shift();
      if (runner.sub) w.shift();
      let shell: string | undefined, module: string | undefined, dashed = false;
      while (w.length && w[0].startsWith("-") && w[0] !== "-") {
        const f = w.shift()!;
        if (f === "--") { dashed = true; break; }
        const eq = f.match(/^(--[\w-]+)=([\s\S]*)$/);
        const name = eq ? eq[1] : f;
        const value = eq ? eq[2] : runner.valued.test(f) && w.length ? w.shift() : undefined;
        if (value === undefined) continue;
        if (runner.chdir?.test(name)) chdir = value;
        else if (runner.reads?.test(name)) reads.push(value);
        else if (runner.shell?.test(name)) shell = value;
        else if (runner.module?.test(name)) module = value;
      }
      if (shell !== undefined) { w = ["sh", "-c", shell]; break; }
      if (module !== undefined) { w = ["python", "-m", module, ...w]; break; }
      if (runner.tools && !dashed) {
        const k = w.indexOf("--");
        w = k < 0 ? [] : w.slice(k + 1);
      }
      // A package runner names a package, perhaps with a version: its program is the bare name.
      if (w.length && /^(npx|bunx|pnpx|uvx|pipx|pnpm|yarn|npm)$/.test(prog)) w[0] = w[0].replace(/(?!^)@[^\/]*$/, "");
      continue;
    }
    if (prog === "sudo") skipOpts(/^-[ugpChrtUD]$/);
    else if (prog === "env") {
      w.shift();
      while (w.length && w[0].startsWith("-") && w[0] !== "--") {
        const f = w.shift()!;
        const split = f === "-S" || f === "--split-string" ? w.shift() : f.match(/^(?:-S|--split-string=)(.+)$/)?.[1];
        if (split !== undefined) { w = [...(tokenize(split)[0]?.words ?? []), ...w]; break; }
        if ((f === "-C" || f === "--chdir") && w.length) { chdir = w.shift(); continue; }
        if (f.startsWith("--chdir=")) { chdir = f.slice(8); continue; }
        if (f.startsWith("-C") && f.length > 2) { chdir = f.slice(2); continue; }
        if (/^-[u]$/.test(f) && w.length) w.shift();
      }
      if (w[0] === "--") w.shift();
      while (w.length && ASSIGN.test(w[0])) assigns.push(w.shift()!);
    } else if (prog === "command" || prog === "builtin") {
      if (w[1] === "-v" || w[1] === "-V") return { ...done(), words: [] };
      skipOpts();
    } else if (prog === "exec" || prog === "nohup" || prog === "caffeinate" || prog === "stdbuf") skipOpts(/^-[aw]$/);
    else if (prog === "nice") skipOpts(/^-n$/);
    else if (prog === "time" || prog === "gtime") skipOpts(/^-[of]$/);
    else if (prog === "arch") skipOpts();
    else if (prog === "timeout" || prog === "gtimeout") {
      skipOpts(/^-[sk]$/);
      w.shift();
    } else if (prog === "xargs" || prog === "parallel") {
      xargs = true;
      w.shift();
      while (w.length && w[0].startsWith("-") && w[0] !== "--") {
        const f = w.shift()!;
        if (f === "--arg-file" && w.length) { argFiles.push(w.shift()!); continue; }
        if (f.startsWith("--arg-file=")) { argFiles.push(f.slice(11)); continue; }
        if (/^--(delimiter|max-args|max-procs|max-chars|process-slot-var)$/.test(f) && w.length) { w.shift(); continue; }
        if (f.startsWith("--")) continue;
        // A cluster of short options (-0a FILE, -ra FILE, -tafile): a, I, E, d, L, n, P, s, J
        // and R take the rest of the cluster or the next word; i, e and l take only the rest.
        for (let j = 1; j < f.length; j++) {
          const ch = f[j];
          if ("aIEdLnPsJR".includes(ch)) {
            const v = f.slice(j + 1) || w.shift();
            if (ch === "a" && v !== undefined) argFiles.push(v);
            break;
          }
          if ("iel".includes(ch)) break;
        }
      }
      if (w[0] === "--") w.shift();
    } else break;
  }
  return done();
}

// git subcommands; any other word is an alias, looked up in the repository's config.
const GIT_COMMANDS = new Set(("add stage commit push pull fetch merge checkout switch restore reset rebase stash cherry-pick " +
  "revert am apply rm mv clean init clone gc status log show diff grep blame branch tag config remote submodule worktree " +
  "rev-parse rev-list ls-files ls-tree ls-remote describe shortlog reflog bisect notes format-patch cat-file " +
  "check-ignore check-attr for-each-ref show-ref symbolic-ref update-ref update-index merge-base merge-tree " +
  "name-rev whatchanged help version var count-objects fsck prune repack archive bundle sparse-checkout maintenance " +
  "range-diff difftool mergetool request-pull send-email hash-object write-tree commit-tree read-tree filter-branch replace " +
  "checkout-index mktree mktag fast-import fast-export unpack-objects index-pack pack-objects prune-packed replay diff-tree " +
  "diff-index diff-files cherry show-branch verify-commit verify-tag annotate rerere citool gui instaweb").split(" "));

function gitAlias(dir: string, name: string): string | undefined {
  try {
    const out = execFileSync("git", ["-C", dir, "config", "--get", `alias.${name}`], {
      encoding: "utf-8", timeout: 2000, stdio: ["ignore", "pipe", "ignore"],
    });
    return out.trim() || undefined;
  } catch {
    return undefined;
  }
}

// A git command with its alias (from -c alias.x=... or the config) replaced by what it runs.
// A shell alias (!...) comes back as a script.
function resolveGitAlias(words: string[], cwd: string, vars: Vars, made?: Map<string, string>): { words: string[]; script?: string } {
  if (basename(words[0] ?? "") !== "git") return { words };
  const inline = new Map<string, string>();
  let dir = cwd, k = 1;
  while (k < words.length && words[k].startsWith("-")) {
    const f = words[k];
    if (f === "-c" && words[k + 1]) {
      const m = words[k + 1].match(/^alias\.([^=]+)=(.*)$/is);
      if (m) inline.set(m[1].toLowerCase(), m[2]);
      k += 2;
      continue;
    }
    if (f === "-C" && words[k + 1]) { dir = wordPath(words[k + 1], dir, vars) ?? dir; k += 2; continue; }
    if (f === "--git-dir" || f === "--work-tree" || f === "--namespace") { k += 2; continue; }
    k++;
  }
  const sub = words[k];
  if (!sub || GIT_COMMANDS.has(sub)) return { words };
  const expansion = inline.get(sub.toLowerCase()) ?? made?.get(sub.toLowerCase()) ?? gitAlias(dir, sub);
  if (!expansion) return { words };
  if (expansion.startsWith("!")) return { words, script: expansion.slice(1) + " " + words.slice(k + 1).join(" ") };
  return { words: [...words.slice(0, k), ...(tokenize(expansion)[0]?.words ?? []), ...words.slice(k + 1)] };
}

// find's -exec/-execdir/-ok commands, each up to its ; or +.
function findExecs(words: string[]): string[][] {
  const out: string[][] = [];
  for (let k = 1; k < words.length; k++) {
    if (!/^-(exec|execdir|ok|okdir)$/.test(words[k])) continue;
    const sub: string[] = [];
    for (k++; k < words.length && words[k] !== ";" && words[k] !== "+"; k++) sub.push(words[k]);
    if (sub.length) out.push(sub);
  }
  return out;
}

// Every simple command a bash call would run, wrappers stripped and bash -c / eval / here-doc /
// piped scripts, find -exec and git aliases parsed in turn, each with the directory it runs in
// (cd is followed) and the variables assigned before it. Commands inside code (subprocess,
// os.system, osascript's do shell script) and inside an ad-hoc script file the call runs are
// parsed too.
function parseCommands(src: string, cwd: string, depth = 0, vars: Vars = new Map(), shared: Shared = { links: new Map(), written: new Map(), seq: 0 }): Cmd[] {
  const out: Cmd[] = [];
  let dir = cwd;
  const stack: string[] = [];
  const sub = (text: string, at: string, v: Vars) => (depth <= 4 ? parseCommands(text, at, depth + 1, v, shared) : []);
  for (const raw of tokenize(src)) {
    const lead = raw.words.findIndex((x) => !ASSIGN.test(x));
    const assigns = lead < 0 ? raw.words : raw.words.slice(0, lead);
    const un = unwrap(raw.words);
    let { words } = un;
    const { xargs } = un;
    // Words built from variables the call assigned or $(echo ...) (g=git; $g add -A): the
    // command word is split as the shell splits it.
    if (words.some((x) => /[$`]/.test(x))) {
      const ex = (x: string) => {
        if (!/[$`]/.test(x)) return x;
        const e = expandVars(x, dir, vars);
        return /[$`]/.test(e) ? x : e;
      };
      const first = ex(words[0]);
      words = [...(first !== words[0] && first.trim() ? first.trim().split(/\s+/) : [first]), ...words.slice(1).map(ex)];
    }
    const declare = /^(export|declare|local|readonly|typeset)$/.test(words[0] ?? "");
    if (!words.length || declare) {
      for (const a of declare ? words.slice(1) : assigns) {
        const m = a.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/s);
        if (m) vars.set(m[1], expandVars(m[2], dir, vars));
      }
    }
    const fedRaw = raw.piped ? unwrap(raw.piped.words).words : [];
    // A pipe from echo or printf, or from a bare cat fed a here-document or here-string,
    // carries text the guard can read.
    const fedByCat = fedRaw.length === 1 && basename(fedRaw[0]) === "cat" &&
      !!raw.piped && (raw.piped.code.length > 0 || raw.piped.redirs.some((r) => r.op === "<<<"));
    const fedByEcho = ["echo", "printf"].includes(basename(fedRaw[0] ?? "")) || fedByCat;
    const stdin = [
      ...raw.redirs.filter((r) => r.op === "<<<").map((r) => r.target),
      ...(fedByCat ? [...raw.piped!.code, ...raw.piped!.redirs.filter((r) => r.op === "<<<").map((r) => r.target)] :
        fedByEcho ? fedRaw.slice(1) : []),
    ];
    // xargs -a FILE takes its arguments from FILE: its text, when it is readable and no credential.
    if (xargs && un.argFiles.length) {
      const texts = un.argFiles.map((f) => {
        const p = wordPath(f, dir, vars);
        return p && !credentialOf(p, false) ? fileText(p, { shared } as Cmd) : undefined;
      });
      stdin.length = 0;
      if (texts.every((x) => x !== undefined)) stdin.push(...(texts as string[]));
    }
    const prog0 = basename(words[0] ?? "");
    // Variables a loop or `read` sets: known from a here-string, else unknown.
    if (prog0 === "read" || prog0 === "mapfile" || prog0 === "readarray" || prog0 === "getopts") {
      const names = words.slice(1).filter((x, k, a) => /^[A-Za-z_]\w*$/.test(x) && !/^-[pdtnNuai]$/.test(a[k - 1] ?? ""));
      const known = prog0 === "read" && names.length === 1 && stdin.length === 1 && !raw.piped ? expandVars(stdin[0], dir, vars) : UNKNOWN;
      for (const n of names) vars.set(n, known);
    }
    if ((prog0 === "for" || prog0 === "select") && /^[A-Za-z_]\w*$/.test(words[1] ?? "")) vars.set(words[1], UNKNOWN);
    // An alias this call defines (git config alias.x '...') counts for the commands after it.
    if (basename(words[0] ?? "") === "git") {
      const k = words.findIndex((x) => /^alias\./i.test(x));
      if (k > 0 && words.slice(1, k).includes("config") && words[k + 1] !== undefined) {
        (shared.aliases ??= new Map()).set(words[k].slice(6).toLowerCase(), words[k + 1]);
      }
    }
    const alias = resolveGitAlias(words, dir, vars, shared.aliases);
    words = alias.words;
    if (xargs) words = [...words, ...stdin.flatMap((s) => s.split(/\s+/).filter(Boolean))];
    const here = un.chdir !== undefined ? wordPath(un.chdir, dir, vars) ?? dir + "/" + UNKNOWN : dir;
    const cmd: Cmd = {
      words, redirs: raw.redirs, code: [...raw.code], cwd: here, vars: new Map(vars), xargs, stdin, assigns: [...assigns, ...un.assigns], shared,
      argFiles: un.argFiles, reads: un.reads,
      feeder: raw.piped && !fedByEcho ? { words: fedRaw, cwd: dir, vars: new Map(vars) } : undefined, seq: ++shared.seq,
    };
    out.push(cmd);
    if (alias.script) out.push(...sub(alias.script, here, vars));
    if (!words.length) continue;
    const prog = basename(words[0]);
    if (prog === "cd" || prog === "pushd") {
      const arg = words.slice(1).find((x) => !/^-[LPe@n]+$/.test(x));
      const target = arg && arg !== "-" ? wordPath(arg, dir, vars) : arg === "-" ? undefined : prog === "cd" ? home() : undefined;
      if (prog === "pushd") stack.push(dir);
      dir = target ?? dir + "/" + UNKNOWN;
      continue;
    }
    if (prog === "popd") { dir = stack.pop() ?? dir + "/" + UNKNOWN; continue; }
    noteWrites(cmd);
    if (depth > 4) continue;
    if (SHELLS.has(prog)) {
      const ci = words.findIndex((x, k) => k > 0 && /^-[a-zA-Z]*c[a-zA-Z]*$/.test(x));
      if (ci > 0 && words[ci + 1] !== undefined) {
        const inner = sub(words[ci + 1], here, new Map(vars));
        // Under xargs the script's arguments ({}, "$@", $1) are the names xargs reads, so each
        // command it runs takes them as xargs cat would.
        if (xargs) {
          const known = stdin.flatMap((x) => x.split(/\s+/).filter(Boolean));
          for (const c of inner) {
            c.xargs = true;
            if (known.length) { c.words = [...c.words, ...known]; c.stdin = [...c.stdin, ...stdin]; }
            c.lister ??= cmd.lister ?? cmd.feeder;
          }
        }
        out.push(...inner);
      } else {
        const script = words.slice(1).find((x, k, a) => !x.startsWith("-") && !x.startsWith("+") && !/^[-+][oO]$/.test(a[k - 1] ?? ""));
        if (script) {
          const text = scriptText(script, cmd);
          if (text !== undefined) out.push(...sub(text, here, new Map()));
        } else {
          const bodies = [...raw.code, ...stdin, ...stdinFileText(cmd)];
          for (const body of bodies) out.push(...sub(body, here, new Map(vars)));
          if (stdinUnknown(cmd)) cmd.opaque = true;
        }
      }
    } else if (prog === "source" || prog === ".") {
      const text = words[1] !== undefined ? scriptText(words[1], cmd) : undefined;
      if (text !== undefined) out.push(...sub(text, here, vars));
    } else if (prog === "eval") {
      out.push(...sub(words.slice(1).join(" "), here, vars));
    } else if (prog === "find") {
      const scope = operandsOf(cmd).roots;
      for (const s of findExecs(words)) {
        const w = unwrap(s).words;
        // {} stands for each path find visits, so it is replaced by each root it starts from.
        const roots = w.includes("{}") ? scope : [undefined];
        for (const r of roots) {
          const ws = r === undefined ? w : w.map((x) => x.split("{}").join(r));
          out.push({ words: ws, redirs: [], code: [], cwd: here, vars: new Map(vars), xargs: true, stdin: [], scope, assigns: [], shared, seq: ++shared.seq });
          const ci = SHELLS.has(basename(ws[0] ?? "")) ? ws.findIndex((x, k) => k > 0 && /^-[a-zA-Z]*c[a-zA-Z]*$/.test(x)) : -1;
          if (ci > 0 && ws[ci + 1] !== undefined) out.push(...sub(ws[ci + 1], here, new Map(vars)));
        }
      }
    } else if (prog === "ln") {
      noteLink(cmd);
    } else if (INTERPRETERS.test(prog)) {
      // The script file an interpreter runs, or its stdin, is code too.
      const script = interpreterScript(cmd);
      if (script !== undefined) {
        const text = scriptText(script, cmd);
        if (text !== undefined) cmd.code.push(text);
      } else if (!codeArgs(cmd).length) {
        cmd.code.push(...stdin, ...stdinFileText(cmd));
        if (stdinUnknown(cmd)) cmd.opaque = true;
      }
      for (const body of codeOf(cmd)) for (const line of shellInCode(body)) out.push(...sub(line, here, new Map()));
    }
  }
  return out;
}

// The shell commands code runs: the strings given to os.system, subprocess, child_process,
// system(), backticks in perl/ruby and osascript's do shell script. A list of literals counts
// as one command, its words joined.
function shellInCode(code: string): string[] {
  const outs: string[] = [];
  for (const m of code.matchAll(/do\s+shell\s+script\s+"((?:\\.|[^"\\])*)"/g)) outs.push(m[1].replace(/\\(.)/g, "$1"));
  if (!SUBPROCESS.test(code)) return outs;
  for (const m of code.matchAll(/\[\s*((?:(['"])(?:\\.|(?!\2).)*\2\s*,?\s*)+)\]/g)) {
    outs.push([...m[1].matchAll(/(['"])((?:\\.|(?!\1).)*)\1/g)].map((x) => x[2]).join(" "));
  }
  for (const m of code.matchAll(/(['"])((?:\\.|(?!\1).)*)\1/g)) if (/\s/.test(m[2])) outs.push(m[2]);
  return outs.slice(0, 40);
}

// How an interpreter was called: its inline code (-c, -e, --eval, -p), the module it runs (-m),
// the script file it runs, whether it reads its program from stdin, the files its options read
// (node --env-file), the modules it loads first (node -r/--import, ruby -r), and whether it only
// checks syntax. Options are parsed per language, so python3 -I script.py runs script.py and
// perl -ne 'code' runs code.
type Interp = { lang: string; code: string[]; module?: string; moduleArgs?: string[]; script?: string; stdin: boolean; reads: string[]; preloads: string[]; check: boolean };

function interpreterOf(cmd: Cmd): Interp {
  const prog = basename(cmd.words[0] ?? "");
  const lang = /^python/.test(prog) ? "python" : prog === "nodejs" ? "node" : prog;
  const out: Interp = { lang, code: [], stdin: false, reads: [], preloads: [], check: false };
  if (!INTERPRETERS.test(prog)) return out;
  const w = cmd.words;
  // Single-letter option clusters: in `valued` a letter takes the rest of the cluster, else the
  // next word; in `attached` it takes only the rest of the cluster.
  const cluster = (a: string, k: number, valued: string, attached: string, onValue: (ch: string, v: string | undefined) => void): number => {
    for (let j = 1; j < a.length; j++) {
      const ch = a[j];
      if (valued.includes(ch)) {
        const rest = a.slice(j + 1);
        onValue(ch, rest || w[k + 1]);
        return rest ? k : k + 1;
      }
      if (attached.includes(ch)) { onValue(ch, a.slice(j + 1)); return k; }
      if (ch === "c" && (lang === "perl" || lang === "ruby")) out.check = true;
    }
    return k;
  };
  let k = 1;
  if ((lang === "bun" || lang === "deno") && /^(run|test|x)$/.test(w[1] ?? "")) k = 2;
  if ((lang === "bun" || lang === "deno") && w[1] === "eval") { if (w[2] !== undefined) out.code.push(w[2]); return out; }
  for (; k < w.length; k++) {
    const a = w[k];
    if (a === "-") { out.stdin = true; return out; }
    if (a === "--") { out.script = w[k + 1]; return out; }
    if (!a.startsWith("-")) {
      if (!out.code.length && out.module === undefined) out.script = a;
      return out;
    }
    if (lang === "python") {
      if (a.startsWith("--")) { if (a === "--check-hash-based-pycs") k++; continue; }
      let stop = false;
      k = cluster(a, k, "cmWX", "", (ch, v) => {
        if (ch === "c" && v !== undefined) { out.code.push(v); stop = true; }
        if (ch === "m") { out.module = v; stop = true; }
      });
      if (out.module !== undefined) out.moduleArgs = w.slice(k + 1);
      if (stop) return out;
    } else if (lang === "node" || lang === "bun" || lang === "deno") {
      const eq = a.indexOf("=");
      const name = a.startsWith("--") && eq > 0 ? a.slice(0, eq) : a;
      const value = a.startsWith("--") && eq > 0 ? a.slice(eq + 1) : undefined;
      // -e, -p, --eval, --print, and clusters of them (-pe, -ep): the next word is the code,
      // unless it is the other flag (-p -e CODE).
      if (/^(-[ep]+|--eval|--print)$/.test(name)) {
        if (value === undefined && /^(-[ep]+|--eval|--print)$/.test(w[k + 1] ?? "")) continue;
        const v = value ?? w[++k];
        if (v !== undefined) out.code.push(v);
        return out;
      }
      if (/^(-c|--check)$/.test(name)) { out.check = true; continue; }
      if (/^--env-file(-if-exists)?$/.test(name)) { const v = value ?? w[++k]; if (v !== undefined) out.reads.push(v); continue; }
      if (/^(-r|--require|--import|--loader|--experimental-loader)$/.test(name)) { const v = value ?? w[++k]; if (v !== undefined) out.preloads.push(v); continue; }
      if (value === undefined && /^(-r|--require|--import|--loader|--experimental-loader|-C|--conditions|--input-type|--title|--inspect-port|--debug-port|--redirect-warnings|--diagnostic-dir|--report-dir|--icu-data-dir|--openssl-config|--stack-size|--experimental-config-file)$/.test(name)) k++;
    } else if (lang === "perl") {
      k = cluster(a, k, "eEI", "iMmFxl0CdD", (ch, v) => {
        if ((ch === "e" || ch === "E") && v !== undefined) out.code.push(v);
        if ((ch === "M" || ch === "m") && v) out.preloads.push(v);
      });
    } else if (lang === "ruby") {
      k = cluster(a, k, "eIrEC", "Fx0iWT", (ch, v) => {
        if (ch === "e" && v !== undefined) out.code.push(v);
        if (ch === "r" && v !== undefined) out.preloads.push(v);
      });
    } else if (lang === "osascript") {
      if (a === "-e" && w[k + 1] !== undefined) out.code.push(w[++k]);
      else if (/^-[lsi]$/.test(a)) k++;
    }
  }
  return out;
}

// The word an interpreter runs as its script file, if it runs one.
const interpreterScript = (cmd: Cmd) => interpreterOf(cmd).script;

// The inline code an interpreter was given on its command line (-c, -e, --eval, -p, -m).
function codeArgs(cmd: Cmd): string[] {
  const i = interpreterOf(cmd);
  return [...i.code, ...(i.module !== undefined ? [i.module] : [])];
}

// The text of a file redirected into stdin (cmd < file), if it can be read.
function stdinFileText(cmd: Cmd): string[] {
  const r = cmd.redirs.find((x) => x.op === "<");
  if (!r) return [];
  const p = wordPath(r.target, cmd.cwd, cmd.vars);
  const t = p ? fileText(p, cmd) : undefined;
  return t === undefined ? [] : [t];
}

// stdin that carries code the guard cannot see: a pipe from anything but echo/printf, or a
// redirected file it cannot read.
function stdinUnknown(cmd: Cmd): boolean {
  if (cmd.code.length || cmd.stdin.length) return false;
  if (cmd.feeder) return true;
  const r = cmd.redirs.find((x) => x.op === "<");
  if (!r) return false;
  return stdinFileText(cmd).length === 0;
}

// A file's text: what this call wrote to it, else what is on disk (up to 256 KB).
function fileText(p: string, cmd: Cmd): string | undefined {
  const mine = cmd.shared.written.get(canon(p));
  if (mine !== undefined) return mine;
  try {
    if (statSync(p).size > 256 * 1024) return undefined;
    return readFileSync(p, "utf-8");
  } catch {
    return undefined;
  }
}

// A script file the call runs, read when it is ad hoc: written by this call, outside every git
// repository, or under a temp directory. A tracked script in a repository is the repository's
// own code and is not re-parsed.
function scriptText(word: string, cmd: Cmd): string | undefined {
  const p = wordPath(word, cmd.cwd, cmd.vars);
  if (!p) return undefined;
  if (cmd.shared.written.has(canon(p))) return cmd.shared.written.get(canon(p));
  if (!existsSync(p)) return undefined;
  if (!isTempPath(p) && !(TMPDIR_RE().test(canon(p))) && repoRoot(dirname(p))) return undefined;
  return fileText(p, cmd);
}

const TMPDIR_RE = () => {
  const t = canon((process.env.TMPDIR || "/tmp").replace(/\/$/, ""));
  return new RegExp("^" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "(/|$)");
};

// Records text this command writes to a file (echo/printf/cat here-doc > file), so a script
// it writes and then runs in the same call is read.
function noteWrites(cmd: Cmd) {
  const out = cmd.redirs.filter((r) => r.op === ">" || r.op === ">>" || r.op === ">|");
  if (!out.length) return;
  const prog = basename(cmd.words[0] ?? "");
  let text: string | undefined;
  if (prog === "echo") text = cmd.words.slice(1).filter((x) => !/^-[neE]+$/.test(x)).join(" ");
  else if (prog === "printf") text = cmd.words.slice(1).join(" ");
  else if (prog === "cat" && cmd.words.length === 1) text = [...cmd.code, ...cmd.stdin].join("\n");
  if (text === undefined) return;
  for (const r of out) {
    const p = wordPath(r.target, cmd.cwd, cmd.vars);
    if (p) cmd.shared.written.set(canon(p), (r.op === ">>" ? (cmd.shared.written.get(canon(p)) ?? "") + "\n" : "") + text);
  }
}

// ln [-s] target... link: maps each link this call makes to what it names, so a later write
// through the link is judged by where it lands.
function noteLink(cmd: Cmd) {
  const args = cmd.words.slice(1);
  const symbolic = args.some((a) => /^-[a-zA-Z]*s/.test(a) || a === "--symbolic");
  const plain = args.filter((a) => !a.startsWith("-"));
  if (!plain.length) return;
  const targets = plain.length === 1 ? plain : plain.slice(0, -1);
  const destWord = plain.length === 1 ? "." : plain[plain.length - 1];
  const dest = wordPath(destWord, cmd.cwd, cmd.vars);
  if (!dest) return;
  let destIsDir = false;
  try { destIsDir = statSync(dest).isDirectory() && !args.some((a) => /^-[a-zA-Z]*[nhT]/.test(a)); } catch {}
  for (const t of targets) {
    const link = destIsDir || targets.length > 1 ? join(dest, basename(t)) : dest;
    const named = symbolic ? (isAbsolute(expandVars(t, cmd.cwd, cmd.vars)) ? wordPath(t, cmd.cwd, cmd.vars) : wordPath(t, dirname(link), cmd.vars))
      : wordPath(t, cmd.cwd, cmd.vars);
    if (named) cmd.shared.links.set(link, { named, seq: cmd.seq ?? 0 });
  }
}

// Every path a word names: braces expanded, each resolved (undefined when it cannot be).
function pathsOf(word: string, cmd: Cmd): Array<string | undefined> {
  return braceExpand(word).map((w) => throughLinks(wordPath(w, cmd.cwd, cmd.vars), cmd));
}

// A path that runs through a link the same call made, rewritten to where it lands.
function throughLinks(p: string | undefined, cmd: Cmd): string | undefined {
  if (!p) return p;
  for (let k = 0; k < 8; k++) {
    let hit = false;
    // Only a link made by an earlier command counts: ln's own operands are not followed.
    for (const [link, { named, seq }] of cmd.shared?.links ?? []) {
      if (seq < (cmd.seq ?? Infinity) && under(p, link) && p !== named) { p = named + p.slice(link.length); hit = true; break; }
    }
    if (!hit) break;
  }
  return p;
}

// pathsOf, with each glob expanded on disk as the shell would: a pattern that matches nothing
// stays itself.
function globPathsOf(word: string, cmd: Cmd): Array<string | undefined> {
  const out: Array<string | undefined> = [];
  for (const p of pathsOf(word, cmd)) {
    if (p && GLOB_CHARS.test(p)) {
      const hits = expandGlob(p);
      out.push(...(hits.length ? hits : [p]));
    } else out.push(p);
  }
  return out;
}

// The code an interpreter runs from its command line, a here-document or a here-string.
function codeOf(cmd: Cmd): string[] {
  if (!INTERPRETERS.test(basename(cmd.words[0] ?? ""))) return [];
  return [...interpreterOf(cmd).code, ...cmd.code, ...cmd.redirs.filter((r) => r.op === "<<<").map((r) => r.target)];
}

const SUBPROCESS = /\bsubprocess\b|\bos\.(system|popen|exec\w*|spawn\w*|posix_spawn\w*)\b|\bpty\.spawn|child_process|\bexec(File)?(Sync)?\s*\(|\bspawn(Sync)?\s*\(|Bun\.spawn|Deno\.(run|Command)|\bsystem\b\s*[("'$]|\bqx\s*[({\/]|%x[({]|\bIO\.popen|\bOpen3\b|do\s+shell\s+script|\bexec\s+["'$]/;

// Call arguments with up to three levels of nested parentheses: open(os.path.join(f(x)), 'w').
const ARGS3 = (() => { let a = "[^()]*"; for (let k = 0; k < 3; k++) a = `(?:[^()]|\\(${a}\\))*`; return a; })();
const CODE_WRITES: Array<[RegExp, string]> = [
  [new RegExp(`\\bopen\\s*\\(${ARGS3}?,\\s*(?:mode\\s*=\\s*)?f?['"][rbt]*[wax+]`), "open() for writing"],
  [/\.open\s*\(\s*(?:mode\s*=\s*)?['"][rbt]*[wax+]/, "open() for writing"],
  [/\.write_(text|bytes)\s*\(/, "write_text()"],
  // Data libraries: pandas' to_csv and kin (the string-returning ones only when given a target),
  // numpy's save, matplotlib's savefig, torch, joblib, and any .save(...).
  [/\.to_(parquet|excel|pickle|feather|hdf|stata|orc)\s*\(|\.to_(csv|json|html|latex|markdown|xml|string)\s*\(\s*(?![)\s]|\w+\s*=(?!=))|\.to_\w+\s*\([^)]*\b(path_or_buf|buf|path)\s*=/, "a pandas write"],
  [/\b(np|numpy)\.(save|savez|savez_compressed|savetxt)\s*\(|\.(savefig|tofile|save)\s*\(|\b(torch|joblib)\.(save|dump)\s*\(/, "a data-library save"],
  [/\bshutil\.(copy\w*|move|rmtree|make_archive|unpack_archive)\s*\(/, "shutil"],
  [/\bos\.(remove|unlink|rename|replace|mkdir|makedirs|rmdir|removedirs|symlink|link|truncate)\s*\(/, "os file calls"],
  [/\.(mkdir|touch|unlink|rmdir|rename|symlink_to|hardlink_to)\s*\(/, "a pathlib write"],
  [/\b(writeFile|appendFile|mkdir|rm|rmdir|rename|unlink|copyFile|cp|symlink|truncate)(Sync)?\s*\(/, "an fs write"],
  [/\b(createWriteStream|writeFileSync|appendFileSync|copyFileSync|rmSync|unlinkSync|renameSync|symlinkSync|truncateSync|mkdirSync|cpSync|rmdirSync)\b/, "an fs write"],
  [/\bopen\s*\(?\s*(my\s+)?\$?\w*\s*,?\s*['"]\s*\+?(>>?|\|)/, "a perl open for writing"],
  [/\b(unlink|rmdir|mkdir|rename|symlink|truncate|chmod|chown|utime)\b(\s*[("'$@]|\s+\w)/, "a file call"],
  [/\bFile\.(write|delete|unlink|rename|symlink|link|truncate|chmod|chown|open|new|binwrite)|FileUtils\.|\bIO\.(write|binwrite)/, "a ruby file write"],
  [/\bsqlite3\b[\s\S]*\b(insert|update|delete|create|drop|alter|replace|vacuum|attach)\b/i, "sqlite3 writes"],
  [SUBPROCESS, "a subprocess; run the command itself in bash so it can be checked"],
];

// Code calls that remove or move a directory with everything in it.
const SWEEP_CODE = /\bshutil\.(rmtree|move)\s*\(|\bos\.(rename|renames|replace|removedirs)\s*\(|\b(rm|rmSync|rmdir|rmdirSync|cp|cpSync)\s*\([^)]*\brecursive\b|\b(rename|renameSync)\s*\(|\bFileUtils\.(rm_r|rm_rf|remove_dir|remove_entry|mv|move)\b/;

function codeWrite(code: string): string | undefined {
  for (const [re, what] of CODE_WRITES) if (re.test(code)) return what;
  return undefined;
}

// Code with each path it builds from the home directory or an absolute literal written as one
// string literal: Path.home() / 'a' / 'b', Path.home().joinpath('a', 'b'), Path(Path.home(), 'a'),
// os.path.join(os.path.expanduser('~'), 'a'), os.environ['HOME'] + '/a', path.join(os.homedir(),
// 'a'), `${os.homedir()}/a`, os.path.join('/x', 'a'), Path('/x').joinpath('a'), '/x' + '/a' and
// the like become "/Users/me/a/b" or "/x/a". open lists each such path whose build goes on with a
// part that is no literal (Path.home() / name): its end is unknown. Paths built any other way,
// a variable holding the base included, stay as they are (best-effort, for code a model writes
// in ordinary work).
const HOME_ANCHOR = new RegExp([
  String.raw`\b(?:pathlib\.)?Path\.home\(\s*\)`,
  String.raw`\b(?:os\.path\.)?expanduser\(\s*(['"])~\1\s*\)`,
  String.raw`\b(?:pathlib\.)?Path\(\s*(['"])~\2\s*\)\.expanduser\(\s*\)`,
  String.raw`\bos\.environ\[\s*(['"])HOME\3\s*\]`,
  String.raw`\b(?:os\.environ\.get|os\.getenv)\(\s*(['"])HOME\4[^()]*\)`,
  String.raw`(?:\brequire\(\s*(['"])(?:node:)?os\5\s*\)\.|\b\w+\.)?homedir\(\s*\)`,
  String.raw`\bprocess\.env(?:\.HOME\b|\[\s*(['"])HOME\6\s*\])`,
  String.raw`\$ENV\{\s*['"]?HOME['"]?\s*\}`,
  String.raw`\bDir\.home\b`,
  String.raw`\bENV\[\s*(['"])HOME\7\s*\]`,
  // An absolute or ~/ path literal, raw or byte prefixes included: group 9 is its text. A JS
  // template without a ${...} is a literal too: group 10 is its text.
  String.raw`(?:\b[rRbBuU]{1,2})?(['"])((?:\/|~\/)(?:\\.|(?!\8)[^\\])*)\8`,
  String.raw`\x60((?:\/|~\/)(?:\\.|(?!\x60|\$\{)[^\\])*)\x60`,
].join("|"), "g");
const JOIN_OPEN = /(?:\b(?:os\.path|posixpath|path)\.(?:join|resolve)|\bjoin|\bresolve|\b(?:pathlib\.)?(?:Pure|Posix)?Path)\s*\(\s*$/;
// A string literal (group 2 its text): quoted, prefixed (r'', b''), or a template without ${...}.
const STR_LIT = String.raw`(?:[rRbBuU]{1,2})?(['"\x60])((?:\\.|(?!\1|\$\{).)*)\1`;

// Folded until nothing changes, so Path('/x').joinpath('a') becomes "/x".joinpath('a'), then "/x/a".
function homeExprs(code: string): { code: string; paths: string[]; open: string[] } {
  const paths: string[] = [], open: string[] = [];
  for (let k = 0; k < 4; k++) {
    const r = foldPaths(code);
    paths.push(...r.paths);
    open.push(...r.open);
    if (r.code === code) break;
    code = r.code;
  }
  return { code, paths: [...new Set(paths)], open: [...new Set(open)] };
}

function foldPaths(code: string): { code: string; paths: string[]; open: string[] } {
  let out = "", last = 0;
  const paths: string[] = [], open: string[] = [];
  for (const m of code.matchAll(HOME_ANCHOR)) {
    const start = m.index!;
    if (start < last) continue;
    const literal = m[9] ?? m[10];
    let end = start + m[0].length;
    const segs: string[] = [];
    // How each part joins: "+" concatenates, anything else is a path join.
    const ops: string[] = [];
    let tail = false, more = false;
    // Inside join(...) or Path(...) the parts follow commas; elsewhere / (pathlib), + (strings)
    // or .joinpath(...).
    const opener = code.slice(0, start).match(JOIN_OPEN);
    const sep = new RegExp(String.raw`^\s*${opener ? "[,\/+]" : "[\/+]"}\s*${STR_LIT}`);
    for (;;) {
      const rest = code.slice(end);
      const lit = rest.match(sep);
      if (lit) { segs.push(lit[2]); ops.push(lit[0].trim()[0]); end += lit[0].length; continue; }
      const jp = opener ? null : rest.match(/^\s*\.joinpath\(\s*/);
      if (jp) {
        let k = end + jp[0].length;
        const parts: string[] = [];
        for (;;) {
          const a = code.slice(k).match(new RegExp(String.raw`^${STR_LIT}\s*(,\s*)?`));
          if (!a) break;
          parts.push(a[2]);
          k += a[0].length;
        }
        const close = code.slice(k).match(/^\)/);
        if (!close || !parts.length) { more = true; break; }
        segs.push(...parts);
        ops.push(...parts.map(() => ","));
        end = k + 1;
        continue;
      }
      // Inside a template or f-string, ${os.homedir()}/a or {Path.home()}/a: the text after it.
      const t = !literal && /\{\s*$/.test(code.slice(0, start)) ? rest.match(/^\s*\}([^`'"{}$]*)/) : null;
      if (t && !segs.length) { segs.push(t[1]); tail = true; break; }
      if ((opener ? /^\s*[,\/+]/ : /^\s*[\/+]/).test(rest)) more = true;
      break;
    }
    let path = literal !== undefined ? expandTilde(literal) : home();
    segs.forEach((x, i) => { path = ops[i] === "+" ? path + x : join(path, x.replace(/^\/+/, "")); });
    path = join(path);
    const close0 = code.slice(end).match(/^\s*\)/);
    // A literal with nothing joined to it stays as it is: the literal checks read it.
    if (literal !== undefined && !segs.length && !(opener && close0)) {
      if (more) open.push(path);
      continue;
    }
    if (literal === undefined || segs.length) paths.push(path);
    if (more) open.push(path);
    if (tail) {
      // The template keeps its quotes; the home directory's text replaces the expression.
      const pre = code.slice(0, start).match(/\$?\{\s*$/)![0].length;
      const close = code.slice(end).match(/^\s*\}/)![0].length;
      out += code.slice(last, start - pre) + home();
      last = end + close;
      continue;
    }
    let from = start, to = end;
    // path.join(home, 'a', 'b') and Path(home, 'a') as a whole.
    const close = code.slice(end).match(/^\s*\)/);
    if (opener && close) { from = start - opener[0].length; to = end + close[0].length; }
    if (from < last) { from = start; to = end; }
    out += code.slice(last, from) + JSON.stringify(path);
    last = to;
  }
  return { code: out + code.slice(last), paths, open };
}

// JS template literals without a ${...}: plain strings.
const templates = (code: string) => [...code.matchAll(/\x60((?:\\.|(?!\x60|\$\{)[^\\])*)\x60/g)].map((m) => m[1]);

// The string literals in code that may name a file it writes: the first argument of a file
// call, and any literal shaped like a path (a slash or an extension). A bare word such as a
// subprocess's program name is not one.
function codeLiterals(code: string) {
  const first = [...code.matchAll(/\b(open|Path|write_text|write_bytes|writeFile(?:Sync)?|appendFile(?:Sync)?|createWriteStream|copyfile|copy2?|move|rename|remove|unlink|rmtree)\s*\(\s*(['"])((?:\\.|(?!\2).)*)\2/g)].map((m) => m[3]);
  const shaped = [...code.matchAll(/(['"])((?:\\.|(?!\1).)*)\1/g)].map((m) => m[2]).concat(templates(code))
    .filter((s) => s.length < 400 && !/\s/.test(s) && (s.includes("/") || /\.[A-Za-z0-9]{1,8}$/.test(s) || GLOB_CHARS.test(s)));
  return [...new Set([...first, ...shaped])];
}

const NAME_ONLY = new Set(["ls", "test", "[", "[[", "stat", "file", "du", "which", "type", "echo", "printf", "true",
  "false", "realpath", "readlink", "basename", "dirname", "wc", "cd", "pushd", "mkdir", "touch", "chmod", "exit", "export", "unset", "local"]);
const ALWAYS_RECURSIVE = new Set(["rg", "ag", "rsync", "tar", "zip", "ditto", "scp", "find"]);
const RECURSIVE_FLAG = /^(-[a-zA-Z]*[rRa][a-zA-Z]*|--recursive|--archive)$/;
const DEV_TARGET = /^(\/dev\/(null|stdout|stderr|tty|fd\/\d+)|&?\d+|-)$/;

// Searchers and filters whose first operand is a pattern or a script, not a file: what marks
// the pattern given by flag instead, and which flags take a file.
const PATTERN_FIRST: Record<string, { given: RegExp; file: RegExp; value?: RegExp }> = {
  grep: { given: /^(-e|--regexp|-f|--file)(=|$)|^-e./, file: /^(-f|--file)$/, value: /^(-[ABCmD]|--(context|after-context|before-context|max-count|label))$/ },
  rg: { given: /^(-e|--regexp|-f|--file)(=|$)|^-e./, file: /^(-f|--file)$/, value: /^(-[ABCmMtTj]|--(type|type-not|max-count|context|max-columns|threads))$/ },
  sed: { given: /^(-e|--expression|-f|--file)(=|$)|^-[a-zA-Z]*[ef]$/, file: /^(-f|--file)$/ },
  awk: { given: /^(-f|--file)(=|$)/, file: /^(-f|--file)$/, value: /^-[vF]$/ },
  jq: { given: /^(-f|--from-file)$/, file: /^(-f|--from-file)$/ },
};
for (const [alias, of] of [["egrep", "grep"], ["fgrep", "grep"], ["zgrep", "grep"], ["ag", "rg"], ["ack", "rg"], ["gsed", "sed"],
  ["gawk", "awk"], ["mawk", "awk"], ["nawk", "awk"]]) PATTERN_FIRST[alias] = PATTERN_FIRST[of];

// The words a command reads as files, and (find) the name patterns it matches.
function operandsOf(cmd: Cmd): { paths: string[]; names: string[]; roots: string[] } {
  const prog = basename(cmd.words[0]);
  const args = cmd.words.slice(1);
  if (prog === "find") {
    const end = args.findIndex((a) => a.startsWith("-") || a === "(" || a === "!");
    const roots = end < 0 ? args : args.slice(0, end);
    const names: string[] = [];
    for (let k = 0; k < args.length; k++) if (/^-(i?name|i?path|i?wholename)$/.test(args[k]) && args[k + 1]) names.push(args[++k]);
    return { paths: roots.length ? roots : ["."], names, roots: roots.length ? roots : ["."] };
  }
  const g = gitParts(cmd);
  let rule = PATTERN_FIRST[prog];
  let rest = args;
  if (g) {
    rest = g.args;
    if (g.sub === "grep") rule = PATTERN_FIRST.grep;
  }
  const paths: string[] = [];
  const patternGiven = rule ? rest.some((a) => rule!.given.test(a)) : true;
  let skipped = false;
  for (let k = 0; k < rest.length; k++) {
    const a = rest[k];
    if (g && /^(-S|-G|--grep|--author|--committer|-e)$/.test(a)) { k++; continue; }
    if (rule) {
      if (rule.file.test(a)) { if (rest[k + 1]) paths.push(rest[++k]); continue; }
      if (/^(-e|--regexp|--expression)$/.test(a) || (rule.value && rule.value.test(a))) { k++; continue; }
      if (!patternGiven && !skipped && !a.startsWith("-")) { skipped = true; continue; }
    }
    paths.push(a);
  }
  return { paths, names: [], roots: [] };
}

// What inline code (an interpreter's -c/-e, a here-document or script fed to it) names that
// is a credential: a path segment or file name, however the path is built (pathlib's /,
// os.path.join, expanduser, string concatenation).
const CODE_CREDENTIALS: Array<[RegExp, string]> = [
  [/\.local[\/'"\s,]+share[\/'"\s,]+opencode/i, "OpenCode's data directory, which holds auth.json"],
  [/\bid_(rsa|dsa|ecdsa|ed25519)(_sk)?\b(?!\.pub)/i, "an SSH private key"],
  [/(^|[^\w])\.ssh\b/i, "~/.ssh, where SSH keys live"],
  [/\bkeys\.env\b/i, "keys.env"],
  [/(['"`\/])[\w.*?-]*\.env(?=['"`\/*])/i, "an env file of keys"],
  [/\bdotenv\b/i, "dotenv, which reads .env files of keys"],
  [/\bloadEnvFile\b|--env-file\b/, "Node's .env loader, which reads env files of keys"],
  [/\brclone\b/i, "rclone's config"],
  [/media-syncer/i, "media-syncer's config"],
  [/backup-private/i, "backup-private/"],
  [/api-keys/i, "the API key store"],
];

function codeCredential(code: string): string | undefined {
  if (/\bauth\.json\b/i.test(code) && /opencode/i.test(code)) return "OpenCode's auth.json, which holds the DeepSeek key";
  for (const [re, what] of CODE_CREDENTIALS) if (re.test(code)) return what;
  return undefined;
}

function credentialInCommand(cmd: Cmd): string | undefined {
  for (const r of cmd.redirs) {
    if (r.op === "<<<" || DEV_TARGET.test(r.target)) continue;
    for (const p of pathsOf(r.target, cmd)) {
      const what = p && credentialOf(p);
      if (what) return `${r.op.includes("<") ? "reads" : "writes"} ${what}`;
    }
  }
  // Files a wrapper or xargs -a reads (uv run --env-file, node --env-file, xargs -a).
  for (const f of [...(cmd.argFiles ?? []), ...(cmd.reads ?? []), ...interpreterOf(cmd).reads]) {
    for (const p of pathsOf(f, cmd)) {
      const what = p && credentialOf(p);
      if (what) return `reads ${what}`;
    }
  }
  for (const body of codeOf(cmd)) {
    const what = codeCredential(body);
    if (what) return `runs code that names ${what}`;
  }
  // A module the interpreter runs or loads first (python3 -m dotenv, node -r dotenv/config), and
  // the options variables that load one (NODE_OPTIONS, RUBYOPT, PERL5OPT).
  const it = interpreterOf(cmd);
  const opts = [...cmd.assigns.map((a) => a.match(/^(NODE_OPTIONS|RUBYOPT|PERL5OPT)=(.*)$/s)?.[2]),
    ...["NODE_OPTIONS", "RUBYOPT", "PERL5OPT"].map((n) => cmd.vars.get(n))].filter((x): x is string => typeof x === "string");
  for (const m of [...it.preloads, ...(it.module !== undefined ? [it.module] : []), ...opts]) {
    const what = codeCredential(m);
    if (what) return `loads a module that names ${what}`;
  }
  if (!cmd.words.length) return undefined;
  const prog = basename(cmd.words[0]);
  if (ENV_LOADERS.test(prog)) return `runs ${prog}, which loads .env files of keys`;
  const env = environmentDump(cmd);
  if (env) return env;
  if (NAME_ONLY.has(prog)) return undefined;
  if (["check-ignore", "ls-files", "status"].includes(gitParts(cmd)?.sub ?? "")) return undefined;
  const recursive = ALWAYS_RECURSIVE.has(prog) || cmd.words.slice(1).some((x) => RECURSIVE_FLAG.test(x));
  const { paths, names } = operandsOf(cmd);
  // A recursive reader of content (not find, which lists names) has every file below each
  // operand walked; --include / -g narrow the walk to what it reads.
  const tarReads = !/^(tar|bsdtar|gtar)$/.test(prog) || /^-?[a-zA-Z]*[cru]/.test(cmd.words[1] ?? "") || cmd.words.some((a) => /^(-[a-zA-Z]*[cru][a-zA-Z]*|--create|--append|--update)$/.test(a));
  const walks = ((recursive && prog !== "find" && CONTENT_READERS.has(prog) && tarReads) || ["rg", "ag", "ack"].includes(prog)) && !cmd.words.includes("--files");
  const includes = walks ? includeGlobs(cmd) : [];
  const deep = (p: string): string | undefined => {
    if (!walks) return recursive ? holdsCredential(p) : undefined;
    const r = credentialUnder(p, includes);
    if (r.what) return r.what;
    if (r.unchecked) return `everything under ${p}, too many files to check for credentials (name the files, or narrow the path)`;
    return undefined;
  };
  if (walks && ["grep", "egrep", "fgrep", "rg", "ag", "ack"].includes(prog) && !paths.some((w) => !w.startsWith("-")) && !cmd.feeder && !cmd.redirs.some((r) => r.op.startsWith("<"))) {
    const what = deep(cmd.cwd);
    if (what) return `reads ${what}`;
  }
  for (const word of paths) {
    // curl -F f=@path, --data @path, name=path; and the words inside $(...) or backticks.
    const forms = [word, word.replace(/^[^=@]*[=@]+/, ""), word.replace(/^@/, "")];
    if (/\$\(|`/.test(word)) forms.push(...word.split(/[\s()`'"$;|&<>]+/));
    // defaults reads a plist named without its extension, by path or by domain.
    if (prog === "defaults" && !word.startsWith("-") && !word.endsWith(".plist")) {
      forms.push(word.includes("/") ? `${word}.plist` : join(home(), "Library", "Preferences", `${word}.plist`));
    }
    for (const f of new Set(forms)) {
      if (!f || f.startsWith("-")) continue;
      for (const p of pathsOf(f, cmd)) {
        if (!p) continue;
        const what = credentialOf(p) ?? deep(p);
        if (what) return `reads ${what}`;
      }
    }
  }
  // find -name keys.env: the name is checked as a file in any of its roots.
  for (const name of names) {
    const what = credentialOf(join(cmd.cwd, ".find", name.replace(/^\*\*?\//, "")), false);
    if (what) return `reads ${what}`;
  }
  // A reader whose file the guard cannot resolve (a substitution, a loop variable, a pipe into
  // xargs) passes only when every file it could reach is checked and none is a credential.
  const lister = cmd.lister ?? cmd.feeder;
  if (INTERPRETERS.test(prog)) {
    // Code given a lister's names, as arguments through xargs or as lines on stdin, may open
    // each one: everything the lister names is checked. Other feeders stay unchecked.
    const named = (cmd.xargs && !cmd.stdin.length && !cmd.scope) ||
      (!!cmd.feeder && !cmd.xargs && (it.code.length > 0 || it.module !== undefined || it.script !== undefined));
    const scope = named && lister ? listerScope(lister.words, lister.cwd, lister.vars) : undefined;
    for (const root of scope?.roots ?? []) {
      const r = credentialUnder(root, scope!.names);
      if (r.what) return `runs code on the names a lister gives it, which may reach ${r.what}`;
      if (r.unchecked) return `runs code on the names a lister gives it, and ${root} is too large to check. Name the files`;
    }
    return undefined;
  }
  if (!CONTENT_READERS.has(prog)) return undefined;
  const opaque: Array<[string, Scope | undefined]> = [];
  for (const word of paths) {
    if (word.startsWith("-") || DEV_TARGET.test(word)) continue;
    if (pathsOf(word, cmd).some((p) => p === undefined)) opaque.push([word, scopeOfWord(word, cmd)]);
  }
  if (cmd.xargs && !cmd.stdin.length && !cmd.scope) opaque.push(["the names xargs reads", lister ? listerScope(lister.words, lister.cwd, lister.vars) : undefined]);
  for (const [word, scope] of opaque) {
    const cannot = `reads ${word}, which the guard cannot resolve to a file`;
    if (!scope) return `${cannot}. Name the file, or use the read and grep tools`;
    for (const root of scope.roots) {
      const r = credentialUnder(root, scope.names);
      if (r.what) return `${cannot}, and it may reach ${r.what}`;
      if (r.unchecked) return `${cannot}, and ${root} is too large to check. Name the file, or use the read and grep tools`;
    }
  }
  return undefined;
}

// Command-line env loaders: each reads a .env file of keys into a program's environment.
const ENV_LOADERS = /^(dotenv|dotenvx|dotenv-cli|env-cmd|dotenv-run)$/;

// Programs that read the content of the files they are given.
const CONTENT_READERS = new Set(["cat", "head", "tail", "less", "more", "bat", "nl", "od", "xxd", "hexdump", "strings", "base64",
  "cp", "scp", "rsync", "ditto", "tar", "zip", "grep", "egrep", "fgrep", "zgrep", "rg", "ag", "ack", "sed", "gsed", "awk",
  "gawk", "mawk", "nawk", "jq", "sort", "uniq", "cut", "paste", "diff", "cmp", "comm", "source", ".", "plutil", "defaults", "pbcopy",
  "tac", "rev", "fold", "fmt", "pr", "column", "iconv", "gzip", "bzip2", "xz", "zcat", "openssl", "dd", "split", "join", "look",
  "expand", "unexpand", "view", "vim", "vi", "nvim", "ed", "ex", "emacs", "nano", "mail", "nc", "ncat", "socat", "gpg", "age"]);

type Scope = { roots: string[]; names: RegExp[] };

// The file-name globs a recursive search is limited to: grep --include, rg -g/--glob.
function includeGlobs(cmd: Cmd): RegExp[] {
  const out: RegExp[] = [];
  const a = cmd.words.slice(1);
  for (let k = 0; k < a.length; k++) {
    let v: string | undefined;
    if (/^(--include|-g|--glob|--iglob)$/.test(a[k])) v = a[++k];
    else { const m = a[k].match(/^--(include|glob|iglob)=(.*)$/); if (m) v = m[2]; }
    if (v === undefined) continue;
    if (v.startsWith("!")) continue;
    out.push(globRegex(basename(v)));
  }
  return out;
}

// Where an unresolved word's files can be: the roots of the lister in a whole-word $(...), or
// the directory written before the first expansion. Undefined when it could be anywhere.
function scopeOfWord(word: string, cmd: Cmd): Scope | undefined {
  const whole = word.match(/^\$\(([\s\S]*)\)$|^`([\s\S]*)`$/);
  if (whole) {
    const inner = tokenize(whole[1] ?? whole[2]);
    if (inner.length !== 1) return undefined;
    return listerScope(unwrap(inner[0].words).words, cmd.cwd, cmd.vars);
  }
  const k = word.search(/[$`]/);
  const prefix = k < 0 ? "" : word.slice(0, k);
  const slash = prefix.lastIndexOf("/");
  if (slash < 0) return undefined;
  const dir = wordPath(prefix.slice(0, slash) || "/", cmd.cwd, cmd.vars);
  return dir ? { roots: [dir], names: [] } : undefined;
}

// The files a listing command names: find, ls, git ls-files, grep -l and the like, by root and
// (find -name) by pattern. Undefined for any other command. A root holding a glob is expanded
// on disk as the shell would, relative to cwd, so ls *.env names each match.
function listerScope(words: string[], cwd: string, vars: Vars): Scope | undefined {
  const prog = basename(words[0] ?? "");
  const resolveAll = (ws: string[]) => {
    const roots = ws.length ? ws : ["."];
    const out: string[] = [];
    for (const r of roots.flatMap((x) => braceExpand(x))) {
      const p = wordPath(r, cwd, vars);
      if (p === undefined) return undefined;
      const hits = GLOB_CHARS.test(p) ? expandGlob(p) : [];
      out.push(...(hits.length ? hits : [p]));
    }
    return out;
  };
  if (prog === "find") {
    const args = words.slice(1);
    const end = args.findIndex((a) => a.startsWith("-") || a === "(" || a === "!");
    const roots = resolveAll(end < 0 ? args : args.slice(0, end));
    if (!roots) return undefined;
    const names: RegExp[] = [];
    let other = false;
    for (let k = 0; k < args.length; k++) {
      if (/^-i?name$/.test(args[k]) && args[k + 1] !== undefined) names.push(globRegex(args[++k]));
      else if (/^-(i?path|i?wholename|i?regex|o|or|not)$/.test(args[k]) || args[k] === "!") other = true;
    }
    return { roots, names: other ? [] : names };
  }
  if (prog === "ls") {
    const roots = resolveAll(words.slice(1).filter((a) => !a.startsWith("-")));
    return roots ? { roots, names: [] } : undefined;
  }
  if (prog === "git" && words.includes("ls-files")) {
    const root = repoRoot(cwd);
    return root ? { roots: [root], names: [] } : undefined;
  }
  if (["grep", "egrep", "fgrep", "rg", "ag"].includes(prog) && words.some((a) => /^-[a-zA-Z]*[lL]|^--files/.test(a))) {
    const fake: Cmd = { words, redirs: [], code: [], cwd, vars, stdin: [], assigns: [], shared: { links: new Map(), written: new Map(), seq: 0 } };
    const roots = resolveAll(operandsOf(fake).paths.filter((a) => !a.startsWith("-")));
    return roots ? { roots, names: [] } : undefined;
  }
  return undefined;
}

const SKIP_DIRS = new Set([".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox"]);

// The first credential at or below root (matching one of names, when given); unchecked when the
// tree is too large to walk.
function credentialUnder(root: string, names: RegExp[] = [], budget = 20000): { what?: string; unchecked?: boolean } {
  const fits = (n: string) => !names.length || names.some((re) => re.test(n));
  // The known credential locations below root count whether or not they exist yet.
  const c = canon(root);
  const { auths, dirs } = credentialRoots(c);
  if (auths.some((auth) => under(auth, c) && auth !== c) && fits("auth.json")) return { what: AUTH_WHAT };
  for (const [d, what] of dirs) if (under(d, c) && d !== c) return { what };
  let st;
  try { st = statSync(root); } catch { return {}; }
  if (!st.isDirectory()) {
    const what = fits(basename(root)) ? credentialOf(root, false) : undefined;
    return what ? { what } : {};
  }
  const top = credentialOf(root, false) ?? (names.length ? undefined : holdsCredential(root));
  if (top) return { what: top };
  const stack = [root];
  let count = 0;
  while (stack.length) {
    const d = stack.pop()!;
    let entries;
    try { entries = readdirSync(d, { withFileTypes: true }); } catch { continue; }
    for (const e of entries) {
      if (++count > budget) return { unchecked: true };
      const p = join(d, e.name);
      if (e.isDirectory()) {
        if (SKIP_DIRS.has(e.name)) continue;
        const what = names.length ? undefined : credentialOf(p, false);
        if (what) return { what };
        stack.push(p);
      } else if (fits(e.name)) {
        const what = credentialOf(p, false);
        if (what) return { what };
      }
    }
  }
  return {};
}

// launchctl and ps can print a job's or a process's environment, where the keys live, and
// rclone config show/dump prints rclone.conf.
function environmentDump(cmd: Cmd): string | undefined {
  const prog = basename(cmd.words[0] ?? "");
  const args = cmd.words.slice(1);
  if (prog === "rclone") {
    const k = args.indexOf("config");
    const sub = k < 0 ? undefined : args.slice(k + 1).find((a) => !a.startsWith("-"));
    if (sub === "show" || sub === "dump") return `prints rclone's config (rclone config ${sub}), which holds its remotes' tokens`;
  }
  if (prog === "launchctl") {
    const pos = args.filter((a) => !a.startsWith("-"));
    if (pos[0] === "export") return "prints launchd's environment, which may hold keys";
    if (pos[0] === "getenv" && pos[1] && KEYISH_BIN.test(pos[1].toUpperCase())) return `reads ${pos[1]} from launchd's environment, a key`;
    if (["print", "list", "blame", "procinfo", "dumpstate"].includes(pos[0] ?? "") && pos[1]) {
      const label = pos[1].split("/").pop()!;
      for (const d of [join(home(), "Library", "LaunchAgents"), "/Library/LaunchAgents", "/Library/LaunchDaemons"]) {
        const plist = join(d, `${label}.plist`);
        if (existsSync(plist) && plistHoldsKeys(plist)) return `prints the environment of ${label}, whose plist ${basename(plist)} holds keys`;
      }
    }
  }
  if (prog === "ps" && (args.some((a) => /^-[a-zA-Z]*E/.test(a)) || (args[0] !== undefined && !args[0].startsWith("-") && /^[a-zA-Z]*e[a-zA-Z]*$/.test(args[0])))) {
    return "prints processes' environments, which hold keys";
  }
  return undefined;
}

// git's subcommand and arguments after its global options, and the directory it runs in.
function gitParts(cmd: Cmd): { sub: string; args: string[]; dir: string } | undefined {
  if (basename(cmd.words[0] ?? "") !== "git") return undefined;
  let dir = cmd.cwd;
  let k = 1;
  while (k < cmd.words.length && cmd.words[k].startsWith("-")) {
    const f = cmd.words[k];
    if (f === "-C" && cmd.words[k + 1]) { dir = wordPath(cmd.words[k + 1], dir, cmd.vars) ?? dir; k += 2; continue; }
    if (f === "-c" || f === "--git-dir" || f === "--work-tree" || f === "--namespace") { k += 2; continue; }
    k++;
  }
  if (k >= cmd.words.length) return undefined;
  return { sub: cmd.words[k], args: cmd.words.slice(k + 1), dir };
}

const GIT_WRITES = new Set(["read-tree", "checkout-index", "commit-tree", "write-tree", "hash-object", "mktree", "mktag", "fast-import",
  "unpack-objects", "index-pack", "pack-objects", "prune-packed", "difftool", "mergetool", "send-email", "filter-repo", "replay",
  "citool", "gui", "instaweb",
  "add", "stage", "commit", "push", "merge", "checkout", "switch", "reset", "rebase", "stash",
  "cherry-pick", "revert", "am", "apply", "rm", "mv", "restore", "clean", "pull", "init", "clone", "gc", "update-ref",
  "update-index", "notes", "filter-branch", "replace", "fetch", "prune", "repack", "maintenance", "sparse-checkout", "bisect"]);

// A git long option as itself or as an abbreviation git accepts (parse-options takes a unique
// prefix): name is the option, min its shortest prefix counted.
function gitLong(a: string, name: string, min: string): boolean {
  const opt = a.split("=")[0];
  return opt.startsWith(min) && name.startsWith(opt);
}

// An option that makes git write a file or run a program: --output, --ext-diff, --textconv,
// and git grep's -O / --open-files-in-pager (also inside a cluster such as -iO).
function gitRisky(g: { sub: string; args: string[] }): string | undefined {
  for (const a of g.args) {
    if (a === "--") break;
    if (gitLong(a, "--output", "--ou") || gitLong(a, "--output-directory", "--output-")) return "--output";
    if (gitLong(a, "--ext-diff", "--ext")) return "--ext-diff";
    if (gitLong(a, "--textconv", "--textc")) return "--textconv";
    if (g.sub === "grep" && (gitLong(a, "--open-files-in-pager", "--op") || /^-[a-zA-Z]*O/.test(a))) return "-O (opens a pager program)";
  }
  return undefined;
}

function gitWrite(g: { sub: string; args: string[] }): boolean {
  const pos = g.args.filter((a) => !a.startsWith("-"));
  if (gitRisky(g)) return true;
  switch (g.sub) {
    case "grep": return false;
    case "format-patch": return !g.args.includes("--stdout");
    case "bundle": return pos[0] !== "verify" && pos[0] !== "list-heads";
    case "archive": return g.args.some((a) => /^-o|^--output/.test(a));
    case "symbolic-ref": return pos.length > 1 || g.args.some((a) => /^(-d|--delete)$/.test(a));
    case "fsck": return g.args.includes("--lost-found");
    case "hash-object": return g.args.includes("-w");
    case "rerere": return pos[0] !== "status" && pos[0] !== "diff";
    case "stash": return !["list", "show"].includes(pos[0] ?? "push");
    case "worktree": return ["add", "remove", "move", "prune", "lock", "unlock", "repair"].includes(pos[0] ?? "");
    case "branch": return g.args.some((a) => /^-[dDmMcC]$|^--(delete|move|copy|set-upstream-to|unset-upstream)/.test(a)) ||
      (pos.length > 0 && !g.args.some((a) => /^(-l|--list|-a|--all|-r|--remotes|--contains|--merged|--no-merged|--show-current|-v|-vv)$/.test(a)));
    case "tag": return pos.length > 0 && !g.args.some((a) => a === "-l" || a === "--list" || a === "-v" || a === "--verify");
    case "config": return !g.args.some((a) => /^(--get|--get-all|--get-regexp|-l|--list|--show-origin)/.test(a)) && pos.length > 1;
    case "remote": return ["add", "remove", "rm", "rename", "set-url", "set-head", "prune"].includes(pos[0] ?? "");
    case "submodule": return pos.length > 0 && pos[0] !== "status";
    case "apply": return !g.args.some((a) => /^--(check|stat|numstat|summary)$/.test(a));
    default: return GIT_WRITES.has(g.sub) || !GIT_COMMANDS.has(g.sub);
  }
}

const PKG_WRITES: Record<string, RegExp> = {
  brew: /^(install|reinstall|upgrade|uninstall|remove|rm|bundle|link|unlink|tap|untap|cleanup|pin|unpin|services)$/,
  npm: /^(install|i|ci|add|uninstall|remove|rm|update|up|link|publish|exec|x)$/, pnpm: /^(install|i|add|remove|rm|update|up|dlx|exec)$/,
  yarn: /^(install|add|remove|upgrade|dlx)$/, bun: /^(install|i|add|remove|rm|update|link|x)$/,
  pip: /^(install|uninstall|download)$/, pip3: /^(install|uninstall|download)$/, pipx: /^(install|uninstall|upgrade|inject|run)$/,
  mise: /^(install|i|use|u|lock|upgrade|up|uninstall|rm|prune|trust)$/, cargo: /^(install|uninstall|add|remove|update|fmt|fix|build)$/,
  go: /^(install|get|build|generate|mod)$/, gem: /^(install|uninstall|update)$/, launchctl: /^(load|unload|bootstrap|bootout|kickstart|enable|disable)$/,
  uv: /^(add|remove|sync|lock|venv|init|build|publish|tool|pip)$/,
};
// A package manager's subcommand, past its global options, and the directory one of them
// moves it to (npm --prefix, pnpm -C/--dir, yarn and bun --cwd).
const PKG_OPTS: Record<string, { valued: RegExp; chdir: RegExp }> = {
  npm: { valued: /^(--prefix|-C|-w|--workspace|--userconfig|--cache|--registry|--loglevel)$/, chdir: /^(--prefix|-C)$/ },
  pnpm: { valued: /^(-C|--dir|-F|--filter|--loglevel|--reporter)$/, chdir: /^(-C|--dir)$/ },
  yarn: { valued: /^(--cwd)$/, chdir: /^--cwd$/ },
  bun: { valued: /^(--cwd|-c|--config)$/, chdir: /^--cwd$/ },
};
function pkgCall(prog: string, args: string[]): { sub?: string; dir?: string } {
  const o = PKG_OPTS[prog];
  let dir: string | undefined;
  for (let k = 0; k < args.length; k++) {
    const a = args[k];
    if (!a.startsWith("-")) return { sub: a, dir };
    if (!o) continue;
    const eq = a.match(/^(--[\w-]+)=([\s\S]*)$/);
    if (eq) { if (o.chdir.test(eq[1])) dir = eq[2]; continue; }
    if (o.valued.test(a) && args[k + 1] !== undefined) { if (o.chdir.test(a)) dir = args[k + 1]; k++; }
  }
  return { dir };
}

// What a gh subcommand group does that writes.
const GH_WRITES = /^(create|merge|close|reopen|edit|comment|review|ready|checkout|delete|transfer|lock|unlock|pin|unpin|upload|download|fork|clone|rename|archive|unarchive|sync|set|run|rerun|cancel|enable|disable|add|remove|develop|deploy)$/;
const SQL_WRITE = /\b(insert|update|delete|drop|create|alter|replace|vacuum|attach|reindex|upsert)\b|\bpragma\s+\w+\s*=|(^|;)\s*\.(import|save|backup|restore|clone|output|once|shell|system|load|excel|open|log)\b/im;
const SQL_EXEC = /(^|;|\n)\s*\.(shell|system|load|output|once|excel|log|save|backup|import|clone|dump\s+\S)|\b(writefile|edit|load_extension)\s*\(/i;
const DRY_RUN = /^(-n|--dry-run|--just-print|--recon|-q|--question|--check|--diff)$/;

// The files a sed script writes (w/W, s///w) and whether it runs commands (e, s///e).
function sedScan(script: string): { files: string[]; exec: boolean } {
  const files: string[] = [];
  let exec = false;
  for (const line of script.split("\n")) {
    let rest = line;
    for (let k = 0; k < 50; k++) {
      const m = rest.match(/(^|[^A-Za-z])s([^\w\s\\])((?:\\.|(?!\2)[^\\])*)\2((?:\\.|(?!\2)[^\\])*)\2([gpiImMe0-9]*)(w\s*(.*))?/);
      if (!m) break;
      if (m[5].includes("e")) exec = true;
      if (m[6] !== undefined) { if (m[7].trim()) files.push(m[7].trim()); rest = rest.slice(0, m.index!); break; }
      rest = rest.slice(0, m.index!) + m[1] + rest.slice(m.index! + m[0].length);
    }
    rest = rest.replace(/(^|[^A-Za-z])y([^\w\s\\])(?:\\.|(?!\2)[^\\])*\2(?:\\.|(?!\2)[^\\])*\2/g, "$1").replace(/\/(?:\\.|[^\/\\])*\//g, "");
    const w = rest.match(/(?:^|[;{}!0-9$,\s])\s*[wW]\s*(\S.*)$/);
    if (w) files.push(w[1].trim());
    if (/(?:^|[;{}!0-9$,])\s*e(?:\s|;|$)/.test(rest)) exec = true;
  }
  return { files, exec };
}

function sedWrites(cmd: Cmd): { files: string[]; other?: string } {
  const args = cmd.words.slice(1);
  const scripts: string[] = [];
  let given = false, other: string | undefined;
  for (let k = 0; k < args.length; k++) {
    const a = args[k];
    if (/^(-[a-zA-Z]*e|--expression)$/.test(a)) { given = true; if (args[k + 1] !== undefined) scripts.push(args[++k]); continue; }
    if (a.startsWith("--expression=")) { given = true; scripts.push(a.slice(13)); continue; }
    if (/^(-[a-zA-Z]*f|--file)$/.test(a) || a.startsWith("--file=")) {
      given = true;
      const f = a.startsWith("--file=") ? a.slice(7) : args[++k];
      const p = f !== undefined ? wordPath(f, cmd.cwd, cmd.vars) : undefined;
      const text = p ? fileText(p, cmd) : undefined;
      if (text === undefined) other = "sed -f with a script the guard cannot read";
      else scripts.push(text);
    }
  }
  if (!given) { const first = args.find((a) => !a.startsWith("-")); if (first !== undefined) scripts.push(first); }
  const files: string[] = [];
  for (const sc of scripts) {
    const r = sedScan(sc);
    files.push(...r.files.filter((f) => !DEV_TARGET.test(f)));
    if (r.exec) other = "sed's e command, which runs a shell command";
  }
  return { files, other };
}

// The files a git command writes besides the repository: --output, archive -o, bundle create;
// dir: where format-patch writes its patches ("" for the repository's directory).
function gitOutputs(g: { sub: string; args: string[] }): { files: string[]; dir?: string } {
  const files: string[] = [];
  let dir: string | undefined;
  const a = g.args;
  for (let k = 0; k < a.length; k++) {
    if (gitLong(a[k], "--output", "--ou") && !a[k].includes("=") && a[k + 1] !== undefined) files.push(a[++k]);
    else if (gitLong(a[k], "--output", "--ou") && a[k].includes("=")) files.push(a[k].slice(a[k].indexOf("=") + 1));
    else if (g.sub === "archive" && a[k] === "-o" && a[k + 1] !== undefined) files.push(a[++k]);
    else if (g.sub === "archive" && /^-o./.test(a[k])) files.push(a[k].slice(2));
  }
  const pos = a.filter((x) => !x.startsWith("-"));
  if (g.sub === "bundle" && pos[0] === "create" && pos[1]) files.push(pos[1]);
  if (g.sub === "format-patch" && !a.includes("--stdout")) {
    const k = a.findIndex((x) => x === "-o" || x === "--output-directory");
    dir = k >= 0 && a[k + 1] !== undefined ? a[k + 1] : a.find((x) => x.startsWith("--output-directory="))?.slice(19) ?? "";
  }
  return { files: files.filter((f) => f !== "-" && f !== "/dev/stdout"), dir };
}

// What one simple command writes: named targets; a description when it writes somewhere that
// cannot be named (git, package managers, code); and `here`, the directory such an unnamed
// write lands in when it lands in the working tree (deep: anywhere below it).
function writesOf(cmd: Cmd): { targets: string[]; other?: string; here?: string; deep?: boolean } {
  const targets: string[] = [];
  let other: string | undefined;
  let here: string | undefined;
  let deep = false;
  for (const r of cmd.redirs) {
    if (!/>/.test(r.op) || r.op === ">&" && /^\d+$|^-$/.test(r.target) || DEV_TARGET.test(r.target)) continue;
    targets.push(r.target);
  }
  const w = cmd.words;
  if (!w.length) return { targets };
  const prog = basename(w[0]);
  const args = w.slice(1);
  const plain = args.filter((a) => !a.startsWith("-"));
  const valueOf = (re: RegExp) => {
    for (let k = 0; k < args.length; k++) {
      if (re.test(args[k]) && args[k + 1] !== undefined) return args[k + 1];
      const m = args[k].match(/^--[\w-]+=(.*)$/);
      if (m && re.test(args[k].split("=")[0])) return m[1];
    }
    return undefined;
  };
  const dir = (v: string | undefined) => (v === undefined ? cmd.cwd : wordPath(v, cmd.cwd, cmd.vars) ?? cmd.cwd);
  // A formatter rewrites the paths it is given, and everything below them; given none, where it runs.
  const rewrites = (ops: string[]) => {
    deep = true;
    if (ops.length) targets.push(...ops);
    else here = cmd.cwd;
  };
  switch (prog) {
    case "tee": targets.push(...plain); break;
    case "tree": { const o = valueOf(/^-o$/); if (o !== undefined) targets.push(o); break; }
    case "xxd": if (args.some((a) => /^-[a-z]*r/.test(a)) || plain.length > 1) { if (plain[1]) targets.push(plain[1]); } break;
    case "base64": { const o = valueOf(/^(-o|--output)$/); if (o !== undefined && o !== "-") targets.push(o); break; }
    case "file": if (args.includes("-C")) { other = "file -C (compiles a magic file)"; here = cmd.cwd; } break;
    case "uniq": { const pos = args.filter((a, k) => !a.startsWith("-") && !/^-[fs]$/.test(args[k - 1] ?? "")); if (pos[1]) targets.push(pos[1]); break; }
    case "split": case "csplit": case "gsplit": other = `${prog} (writes pieces)`; here = cmd.cwd; break;
    case "vi": case "vim": case "nvim": case "ex": case "ed": case "red": case "emacs": case "nano": case "pico": case "mg": case "view":
      other = `${prog} (an editor)`;
      targets.push(...args.filter((a, k) => !/^[-+]/.test(a) && !/^(-c|--cmd|-S|-u|-i|-s|-W|-w|-T|--eval|-l)$/.test(args[k - 1] ?? "")));
      here = cmd.cwd;
      break;
    case "mv": case "cp": case "ln": case "install": case "rsync": case "scp": case "ditto":
      if (plain.length) targets.push(...(prog === "mv" ? plain : [plain[plain.length - 1]]));
      { const t = args.findIndex((a) => a === "-t" || a === "--target-directory"); if (t >= 0 && args[t + 1]) targets.push(args[t + 1]); }
      break;
    case "rm": case "rmdir": case "mkdir": case "touch": case "chmod": case "chown": case "truncate": case "unlink": case "shred":
      targets.push(...(prog === "chmod" || prog === "chown" ? plain.slice(1) : plain));
      break;
    case "dd": for (const a of args) if (a.startsWith("of=")) targets.push(a.slice(3)); break;
    case "sort": {
      const o = valueOf(/^(-o|--output)$/);
      if (o !== undefined) targets.push(o);
      // -ofile, or o inside a cluster (-uo file).
      for (let k = 0; k < args.length; k++) {
        const m = args[k].match(/^-([a-zA-Z]*?)o(.*)$/);
        if (!m || args[k].startsWith("--") || args[k] === "-o") continue;
        const v = m[2] || args[k + 1];
        if (v !== undefined) targets.push(v);
      }
      break;
    }
    case "sed": case "gsed": case "perl": case "ruby":
      if (prog === "sed" || prog === "gsed") {
        const s = sedWrites(cmd);
        targets.push(...s.files);
        if (s.other) other = s.other;
      }
      if (args.some((a) => (/^-[a-zA-Z]*i/.test(a) && !/^-[MImC]/.test(a)) || a.startsWith("--in-place"))) {
        // Positional arguments, minus the script: the value of -e/-f/-E, else the first one.
        const pos: string[] = [];
        let script = false;
        const takesScript = prog === "perl" || prog === "ruby" ? /^-[a-zA-Z]*[eE]$/ : /^(-[a-zA-Z]*[ef]|--expression|--file)$/;
        for (let k = 0; k < args.length; k++) {
          if (takesScript.test(args[k])) { script = true; k++; continue; }
          if (!args[k].startsWith("-")) pos.push(args[k]);
        }
        targets.push(...(script ? pos : pos.slice(1)));
        if (!targets.length) other = `${prog} -i`;
      }
      break;
    case "awk": case "gawk": case "mawk": case "nawk": {
      const program = args.includes("-f") ? "" : args.filter((a, k) => !a.startsWith("-") && !/^-[vF]$/.test(args[k - 1] ?? ""))[0] ?? "";
      if (/\b(print|printf)\b[^;}]*>|\bsystem\s*\(|\|\s*getline|\bprint(f)?\b[^;}]*\|/.test(program)) other = `${prog} writing files or running commands`;
      if (args.some((a) => a === "-i" || a === "--inplace" || a === "inplace")) other = `${prog} -i inplace`;
      if (args.some((a) => /^(-o|-d|-p|--pretty-print|--dump-variables|--profile)(=|$)/.test(a) || /^-[odp]./.test(a))) other = `${prog} writing a profile or dump file`;
      break;
    }
    case "curl":
      for (let k = 0; k < args.length; k++) {
        const a = args[k];
        if ((a === "-o" || a === "--output" || /^-[a-zA-Z]*o$/.test(a)) && args[k + 1]) targets.push(args[k + 1]);
        else if (/^(-c|--cookie-jar|-D|--dump-header|--trace|--trace-ascii|--stderr|--libcurl|--etag-save|--hsts|--alt-svc)$/.test(a) && args[k + 1] && args[k + 1] !== "-") targets.push(args[k + 1]);
        else if (a.startsWith("--output=")) targets.push(a.slice(9));
        if (a === "--remote-name" || a === "--remote-name-all" || a === "--output-dir" || /^-[a-zA-Z]*[OJ][a-zA-Z]*$/.test(a)) {
          other = "curl -O";
          here = cmd.cwd;
        }
      }
      break;
    case "wget": {
      other = "wget";
      here = dir(valueOf(/^(-P|--directory-prefix)$/));
      for (const re of [/^(-O|--output-document)$/, /^(-o|--output-file)$/, /^(-a|--append-output)$/]) {
        const o = valueOf(re);
        if (o !== undefined && o !== "-") targets.push(o);
      }
      for (const a of args) { const m = a.match(/^-[Ooa](.+)$/); if (m && m[1] !== "-") targets.push(m[1]); }
      break;
    }
    case "tar": case "bsdtar": case "gtar": {
      // The mode is the first word (xf, -xzf) or a flag of its own.
      const mode = (m: string) => (args[0] && !args[0].startsWith("--") && new RegExp(`^-?[a-zA-Z]*${m}[a-zA-Z]*$`).test(args[0])) ||
        args.some((a) => new RegExp(`^-[a-zA-Z]*${m}[a-zA-Z]*$`).test(a));
      if (mode("x") || args.some((a) => a === "--extract" || a === "--get")) { other = "tar -x"; here = dir(valueOf(/^(-C|--directory)$/)); deep = true; }
      else if (mode("c") || mode("r") || mode("u") || args.includes("--create")) {
        other = "tar -c";
        const f = valueOf(/^(-f|--file)$/) ?? (args[0] && !args[0].startsWith("--") && /f/.test(args[0]) ? args[1] : undefined) ??
          (() => { const k = args.findIndex((a) => /^-[a-zA-Z]*f$/.test(a)); return k >= 0 ? args[k + 1] : undefined; })();
        if (f && f !== "-") targets.push(f);
      }
      break;
    }
    case "unzip": other = "unzip"; here = dir(valueOf(/^-d$/)); deep = true; break;
    case "zip": case "gzip": case "xz": case "bzip2": other = prog; break;
    case "gunzip": case "unxz": case "bunzip2": targets.push(...plain); break;
    case "patch": other = "patch"; here = dir(valueOf(/^(-d|--directory)$/)); deep = true; break;
    case "find": {
      const act = args.find((a) => /^-(delete|fprint0?|fprintf|fls)$/.test(a));
      if (act) { other = `find ${act}`; here = cmd.cwd; deep = true; }
      break;
    }
    case "make": case "gmake": case "ninja":
      if (!args.some((a) => DRY_RUN.test(a))) { other = `${prog} (build recipes write files)`; here = dir(valueOf(/^(-C|--directory)$/)); deep = true; }
      break;
    case "cmake": if (args.some((a) => a === "--build" || a === "--install")) { other = "cmake --build"; here = cmd.cwd; deep = true; } break;
    case "black": case "isort": case "autopep8": case "yapf": case "rustfmt": case "prettier": case "eslint": case "biome":
      if (["black", "isort", "rustfmt"].includes(prog) ? !args.some((a) => DRY_RUN.test(a)) : args.some((a) => /^(-i|--in-place|-w)$/.test(a))) {
        other = `${prog} rewrites files`;
        rewrites(prog === "biome" ? plain.slice(1) : plain);
      }
      break;
    case "ruff":
      if ((plain[0] === "format" && !args.some((a) => DRY_RUN.test(a))) || args.includes("--fix")) { other = "ruff rewrites files"; rewrites(plain.slice(1)); }
      break;
    case "gofmt": case "goimports": if (args.includes("-w")) { other = `${prog} -w`; here = cmd.cwd; deep = true; } break;
    case "sqlite3": {
      const q = sqliteParts(cmd);
      if (q.archive) { other = "sqlite3 -A, which can extract an archive"; here = cmd.cwd; deep = true; break; }
      if ([...q.sql, ...cmd.code, ...cmd.stdin].some((x) => SQL_EXEC.test(x))) { other = "sqlite3 dot-commands that write files or run programs"; break; }
      if (q.init.some((x) => x === undefined)) { other = "sqlite3 -init with a file the guard cannot read"; break; }
      if (q.readonly) break;
      if (sqliteMayWrite(cmd, q)) {
        other = "sqlite3 that may write the database (use sqlite3 -readonly)";
        if (q.db) targets.push(q.db);
      }
      break;
    }
    case "gh": {
      // gh's subcommand words, without the repository a -R/--repo names.
      const words = args.filter((a, k) => !a.startsWith("-") && !/^(-R|--repo)$/.test(args[k - 1] ?? ""));
      if (words[0] === "api") {
        const method = valueOf(/^(-X|--method)$/) ?? args.find((a) => /^-X[A-Za-z]+$/.test(a))?.slice(2);
        if (args.some((a) => /^(-f|-F|--field|--raw-field|--input)$/.test(a)) || (method && method.toUpperCase() !== "GET")) other = "gh api writing";
      } else if (words[1] && GH_WRITES.test(words[1])) other = `gh ${words[0]} ${words[1]}`;
      break;
    }
    case "save-and-push.sh": case "ship.sh": other = `${prog} (a commit)`; break;
    case "opencode": if (plain[0] === "run") other = "opencode run (an agent that can write)"; break;
  }
  if (!other && args.some((a) => /^--(write|fix)(=|$)/.test(a))) { other = `${prog} ${args.find((a) => /^--(write|fix)/.test(a))}`; here = cmd.cwd; deep = true; }
  if (cmd.xargs && ["rm", "rmdir", "mv", "cp", "ln", "touch", "mkdir", "chmod", "chown", "truncate", "unlink", "shred", "tee", "dd"].includes(prog)) {
    other = `xargs ${prog}`;
    here = cmd.cwd;
    deep = true;
  }
  const g = gitParts(cmd);
  if (g) {
    const out = gitOutputs(g);
    targets.push(...out.files);
    if (out.dir !== undefined) { other = `git ${g.sub}`; here = out.dir === "" ? g.dir : wordPath(out.dir, g.dir, cmd.vars) ?? g.dir; }
    if (gitWrite(g)) other = `git ${g.sub}`;
  }
  if (PKG_WRITES[prog]) {
    const pk = pkgCall(prog, args);
    if (pk.sub && PKG_WRITES[prog].test(pk.sub)) {
      other = `${prog} ${pk.sub}`;
      // A JavaScript package manager writes node_modules and its lockfile where it runs.
      if (/^(npm|pnpm|yarn|bun)$/.test(prog)) here = dir(pk.dir);
    }
  }
  if (/^(npx|bunx|pnpx)$/.test(prog) && args.some((a) => /^(-w|--write|--fix)$/.test(a))) { other = `${prog} rewriting files`; here = cmd.cwd; deep = true; }
  if (/^python/.test(prog) && args.includes("-m") && /^(pip|tutorboard\.gitops)$/.test(args[args.indexOf("-m") + 1] ?? "")) {
    other = `python -m ${args[args.indexOf("-m") + 1]}`;
  }
  // python -m black board/ writes what black board/ writes.
  const it = INTERPRETERS.test(prog) ? interpreterOf(cmd) : undefined;
  if (it?.lang === "python" && it.module && !other) {
    const inner = writesOf({ ...cmd, words: [it.module, ...(it.moduleArgs ?? [])], redirs: [], code: [], opaque: false });
    targets.push(...inner.targets);
    if (inner.other) ({ other, here, deep = false } = inner);
  }
  for (const body of codeOf(cmd)) {
    const what = codeWrite(body);
    if (what) other = `code that writes files (${what})`;
  }
  if (cmd.opaque) { other = "code from a pipe the guard cannot read (write it to a file under /tmp and run that)"; here = cmd.cwd; deep = true; }
  return { targets: targets.filter((t) => t !== ""), other, here, deep };
}

// ---- the rules

type Call = { tool: string; args: any; session: string; directory: string };

function commandOf(call: Call): string | undefined {
  if (call.tool === "bash" || call.tool === "bg_shell" || call.tool === "monitor") return call.args?.command;
  return undefined;
}

function cwdOf(call: Call) {
  const w = call.args?.workdir;
  return w ? (isAbsolute(w) ? w : resolve(call.directory, w)) : call.directory;
}

function patchTargets(text: string) {
  return [...String(text ?? "").matchAll(/^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Move to: (.+)$/gm)].map((m) => (m[1] ?? m[2]).trim());
}

// Paths a file tool touches, and whether it reads them (content) or only lists names.
function filePaths(call: Call): { paths: string[]; content: boolean } {
  const a = call.args ?? {};
  const abs = (p: string) => wordPath(String(p), call.directory) ?? resolve(call.directory, String(p));
  switch (call.tool) {
    case "read": case "lsp": return { paths: a.filePath ? [abs(a.filePath)] : [], content: true };
    case "edit": case "write": case "multiedit": return { paths: a.filePath ? [abs(a.filePath)] : [], content: true };
    case "apply_patch": case "patch": return { paths: patchTargets(a.patchText ?? a.patch).map(abs), content: true };
    case "grep": {
      const base = a.path ? abs(a.path) : call.directory;
      return { paths: [base, ...(a.include ? [join(base, String(a.include))] : [])], content: true };
    }
    case "glob": {
      const base = a.path ? abs(a.path) : call.directory;
      return { paths: [base, ...(a.pattern ? [isAbsolute(a.pattern) ? a.pattern : join(base, String(a.pattern))] : [])], content: false };
    }
    case "list": return { paths: [a.path ? abs(a.path) : call.directory], content: false };
    default: return { paths: [], content: false };
  }
}

function credentialRule(call: Call, cmds: Cmd[] | undefined): string | undefined {
  if (cmds) {
    for (const c of cmds) {
      const what = credentialInCommand(c);
      if (what) return `Refused: this command ${what}. ${CRED_MOVE}`;
    }
    return undefined;
  }
  const { paths, content } = filePaths(call);
  for (const p of paths) {
    // Listing names reads no secret, so a name-only tool's glob is not expanded on disk.
    const what = credentialOf(p, content) ?? (content && call.tool === "grep" ? holdsCredential(p) : undefined);
    if (what) return `Refused: ${call.tool} on ${what}. ${CRED_MOVE}`;
  }
  if (call.tool === "grep" || call.tool === "glob") {
    const a = call.args ?? {};
    const root = paths[0];
    const env = root ? envFileUnder(root, call.tool === "grep" ? a.include : a.pattern) : undefined;
    if (env) return `Refused: ${call.tool} over ${root} would reach ${env}. ${CRED_MOVE} Search a narrower path, or exclude it with include.`;
  }
  return undefined;
}

// An env file a ripgrep search from root would reach, as the grep and glob tools run it
// (--hidden, .gitignore honoured inside a git work tree): a *.env or .env file below root that
// no git work tree ignores and whose name the pattern can match. In a work tree, git lists the
// candidates; elsewhere the tree is walked, and one too large to walk counts as reaching one.
function envFileUnder(root: string, pattern?: string): string | undefined {
  let st;
  try { st = statSync(root); } catch { return undefined; }
  if (!st.isDirectory()) return undefined;
  const names = pattern ? braceExpand(basename(String(pattern))).map(globRegex) : [];
  const fits = (n: string) => ENV_FILE.test(n) && n !== "env" && (!names.length || names.some((re) => re.test(n)));
  const ignored = (p: string) => {
    if (!repoRoot(dirname(p))) return false;
    try {
      execFileSync("git", ["-C", dirname(p), "check-ignore", "-q", "--", basename(p)], { timeout: 3000, stdio: "ignore" });
      return true;
    } catch {
      return false;
    }
  };
  if (repoRoot(root)) {
    const r = envFileInRepo(root, fits, { repos: 0 });
    if (r !== null) return r;
  }
  const stack = [root];
  let count = 0, checks = 0;
  while (stack.length) {
    const d = stack.pop()!;
    let entries;
    try { entries = readdirSync(d, { withFileTypes: true }); } catch { continue; }
    for (const e of entries) {
      if (++count > 20000) return `everything under ${root}, too many files to check for env files of keys`;
      const p = join(d, e.name);
      if (e.isDirectory()) { if (e.name !== ".git") stack.push(p); continue; }
      if (!fits(e.name)) continue;
      if (++checks > 20 || !ignored(p)) return `${p}, an env file of keys`;
    }
  }
  return undefined;
}

// envFileUnder in a git work tree: git lists the unignored *.env files below root, then each
// repository nested below it (an untracked one, or a checked-out submodule) is asked in turn,
// since ripgrep walks into it and honours only its ignore rules. Null when git fails.
function envFileInRepo(root: string, fits: (n: string) => boolean, seen: { repos: number }): string | undefined | null {
  const git = (...a: string[]) => execFileSync("git", ["-C", root, ...a], {
    encoding: "utf-8", timeout: 5000, stdio: ["ignore", "pipe", "ignore"], maxBuffer: 64 * 1024 * 1024,
  }).split("\0").filter(Boolean);
  let nested: string[];
  try {
    const hit = git("ls-files", "-co", "--exclude-standard", "-z", "--", "*.env").find((f) => fits(basename(f)));
    if (hit) return `${join(root, hit)}, an env file of keys`;
    nested = git("ls-files", "-o", "--exclude-standard", "-z").filter((f) => f.endsWith("/")).map((f) => f.slice(0, -1));
    nested.push(...git("ls-files", "-s", "-z").filter((l) => l.startsWith("160000 ")).map((l) => l.split("\t").slice(1).join("\t")));
  } catch {
    return null;
  }
  for (const n of nested) {
    const dir = join(root, n);
    if (!existsSync(join(dir, ".git"))) continue;
    if (++seen.repos > 50) return `everything under ${root}, too many nested repositories to check for env files of keys`;
    const r = envFileInRepo(dir, fits, seen);
    if (r === null) return `${dir}, a nested repository the guard could not check for env files of keys`;
    if (r) return r;
  }
  return undefined;
}

function readonlyRule(call: Call, g: Guard, cmds: Cmd[] | undefined): string | undefined {
  if (!g.readonly) return undefined;
  const why = `this agent is read-only (${g.readonly})`;
  const move = "Report the change you would make instead of making it.";
  if (READONLY_DENIED.has(call.tool)) return `Refused: ${why}, so it may not use ${call.tool}. ${move}`;
  if (call.tool === "task") {
    const sub = String(call.args?.subagent_type ?? "");
    if (!READONLY_AGENTS.has(agentName(sub))) return `Refused: ${why}; it may start only read-only subagents (explore, reviewer, verifier), not "${sub}". ${move}`;
  }
  for (const c of cmds ?? []) {
    const { targets, other } = writesOf(c);
    if (other) return `Refused: ${why}, and this command runs ${other}. ${move}`;
    for (const t of targets) {
      for (const p of globPathsOf(t, c)) {
        if (!p || !isTempPath(p)) return `Refused: ${why}, and this command writes ${t}. Only scratch files under /tmp are allowed. ${move}`;
      }
    }
    const not = readonlyBlocked(c);
    if (not) return `Refused: ${why}, and this command ${not}. It may run read commands, git's read subcommands and tests (python3 -m unittest, pytest, a file under test/). ${move}`;
  }
  return undefined;
}

// What a read-only agent may run: an allowlist, since a program the guard does not know can
// write. Writes through allowed programs (redirection, tee, cp, sed -i) are judged by writesOf.
const RO_PROGRAMS = new Set(("cat head tail less more bat wc ls stat file du df which type whereis echo printf true false test [ [[ pwd " +
  "realpath readlink basename dirname cut tr sort uniq grep egrep fgrep zgrep rg ag ack diff cmp comm jq column nl od xxd hexdump " +
  "strings date id whoami uname hostname sw_vers ps pgrep sleep tree mdls mdfind shasum md5 sha256sum sha1sum cksum base64 fold fmt " +
  "rev tac paste join expand unexpand seq expr bc cal locale cd pushd popd export unset set shift read local declare typeset exit " +
  "return : wait getopts for case in esac select sed gsed awk gawk mawk nawk find git tee mkdir touch cp mv rm rmdir mktemp env " +
  "printenv command hash tar unzip zcat plutil defaults launchctl brew mise python python3 node ruby perl pytest bash sh zsh curl " +
  "sqlite3 make otool nm lipo lsof uptime vm_stat iconv black ruff isort flake8 pyflakes shellcheck prettier eslint gh").split(" "));
const RO_ASSIGN = /^(GIT_\w+|PAGER|\w*EDITOR|LESS\w*|BASH_ENV|ENV|LD_\w+|DYLD_\w+|NODE_OPTIONS|PERL5OPT|PERL5LIB|RUBYOPT|RUBYLIB|PYTHONSTARTUP|PYTHONPATH|PROMPT_COMMAND|SHELLOPTS|BASHOPTS|PS4|IFS|MANPAGER|BROWSER)=/;
const GIT_READS = new Set(("status log show diff grep blame rev-parse rev-list ls-files ls-tree ls-remote describe shortlog reflog " +
  "cat-file check-ignore check-attr for-each-ref show-ref merge-base name-rev whatchanged help version var count-objects range-diff " +
  "diff-tree diff-index diff-files cherry show-branch verify-commit verify-tag annotate branch tag config remote stash worktree " +
  "notes submodule apply").split(" "));
const TEST_FILE = /(^|\/)(tests?|spec)\/|(^|\/)test_[^\/]*$|_test\.[a-z]+$|\.test\.[a-z]+$/;

// A test a read-only agent runs must not come from /tmp, the one place it can write.
function testFromScratch(c: Cmd): boolean {
  if (isTempPath(c.cwd)) return true;
  return c.words.slice(1).some((a) => !a.startsWith("-") && /[\/.]/.test(a) && (() => { const p = wordPath(a.replace(/^[\w-]+=/, ""), c.cwd, c.vars); return !p || isTempPath(p); })());
}

function readonlyBlocked(c: Cmd): string | undefined {
  const risky = c.assigns.find((a) => RO_ASSIGN.test(a));
  if (risky) return `sets ${risky.split("=")[0]}, which makes a program run another`;
  if (!c.words.length) return undefined;
  const w0 = c.words[0];
  if (/[$`]/.test(w0)) return `runs ${w0}, a command name the guard cannot resolve`;
  const prog = basename(w0);
  if (w0.includes("/")) {
    if (TEST_FILE.test(w0)) return testFromScratch(c) ? `runs ${w0} from /tmp, where this agent can write` : undefined;
    if (!/^\/(usr\/(local\/)?|opt\/homebrew\/)?s?bin\/[^\/]+$/.test(w0)) return `runs ${w0}, a script (only test files run for a read-only agent)`;
  }
  const args = c.words.slice(1);
  const pos = args.filter((a) => !a.startsWith("-"));
  const first = pos[0] ?? "";
  if (/^(export|declare|typeset|local)$/.test(prog)) {
    const bad = args.find((a) => RO_ASSIGN.test(a));
    return bad ? `sets ${bad.split("=")[0]}, which makes a program run another` : undefined;
  }
  if (!RO_PROGRAMS.has(prog)) return `runs ${prog}, which is not a read command`;
  const notRead = (what: string) => `runs ${what}, which is not a read command`;
  switch (prog) {
    case "git": {
      const g = gitParts(c);
      if (!g) return undefined;
      if (c.words.slice(1, c.words.indexOf(g.sub)).some((a) => /^(-c|--config-env|--exec-path|-p|--paginate)/.test(a))) return notRead("git with -c or a pager");
      const risky0 = gitRisky(g);
      if (risky0) return notRead(`git ${g.sub} ${risky0}, which writes a file or runs a program`);
      if (!GIT_READS.has(g.sub) || gitWrite(g)) return notRead(`git ${g.sub}`);
      const risky = gitRisky(g) ?? (g.args.some((a) => /^-[a-zA-Z]*O/.test(a)) ? "-O" : undefined);
      if (risky) return notRead(`git ${g.sub} ${risky}, which writes a file or runs a program`);
      if (g.sub === "config" && g.args.some((a) => /^(-e|--edit)$/.test(a))) return notRead("git config --edit");
      if (g.sub === "stash" && !["list", "show"].includes(g.args.filter((a) => !a.startsWith("-"))[0] ?? "")) return notRead("git stash");
      return undefined;
    }
    case "sort": return args.some((a) => /^--compress-program/.test(a)) ? notRead("sort --compress-program") : undefined;
    case "find": {
      const act = args.find((a) => /^-(delete|exec|execdir|ok|okdir|fprint0?|fprintf|fls)$/.test(a));
      return act ? `runs find ${act}, which writes or runs a program (list with find, then read with grep -r or xargs grep)` : undefined;
    }
    case "rg": case "ag": return args.some((a) => /^--pre(=|$)|^--pre-glob/.test(a)) ? notRead(`${prog} --pre (runs a program)`) : undefined;
    case "tar": return /^-?[a-zA-Z]*t/.test(args[0] ?? "") || args.some((a) => /^(-[a-zA-Z]*t[a-zA-Z]*|--list)$/.test(a)) ? undefined : notRead("tar without -t");
    case "unzip": return args.some((a) => /^-[a-zA-Z]*[ltpvZ]/.test(a)) ? undefined : notRead("unzip without -l");
    case "plutil": return ["-p", "-lint", "-help", "-type"].includes(args[0] ?? "") && !args.includes("-o") ? undefined : notRead("plutil that converts or edits");
    case "defaults": return ["read", "read-type", "domains", "find", "help"].includes(first) ? undefined : notRead(`defaults ${first}`);
    case "launchctl": return ["list", "print", "blame", "print-disabled", "print-cache", "help", "version", "managerpid", "manageruid", "managername", "error", "hostinfo"].includes(first) ? undefined : notRead(`launchctl ${first}`);
    case "brew": return ["list", "ls", "info", "deps", "outdated", "config", "search", "leaves", "uses", "desc", "commands", "tap-info", "home"].includes(first) || args.every((a) => /^--(prefix|cellar|repository|version|env)$/.test(a)) ? undefined : notRead(`brew ${first}`);
    case "mise": return ["ls", "list", "current", "which", "where", "version", "doctor", "ls-remote", "settings"].includes(first) || args.every((a) => /^(--version|-v)$/.test(a)) ? undefined : notRead(`mise ${first}`);
    case "make": return args.some((a) => DRY_RUN.test(a)) ? undefined : notRead("make without -n");
    case "env": case "printenv": case "command": case "hash": return undefined;
    case "mktemp": return pos.every((a) => isTempPath(wordPath(a, c.cwd, c.vars) ?? "/x")) ? undefined : notRead("mktemp outside /tmp");
    case "curl":
      if (args.some((a) => /^(-[a-zA-Z]*[dFTK]|--data[\w-]*|--form[\w-]*|--json|--upload-file|--config)(=|$)/.test(a))) return notRead("curl sending data");
      { const m = valueOfArgs(args, /^(-X|--request)$/) ?? args.find((a) => /^-X[A-Za-z]+$/.test(a))?.slice(2);
        if (m && !/^(GET|HEAD|OPTIONS)$/i.test(m)) return notRead(`curl -X ${m}`); }
      return undefined;
    case "sqlite3": return args.includes("-readonly") || !cmd_hasWriteSql(c) ? undefined : notRead("sqlite3 without -readonly");
    case "awk": case "gawk": case "mawk": case "nawk":
      if (args.some((a, k) => a === "-f" || /^--file/.test(a) || /^-[a-zA-Z]*f$/.test(a))) return notRead(`${prog} -f (a program the guard cannot read)`);
      if (/@load|ENVIRON\[|\bsystem\b|\|/.test(args.find((a, k) => !a.startsWith("-") && !/^-[vF]$/.test(args[k - 1] ?? "")) ?? "")) return notRead(`${prog} that runs a command`);
      return undefined;
    case "black": case "isort": return args.some((a) => /^(--check|--diff)$/.test(a)) ? undefined : notRead(`${prog} without --check`);
    case "ruff": return first === "check" && !args.includes("--fix") ? undefined : first === "format" && args.some((a) => /^(--check|--diff)$/.test(a)) ? undefined : notRead(`ruff ${first}`);
    case "prettier": return args.some((a) => /^(--check|-c|--list-different|-l)$/.test(a)) ? undefined : notRead("prettier without --check");
    case "eslint": return args.some((a) => /^--fix/.test(a)) ? notRead("eslint --fix") : undefined;
    case "gh": return ["pr", "issue", "repo", "api", "run", "release", "search", "status", "workflow", "label"].includes(first) ? undefined : notRead(`gh ${first}`);
    case "bash": case "sh": case "zsh": {
      if (args.some((a) => /^-[a-zA-Z]*c[a-zA-Z]*$/.test(a))) return undefined;
      if (args.some((a) => /^-[a-zA-Z]*n[a-zA-Z]*$/.test(a))) return undefined;
      const script = args.find((x, k) => !x.startsWith("-") && !x.startsWith("+") && !/^[-+][oO]$/.test(args[k - 1] ?? ""));
      if (script) {
        if (!TEST_FILE.test(script)) return `runs ${script}, a script (only test files run for a read-only agent)`;
        return testFromScratch(c) ? `runs ${script} from /tmp, where this agent can write` : undefined;
      }
      return c.opaque ? notRead(`${prog} reading a script from a pipe`) : undefined;
    }
    case "python": case "python3": case "node": case "ruby": case "perl": return interpreterBlocked(c, prog);
    case "pytest": return testFromScratch(c) || args.some((a) => /^(-p|--rootdir|--confcutdir|-c|--basetemp)$/.test(a)) ? notRead("pytest from /tmp or with a plugin") : undefined;
  }
  return undefined;
}

function valueOfArgs(args: string[], re: RegExp): string | undefined {
  for (let k = 0; k < args.length; k++) {
    if (re.test(args[k]) && args[k + 1] !== undefined) return args[k + 1];
    const m = args[k].match(/^(--[\w-]+)=(.*)$/);
    if (m && re.test(m[1])) return m[2];
  }
  return undefined;
}

// sqlite3's arguments: the database, the SQL it runs (its -cmd values and the words after the
// database), the text of its -init files (undefined when unreadable), -readonly, and -A.
function sqliteParts(c: Cmd): { db?: string; sql: string[]; init: Array<string | undefined>; readonly: boolean; archive: boolean } {
  const args = c.words.slice(1);
  const pos: string[] = [], sql: string[] = [], init: Array<string | undefined> = [];
  let readonly = false, archive = false;
  for (let k = 0; k < args.length; k++) {
    const a = args[k], o = a.replace(/^--/, "-");
    if (o === "-cmd") { if (args[k + 1] !== undefined) sql.push(args[++k]); continue; }
    if (o === "-init") { const p = args[k + 1] !== undefined ? wordPath(args[++k], c.cwd, c.vars) : undefined; init.push(p ? fileText(p, c) : undefined); continue; }
    if (o === "-readonly") { readonly = true; continue; }
    if (/^-(A|archive)/.test(o)) { archive = true; continue; }
    if (/^-(separator|nullvalue|newline|vfs|maxsize|mmap|pagecache|lookaside|heap|escape)$/.test(o)) { k++; continue; }
    if (a.startsWith("-")) continue;
    pos.push(a);
  }
  return { db: pos[0], sql: [...sql, ...pos.slice(1), ...(init.filter((x) => x !== undefined) as string[])], init, readonly, archive };
}

// SQL piped in from echo, printf or a cat here-document is read like SQL on the command line.
function sqliteMayWrite(c: Cmd, q = sqliteParts(c)): boolean {
  return [...q.sql, ...c.stdin].some((x) => SQL_WRITE.test(x) || SQL_EXEC.test(x)) || c.code.length > 0 || !!c.feeder ||
    c.redirs.some((r) => r.op === "<" || r.op === "<<<") || (q.sql.length === 0 && !c.stdin.length);
}

function cmd_hasWriteSql(c: Cmd): boolean {
  const q = sqliteParts(c);
  return q.archive || q.init.some((x) => x === undefined) || sqliteMayWrite(c, q);
}

// An interpreter run by a read-only agent: tests, syntax checks and inline code that neither
// writes nor runs anything.
function interpreterBlocked(c: Cmd, prog: string): string | undefined {
  const args = c.words.slice(1);
  if (args.length && args.every((a) => /^(-V|--version|-v|-h|--help)$/.test(a))) return undefined;
  if (prog === "perl" || prog === "ruby") {
    if (args.some((a) => /^-[a-zA-Z]*i/.test(a))) return `runs ${prog} -i, which edits files`;
    if (args.some((a) => /^-M/.test(a) && !/^-M(strict|warnings|utf8|List::Util|Data::Dumper|JSON::PP)\b/.test(a))) return `runs ${prog} with a module the guard does not know`;
  }
  const it = interpreterOf(c);
  const lang = it.lang;
  if (args.some((a) => /^(-r|--require|--import|--loader|--experimental-loader)(=|$)/.test(a))) return `runs ${prog} with a preloaded module`;
  const runsTests = it.module !== undefined || (lang === "node" && args.includes("--test")) || it.script !== undefined;
  if (runsTests && testFromScratch(c)) return `runs ${prog} on code from /tmp, where this agent can write`;
  if (lang === "python" && it.module !== undefined) {
    const mod = it.module;
    if (mod === "unittest" || mod === "pytest" || mod === "pydoc" || mod === "tabnanny") return undefined;
    const after = args.slice(args.indexOf(mod) + 1);
    if (mod === "json.tool" && after.filter((a) => !a.startsWith("-")).length <= 1) return undefined;
    return `runs python -m ${mod}, which is not a test or a read`;
  }
  if (lang === "node" && (args.includes("--test") || it.check) && !it.code.length) return undefined;
  if ((lang === "ruby" || lang === "perl") && it.check && !it.code.length) return undefined;
  const script = it.script;
  if (script !== undefined) return TEST_FILE.test(script) ? undefined : `runs ${script}, a script (only test files run for a read-only agent)`;
  if (c.opaque) return `runs ${prog} on code from a pipe the guard cannot read`;
  for (const body of codeOf(c)) {
    const risk = codeRisk(body, lang);
    if (risk) return `runs ${prog} code that ${risk}`;
  }
  return undefined;
}

// Whether inline code could write, run a program or hide what it calls. Stricter than
// codeWrite: a read-only agent's code may read and print, nothing else.
function codeRisk(code: string, lang: string): string | undefined {
  const text = code.replace(/\b(sys\.(stdout|stderr)(\.buffer)?|process\.(stdout|stderr)|\$stdout|\$stderr|STDOUT|STDERR)\.write\b/g, "OUT");
  const hidden = /\bopen\b(?!\s*\()|\b(builtins|eval|exec|(?<!re\.)compile|getattr|setattr|delattr|globals|vars|__import__|__builtins__|__dict__|__class__|__subclasses__|importlib|ctypes|cffi|runpy|code\.interact|fromCharCode|atob|b64decode|chr|codecs\.decode|Function|Reflect|Proxy|vm|process\.binding|process\.dlopen|require\s*\(\s*[^'"\s)]|import\s*\(|send|__send__|public_send|instance_eval|class_eval|binding|syscall|do\s+FILE|require\s+\$)\b|\\x[0-9a-fA-F]{2}|\\u[0-9a-fA-F]{4}|\[[^\]]*['"]\s*\+|\+\s*['"][^\]]*\]/;
  const h = text.match(hidden);
  if (h) return `uses ${h[0].trim()}, which can hide what it calls`;
  const writes = /\b\w*([Ww]rite|[Uu]nlink|[Rr]mdir|[Mm]kdir|[Rr]ename|[Ss]ymlink|[Tt]runcate|[Cc]hmod|[Cc]hown|[Uu]time|[Rr]mtree|[Cc]opy[Ff]ile|[Cc]opytree|[Mm]akedirs|[Rr]emovedirs)\w*|\bos\.replace\b|\bFile::|\b(remove|touch|copy2|copyfileobj|link|rm|rmSync|cp|cpSync|appendFile\w*|createWriteStream|open\w*Sync|dump|savez?|to_csv|to_json|to_parquet|savefig|extractall|extract|make_archive|unpack_archive|urlretrieve|FileUtils|syswrite)\s*\(|\bshutil\b|\bFileUtils\b|\bFile\.(write|delete|unlink|new|open|binwrite)|\bIO\.(write|binwrite|sysopen)|\bDir\.(mkdir|rmdir|unlink|delete)|\bunlink\b|\brename\b|\bmkdir\b|\brmdir\b|\butime\b|\bsymlink\b|\bchmod\b|\bchown\b|\btruncate\b/;
  const w = text.match(writes);
  if (w) return `calls ${w[0].trim()}, which can write`;
  const runs = /\b(subprocess|system|popen|spawn\w*|fork|exec\w*|execSync|child_process|pty|os\.kill|kill|Open3|PTY|Process|Bun|Deno|socket|sqlite3|dbm|shelve|webbrowser|multiprocessing|worker_threads|qx)\b|%x[({]|`|do\s+shell\s+script|\bopen\s*\(\s*[^,)]*\|/;
  const r = text.match(runs);
  if (r && !(lang === "node" && r[0] === "`" && !/\b(exec|spawn)/.test(text))) return `uses ${r[0].trim()}, which can run a program or write`;
  // open() reads unless a mode says otherwise.
  for (const o of text.matchAll(/(\.)?\b(open|fopen|openSync|ZipFile|TarFile)\s*\(/g)) {
    const inner = callArgs(text, o.index! + o[0].length);
    const parts = inner.split(",").map((x) => x.trim());
    const isMethod = o[1] === ".";
    const mode = isMethod && !/^['"][^'"]*\//.test(parts[0] ?? "") ? parts[0] : parts[1];
    if (parts.length <= (isMethod ? 0 : 1) || mode === undefined || mode === "") continue;
    if (/^(mode\s*=\s*)?[bfru]*['"][rbtU]*['"]$/.test(mode) || /^(encoding|newline|errors|buffering)\s*=/.test(mode)) continue;
    if (lang === "perl" && /^['"]?<['"]?$/.test(mode)) continue;
    return `opens a file with mode ${mode}`;
  }
  if (lang === "perl" && /\bopen\s*\(?\s*(my\s+)?\$?\w+\s*,\s*['"]\s*[+>|]/.test(text)) return "opens a file for writing";
  return undefined;
}

// The text between a call's parentheses, starting just after the opening one.
function callArgs(text: string, start: number): string {
  let depth = 1, q: string | null = null;
  for (let j = start; j < text.length; j++) {
    const ch = text[j];
    if (q) { if (ch === "\\") j++; else if (ch === q) q = null; continue; }
    if (ch === "'" || ch === '"') q = ch;
    else if (ch === "(" || ch === "[" || ch === "{") depth++;
    else if ((ch === ")" || ch === "]" || ch === "}") && --depth === 0) return text.slice(start, j);
  }
  return text.slice(start);
}

// The files a patch changes, resolved against dir; undefined when the patch cannot be read.
function patchFiles(file: string | undefined, dir: string, vars: Vars): string[] | undefined {
  const p = file && wordPath(file, dir, vars);
  if (!p) return undefined;
  try {
    if (statSync(p).size > 8 * 1024 * 1024) return undefined;
    const text = readFileSync(p, "utf-8");
    const names = [...text.matchAll(/^(?:\+\+\+|---) (?:[ab]\/)?(\S+)|^diff --git a\/(\S+) b\/(\S+)/gm)]
      .flatMap((m) => [m[1], m[2], m[3]]).filter((n) => n && n !== "/dev/null");
    return [...patchTargets(text), ...names].map((n) => resolve(dir, n));
  } catch {
    return undefined;
  }
}

// A git command run in the main checkout that rewrites board/ files: what it does, else undefined.
// merge, pull, commit and push are the documented way main changes (board/README.md).
function gitBoardWrite(c: Cmd, covers: (p: string) => boolean): string | undefined {
  const g = gitParts(c);
  if (!g || !underC(g.dir, atlasMain())) return undefined;
  const a = g.args;
  const dd = a.indexOf("--");
  const after = dd >= 0 ? a.slice(dd + 1) : [];
  const before = dd >= 0 ? a.slice(0, dd) : a;
  const pos = before.filter((x, k) => !x.startsWith("-") && !/^(-s|--source|-m|-b|-B|-c|-C)$/.test(before[k - 1] ?? ""));
  const touches = (paths: string[]) => paths.some((x) => pathsOf(x, { ...c, cwd: g.dir }).some((p) => !p || covers(p)));
  const has = (re: RegExp) => a.some((x) => re.test(x));
  const what = `git ${g.sub} ${a.join(" ")}`.trim();
  switch (g.sub) {
    case "checkout": case "switch": {
      if (has(/^(-f|--force|--discard-changes|-m|--merge|--overwrite-ignore)$/) || has(/^-[a-zA-Z]*f[a-zA-Z]*$/)) return what;
      const paths = [...after, ...(g.sub === "checkout" ? pos.filter((x) => existsSync(wordPath(x, g.dir, c.vars) ?? "\0")) : [])];
      if (paths.length) return touches(paths) ? what : undefined;
      if (has(/^(-b|-B|-c|-C|--orphan|--detach|--create|--force-create)$/)) return what;
      const target = pos[0];
      return target && !["main", "master"].includes(target) ? what : undefined;
    }
    case "restore":
      if (has(/^(--staged|-S)$/) && !has(/^(--worktree|-W)$/)) return undefined;
      return !(pos.length + after.length) || touches([...pos, ...after]) ? what : undefined;
    case "reset": return has(/^--(hard|merge|keep)$/) ? what : undefined;
    case "stash": {
      const action = pos[0] ?? "push";
      if (["list", "show", "drop", "clear", "create", "store"].includes(action)) return undefined;
      const specs = [...after, ...(action === "push" ? pos.slice(1) : [])];
      return ["push", "save"].includes(action) && specs.length && !touches(specs) ? undefined : what;
    }
    case "clean":
      if (has(/^(-n|--dry-run)$|^-[a-zA-Z]*n/)) return undefined;
      return (pos.length + after.length ? touches([...pos, ...after]) : covers(g.dir)) ? what : undefined;
    case "rm": case "mv": return !has(/^--cached$/) && touches([...pos, ...after]) ? what : undefined;
    case "apply": {
      if (has(/^--(check|stat|numstat|summary|cached)$/) && !has(/^--index$/)) return undefined;
      const files = pos.length ? pos : [c.redirs.find((r) => r.op === "<")?.target ?? ""];
      const changed = files.map((f) => patchFiles(f, g.dir, c.vars));
      return changed.some((f) => !f || f.some(covers)) ? what : undefined;
    }
    case "am": case "cherry-pick": case "revert": case "rebase":
      return has(/^--(abort|quit)$/) ? undefined : what;
    case "read-tree": return has(/^(-u|--reset)$/) || has(/^--prefix/) ? what : undefined;
    case "checkout-index": case "worktree": case "sparse-checkout": case "filter-branch": case "replay":
      return g.sub === "worktree" ? (["add", "remove", "move"].includes(pos[0] ?? "") && touches(pos.slice(1)) ? what : undefined) : what;
  }
  return undefined;
}

function worktreeRule(call: Call, cmds: Cmd[] | undefined): string | undefined {
  const board = join(atlasMain(), "board");
  const inBoard = (p: string) => underC(p, board);
  // p is board/, inside it, or a directory that holds it.
  const covers = (p: string) => inBoard(p) || underC(board, p);
  const move = "Make a worktree under ~/Developer/Atlas-wt/<item> (worktree_create), change it there, then merge into main.";
  const refuse = (p: string) => `Refused: ${p} is in the main checkout's board/, which serves the owner's iPad live. ${move}`;
  if (EDIT_TOOLS.has(call.tool)) {
    for (const p of filePaths(call).paths) if (inBoard(p)) return refuse(p);
    return undefined;
  }
  // From the main checkout, a write whose target the guard cannot resolve may land in board/.
  const fromMain = underC(call.directory, atlasMain());
  const unknown = (t: string) => `Refused: the command writes ${t}, a path the guard cannot resolve, from the main checkout. Name the path, or ${move.charAt(0).toLowerCase() + move.slice(1)}`;
  for (const c of cmds ?? []) {
    const git = gitBoardWrite(c, covers);
    if (git) return `Refused: ${git} in the main checkout rewrites board/ files, which serve the owner's iPad live. ${move}`;
    const { targets, other, here, deep } = writesOf(c);
    const prog = basename(c.words[0] ?? "");
    const sweeping = ["rm", "rmdir", "shred", "mv", "chmod", "chown", "chflags", "rsync", "xattr"].includes(prog) || deep;
    for (const t of targets) {
      for (const p of globPathsOf(t, c)) {
        if (!p) { if (fromMain) return unknown(t); continue; }
        if (sweeping ? covers(p) : inBoard(p)) return refuse(p);
      }
    }
    if (other?.startsWith("code")) {
      // Literals shaped like paths, and any literal naming an entry that exists where it runs.
      // Paths built from the home directory are judged as the literal path they make.
      const homed = codeOf(c).map(homeExprs);
      const bodies = homed.map((h) => h.code);
      // Code that removes or moves a whole tree reaches board/ from any path holding it, as rm -r does.
      const sweepCode = bodies.some((b) => SWEEP_CODE.test(b));
      for (const p of homed.flatMap((h) => h.paths)) if (sweepCode ? covers(p) : inBoard(p)) return refuse(p);
      const fileWrite = bodies.some((b) => CODE_WRITES.some(([re]) => re !== SUBPROCESS && re.test(b)));
      // A literal base that holds board/ and a literal naming the rest, however the code joins
      // them ('/'.join, % or .format, an alias of join, a variable between): judged as joined.
      // A leading %s or {} placeholder is the base's place.
      if (fileWrite) {
        const strs = bodies.flatMap((b) => [...b.matchAll(/(['"\x60])((?:\\.|(?!\1).)*)\1/g)].map((m) => m[2]))
          .filter((x) => x && x.length < 400 && !/\s/.test(x));
        const bases = strs.filter((x) => /^(\/|~\/)/.test(x)).map((x) => resolve(expandTilde(x))).filter((p) => covers(p) && !inBoard(p));
        for (const base of bases) {
          for (const x of strs) {
            const p = join(base, x.replace(/^(%[sr]|\{\w*\})/, "").replace(/^\/+/, ""));
            if (!x.startsWith("~") && inBoard(p)) return refuse(p);
          }
        }
      }
      // A path built from the home directory whose end is not a literal may reach board/.
      const open = homed.flatMap((h) => h.open).filter(covers);
      if (fileWrite && open.length && (fromMain || underC(c.cwd, atlasMain()))) return unknown(`${open[0]}/...`);
      const lits = [...new Set([...bodies.flatMap(codeLiterals), ...bodies.flatMap((b) => [...b.matchAll(/(['"])((?:\\.|(?!\1).)*)\1/g)]
        .map((m) => m[2]).filter((l) => l && l.length < 400 && !/\s/.test(l) && existsSync(resolve(c.cwd, expandTilde(l)))))])];
      for (const lit of lits) {
        // A literal naming the working directory itself ('.') is not a file the code writes,
        // unless the code removes or moves whole trees.
        for (const p of globPathsOf(lit, c)) {
          if (p && (GLOB_CHARS.test(lit) || sweepCode ? covers(p) : inBoard(p)) && (sweepCode || canon(p) !== canon(c.cwd))) return refuse(p);
        }
      }
      // Code run inside board/ that writes files it does not name elsewhere writes board/.
      // A path the code computes (concatenation, format, join) cannot be read from its literals.
      const computed = open.length > 0 || bodies.some((b) => /['"`]\s*\+|\+\s*['"`]|\bf['"]|\.format\s*\(|%\s*[(\w]|\bjoin(path)?\s*\(|\/\s*['"]|\$\{|\blistdir\b|\bglob\b|\bwalk\b|\breaddir|\bscandir\b|\biterdir\b/.test(b));
      const elsewhere = !computed && lits.some((l) => pathsOf(l, c).some((p) => p && !covers(p)));
      if ((fileWrite || c.opaque) && !elsewhere && covers(c.cwd)) return refuse(c.cwd);
    }
    if (prog === "patch") {
      const file = c.words.slice(1).find((x, k, a) => /^(-i|--input)$/.test(a[k - 1] ?? "")) ?? c.words.find((x) => x.startsWith("--input="))?.slice(8) ??
        c.redirs.find((r) => r.op === "<")?.target;
      const files = patchFiles(file, here ?? c.cwd, c.vars);
      if (files ? files.some(covers) : covers(here ?? c.cwd)) return `Refused: patch ${files ? "changes" : "may change"} files in the main checkout's board/. ${move}`;
      continue;
    }
    if (prog === "find" && other) {
      for (const r of operandsOf(c).roots) for (const p of globPathsOf(r, c)) if (!p || covers(p)) return refuse(p ?? r);
      continue;
    }
    if (!here || !other) continue;
    const spots = c.scope ? c.scope.flatMap((r) => pathsOf(r, c)) : [here];
    if (spots.some((p) => !p || (deep ? covers(p) : inBoard(p)))) {
      return `Refused: ${other} here writes into the main checkout's board/, which serves the owner's iPad live. ${move}`;
    }
  }
  return undefined;
}

// The repository root above dir (a .git file or directory), if any.
function repoRoot(dir: string): string | undefined {
  let d = dir;
  for (let k = 0; k < 64; k++) {
    if (existsSync(join(d, ".git"))) return d;
    const p = dirname(d);
    if (p === d) return undefined;
    d = p;
  }
  return undefined;
}

const COMMIT_VALUE = /^(-m|-F|-C|-c|-t|--message|--file|--author|--date|--cleanup|--fixup|--squash|--template|--reuse-message|--reedit-message|--trailer|--chmod)$/;

// A pathspec that names the whole repository: ".", "*", "**", ":/", only exclusions (":!x"),
// a pattern with no literal name in it, a path at or above the root, or one the guard cannot
// resolve (a substitution or variable).
function namesEverything(specs: string[], c: Cmd, dir: string): boolean {
  if (!specs.length) return false;
  const root = repoRoot(dir) ?? dir;
  let includes = 0;
  for (const raw of specs) {
    let spec = raw, top = false, exclude = false;
    const long = spec.match(/^:\(([^)]*)\)/);
    if (long) {
      const magic = long[1].split(",").map((x) => x.trim());
      top = magic.includes("top");
      exclude = magic.includes("exclude");
      spec = spec.slice(long[0].length);
    } else if (spec.startsWith(":")) {
      const short = spec.match(/^:([\/!^]*):?/)!;
      top = short[1].includes("/");
      exclude = /[!^]/.test(short[1]);
      spec = spec.slice(short[0].length);
    }
    if (exclude) continue;
    includes++;
    const literal = spec.replace(/\[[^\]]*\]|[*?]/g, "").replace(/[\/.]/g, "");
    if (!literal) return true;
    if (GLOB_CHARS.test(spec)) continue;
    for (const p of pathsOf(spec, { ...c, cwd: top ? root : dir })) if (p === undefined || underC(root, p)) return true;
  }
  return includes === 0;
}

const NAMED = "Name the paths: git add <path>... (in Atlas, bash board/scripts/save-and-push.sh \"message\" -- <path>...).";

function stagingRule(cmds: Cmd[] | undefined): string | undefined {
  for (const c of cmds ?? []) {
    const g = gitParts(c);
    if (!g) continue;
    if (g.args.some((a) => a.startsWith("--pathspec-from-file"))) {
      return `Refused: git ${g.sub} --pathspec-from-file stages paths the guard cannot see. ${NAMED}`;
    }
    if (g.sub === "add" || g.sub === "stage") {
      const pos = g.args.filter((a, k) => !a.startsWith("-") && !/^--chmod$/.test(g.args[k - 1] ?? ""));
      const all = g.args.some((a) => /^--a(l|ll)?$/.test(a) || a === "--no-ignore-removal" || (/^-[a-zA-Z]*A/.test(a) && !a.startsWith("--")));
      const update = g.args.some((a) => /^--u(p(d(a(te?)?)?)?)?$/.test(a) || (/^-[a-zA-Z]*u/.test(a) && !a.startsWith("--")));
      if (all || namesEverything(pos, c, g.dir) || (update && !pos.length) || (c.xargs && !c.stdin.length && !c.scope)) {
        return `Refused: git ${g.sub} ${g.args.join(" ")} stages everything, including the owner's uncommitted work. ${NAMED}`;
      }
    }
    if (g.sub === "commit") {
      const all = g.args.some((a) => a === "--all" || (/^-[a-zA-Z]+$/.test(a) && a.includes("a")));
      const specs: string[] = [];
      for (let k = 0; k < g.args.length; k++) {
        const a = g.args[k];
        if (COMMIT_VALUE.test(a)) { k++; continue; }
        if (/^-[a-zA-Z]*[mFCct]$/.test(a)) { k++; continue; }
        if (!a.startsWith("-")) specs.push(a);
      }
      if (all || namesEverything(specs, c, g.dir)) {
        return `Refused: git commit ${g.args.join(" ")} commits every modified file. Name the paths: git add <path>..., then commit without -a (in Atlas, bash board/scripts/save-and-push.sh "message" -- <path>...).`;
      }
    }
  }
  return undefined;
}

// A session's parent and creation time: as the plugin recorded them when it started the
// session, else from the client, asked once per process (an error reads as no parent and an
// unknown time).
async function sessionInfo(id: string, client: any, directory: string): Promise<Guard> {
  const g = guardOf(id);
  if (g.parent === undefined || g.created === undefined) {
    let data: any;
    try { data = (await client?.session?.get?.({ path: { id }, query: { directory } }))?.data; } catch {}
    if (g.parent === undefined) g.parent = data?.parentID ?? null;
    const c = data?.time?.created;
    if (g.created === undefined && typeof c === "number") g.created = c;
    guards.set(id, g);
  }
  return g;
}

// The session, then its parents: a subagent may not commit over its orchestrator's failed verify.
async function lineage(session: string, client: any, directory: string): Promise<string[]> {
  const chain = [session];
  let id = session;
  for (let k = 0; k < 5; k++) {
    const parent = (await sessionInfo(id, client, directory)).parent;
    if (!parent) break;
    chain.push(parent);
    id = parent;
  }
  return chain;
}

// A verdict as text a person can act on: its area, its reason, and its defects, from the start.
const HEAD_KEYS = ["area", "name", "label", "check", "requirement", "item", "title", "id"];
const WHY_KEYS = ["reason", "summary", "why", "explanation", "message", "notes", "detail", "details"];
const LIST_KEYS = ["defects", "failures", "findings", "issues", "problems", "errors", "failed", "blockers"];
const ITEM_KEYS = ["what", "summary", "reason", "description", "issue", "problem", "message", "detail", "title"];

function verdictText(v: any, max = 400) {
  const cut = (s: string) => {
    const t = s.replace(/\s+/g, " ").trim();
    return t.length <= max ? t : t.slice(0, max - 1) + "…";
  };
  if (v === null || typeof v !== "object") return cut(String(v));
  const str = (x: any) => (typeof x === "string" && x.trim() ? x.trim() : undefined);
  const head = HEAD_KEYS.map((k) => str(v[k])).find(Boolean);
  const why = WHY_KEYS.map((k) => str(v[k])).find(Boolean);
  const item = (x: any) => {
    if (typeof x === "string") return x;
    if (!x || typeof x !== "object") return JSON.stringify(x);
    const text = ITEM_KEYS.map((k) => str(x[k])).find(Boolean) ?? JSON.stringify(x);
    const sev = str(x.severity) ? `[${x.severity}] ` : "";
    return `${sev}${str(x.where) ? `${x.where}: ` : ""}${text}`;
  };
  let list: string | undefined;
  for (const k of LIST_KEYS) {
    const l = v[k];
    if (Array.isArray(l) && l.length) {
      const items = l.map(item);
      list = items.length > 1 ? items.map((t, i) => `(${i + 1}) ${t}`).join(" ") : items[0];
      break;
    }
    if (str(l) && !why) { list = str(l); break; }
  }
  const parts = [head && `${head}:`, why, list].filter(Boolean) as string[];
  if (!why && !list) {
    const { verdict, ...rest } = v;
    parts.push(JSON.stringify(rest));
  }
  return cut(parts.join(" "));
}

const SHIP_GIT = new Set(["commit", "merge", "pull", "cherry-pick", "am", "revert", "rebase"]);

// What in a command ships work: a commit, a merge, or an agent run outside this session.
function shipsOf(c: Cmd): string | undefined {
  const g = gitParts(c);
  if (g && SHIP_GIT.has(g.sub) && !g.args.some((a) => a === "--abort" || a === "--quit")) return `git ${g.sub}`;
  if (g) {
    // A merge by another name: a branch moved onto other work, or work published.
    const a = g.args, pos = a.filter((x) => !x.startsWith("-"));
    const has = (re: RegExp) => a.some((x) => re.test(x));
    if (g.sub === "push" && !has(/^(-n|--dry-run)$/)) return "git push";
    if (g.sub === "fetch" && pos.slice(1).some((r) => /:/.test(r) && !/:refs\/(remotes|tags)\//.test(r) && !/:$/.test(r))) return "git fetch into a branch";
    if (g.sub === "branch" && has(/^(-f|--force|-C|-M)$|^-[a-zA-Z]*[fCM]/)) return "git branch -f (moves a branch)";
    if ((g.sub === "checkout" && has(/^-B$/)) || (g.sub === "switch" && has(/^(-C|--force-create)$/))) return `git ${g.sub} ${g.sub === "checkout" ? "-B" : "-C"} (moves a branch)`;
    if (g.sub === "update-ref" || g.sub === "commit-tree" || (g.sub === "symbolic-ref" && pos.length > 1)) return `git ${g.sub}`;
    if (g.sub === "reset" && has(/^--(hard|soft|mixed|keep|merge)$/) && pos[0] && !/^(HEAD|@)$/.test(pos[0]) && !a.includes("--")) return "git reset to another commit";
  }
  const prog = basename(c.words[0] ?? "");
  if (prog === "save-and-push.sh" || prog === "ship.sh") return prog;
  if (prog === "board" && c.words[1] === "push") return "board push (a commit)";
  if (/^python/.test(prog) && c.words.includes("tutorboard.gitops")) return "tutorboard.gitops";
  if (prog === "gh" && c.words[1] === "pr" && c.words[2] === "merge") return "gh pr merge";
  if (prog === "gh" && c.words[1] === "api" && c.words.some((x) => /\/(merges?|git\/refs)\b/.test(x)) &&
    c.words.some((x) => /^(-X|--method)$|^-X[A-Za-z]|^(-f|-F|--field|--raw-field|--input)$/.test(x))) return "gh api (a merge or ref update)";
  if (prog === "opencode" && c.words.includes("run")) return "opencode run (a new session outside this one)";
  if (SHELLS.has(prog) && c.words.slice(1).some((x) => /(^|\/)(save-and-push|ship)\.sh$/.test(x))) return "save-and-push.sh";
  for (const body of codeOf(c)) {
    if (SUBPROCESS.test(body) && /['"\s]git['"\s]/.test(body) && /['"\s](commit|merge|pull|cherry-pick|am|revert|rebase|push|update-ref|commit-tree)['"\s]/.test(body)) {
      return "code that runs git";
    }
  }
  if (c.opaque) return "code from a pipe the guard cannot read";
  return undefined;
}

// A command whose name is a variable or substitution the guard cannot resolve could be any
// program, so it is refused for every session.
function opaqueRule(cmds: Cmd[] | undefined): string | undefined {
  for (const c of cmds ?? []) {
    const w0 = c.words[0] !== undefined && /[$`]/.test(c.words[0]) ? c.words[0] : gitParts(c)?.sub;
    if (w0 !== undefined && /[$`]/.test(w0)) {
      return `Refused: the command name ${w0} is a variable or substitution the guard cannot resolve, so it cannot be checked. Write the program's name.`;
    }
  }
  return undefined;
}

async function commitGate(call: Call, cmds: Cmd[] | undefined, client: any): Promise<string | undefined> {
  const ships = (cmds ?? []).map(shipsOf).find(Boolean);
  if (!ships) return undefined;
  // A verifier subagent's reply still being read counts before the gate decides.
  await Promise.all([...settling.values()]);
  // In each session, a run holding a fail no later run has re-verified (holds) closes the gate,
  // and so does one in any session of the lineage: a subagent's own pass never lifts its
  // orchestrator's fail.
  const refuse = (last: Verdicts, where = "") => {
    const quoted = last.failed.slice(0, 2).map((f) => `"${clip1(f, 300)}"`).join("; ");
    const sub = last.run?.startsWith("@");
    const who = sub ? `The ${last.run}` : `Workflow run${last.run ? ` ${last.run}` : ""}`;
    const since = sub ? "no run started since has re-verified" : "no later round of its own verify_until_pass passed and no run started since has re-verified";
    return `Refused: ${ships} after a failed verify. ${who}${where} holds a fail that ${since}: ${quoted}. ` +
      `Fix it and run a fresh verify that passes, or put the failing verdict to the owner; only the owner saying "ship over it" lifts this.`;
  };
  const chain = await lineage(call.session, client, call.directory);
  for (const id of chain) {
    const last = standingFail(guardOf(id, true));
    if (last) return refuse(last);
  }
  // So does one in a descendant of the committing session or of an ancestor (a session whose
  // parent chain reaches it): a workflow a worker or task subagent ran holds the sessions above
  // it. Of the committing session's chain, the nearest session the descendant's chain reaches
  // (the meeting point) is held by it. The committing session is held with it when it is the
  // meeting point, or when the meeting point started the committing session's branch after the
  // fail arrived: a held session may not ship through a fresh subagent. A branch that existed
  // before the fail (a sibling working beside it) is not held. The owner's word lifts it in the
  // descendant, the meeting point or the committing session, and so does the newest-run rule
  // across the tree: a done run started after the fail arrived, in a session on the path from
  // the descendant (not included) through the meeting point to the committing session, decides
  // it (its own fail holds through the lineage loop above). A finished subagent cannot run again.
  const over = (s: string) => guardOf(s, true).override_at ?? 0;
  for (const id of sessionsWithVerdicts()) {
    if (chain.includes(id)) continue;
    const below = await lineage(id, client, call.directory);
    const k = chain.findIndex((s) => below.indexOf(s) > 0);
    if (k < 0) continue;
    const j = below.indexOf(chain[k]);
    const last = standingFail(guardOf(id, true), Math.max(over(call.session), over(chain[k])));
    if (!last) continue;
    const path = [...below.slice(1, j + 1), ...chain.slice(0, k)];
    if (path.some((s) => (guardOf(s, true).verdicts ?? []).some((r) => decides(r) && (r.start ?? r.at) >= last.at))) continue;
    if (k === 0) return refuse(last, ` in subagent session ${id}`);
    const branch = chain[k - 1];
    // An unknown creation time counts as after the fail.
    const created = (await sessionInfo(branch, client, call.directory)).created ?? Infinity;
    if (created < last.at) continue;
    return refuse(last, ` in session ${id} below ${chain[k]}, which started ${branch === call.session ? "this session" : `session ${branch}`} after that fail arrived,`);
  }
  return undefined;
}

// A session's newest run holding a fail no owner's word since has lifted.
function standingFail(g: Guard, override = 0): Verdicts | undefined {
  const all = g.verdicts ?? [], lift = Math.max(g.override_at ?? 0, override);
  let last: Verdicts | undefined;
  for (const v of all) if (holds(v, all) && lift <= v.at && (!last || v.at >= last.at)) last = v;
  return last;
}

// Every session with saved verify verdicts: those this process holds and those in guard/.
function sessionsWithVerdicts(): string[] {
  const ids = new Set<string>();
  for (const [id, g] of guards) if (g.verdicts?.length) ids.add(id);
  let files: string[] = [];
  try { files = readdirSync(GUARD_DIR).filter((f) => f.endsWith(".json")); } catch {}
  for (const f of files) {
    try {
      const j = JSON.parse(readFileSync(join(GUARD_DIR, f), "utf-8"));
      if (j?.verdicts?.length) ids.add(typeof j.id === "string" ? j.id : f.slice(0, -5));
    } catch {}
  }
  return [...ids];
}

const clip1 = (s: string, max: number) => (s.length <= max ? s : s.slice(0, max - 1) + "…");

// The owner's word to ship over a failed verify: a sentence that says "ship over it" and is
// neither a question nor a negation.
function ownerShipsOver(text: string) {
  for (const s of text.split(/(?<=[.!?;])\s+|\n+/)) {
    if (!/\bship (it )?over\b/i.test(s)) continue;
    const t = s.trim();
    // A quoted phrase is a mention (a prompt or doc naming the owner's words), not the owner's word.
    if (/["'\x60\u201c\u2018][^"'\x60\u201d\u2019]*\bship (it )?over\b[^"'\x60\u201d\u2019]*["'\x60\u201d\u2019]/i.test(t)) continue;
    if (/\?$/.test(t) || /^(should|shall|can|could|may|might|do|does|did|would|will|is|are|why|how|what|when)\b/i.test(t)) continue;
    if (/\b(not|never|no|nor|don'?t|doesn'?t|can'?t|cannot|won'?t|shouldn'?t|mustn'?t|wouldn'?t|isn'?t|stop|refuse|refuses|without|unless|until|before|if)\b|n't\b/i.test(t)) continue;
    return true;
  }
  return false;
}

// A shell call that posts a message into an opencode session could forge the owner's word.
const HTTP_CLIENTS = new Set(["curl", "wget", "http", "https", "xh"]);
const HTTP_POSTS = /(^|\s)(-[a-zA-Z]*X\s*|--request[=\s]*)(POST|PUT|PATCH)\b|(^|\s)(-[a-zA-Z]*[dF]|--data[\w-]*|--form|--json|--post-data|--post-file)(\s|=|$)|(^|\s)(POST|PUT|PATCH)(\s|$)/i;

function selfPromptRule(cmds: Cmd[] | undefined): string | undefined {
  for (const c of cmds ?? []) {
    const prog = basename(c.words[0] ?? "");
    if (prog === "opencode" && c.words.includes("run") && c.words.some((x) => /^(-s|--session|-c|--continue)(=|$)/.test(x))) {
      return "Refused: post to an existing session through agent_send, never with opencode run --session.";
    }
    const text = [...c.words, ...codeOf(c), ...c.stdin].join(" ");
    if (!/:4096\b/.test(text) || !/\/session\b/.test(text)) continue;
    // An HTTP client may read the session API; anything else that names it (code, nc) may not.
    if (!HTTP_CLIENTS.has(prog) || HTTP_POSTS.test(text)) {
      return "Refused: post to a session through agent_send or the workflow tools, and read one with session_read; " +
        "never send requests to the opencode server's session API from the shell.";
    }
  }
  return undefined;
}

// The repository's own working tree holding p (its .git is a directory), or undefined when p is
// in a linked worktree (.git is a file) or in no repository.
function primaryCheckout(p: string): string | undefined {
  let d = resolve(p);
  for (let k = 0; k < 64; k++) {
    try { return statSync(join(d, ".git")).isDirectory() ? d : undefined; } catch {}
    const up = dirname(d);
    if (up === d) return undefined;
    d = up;
  }
  return undefined;
}

// An /ultracode session, or a subagent or workflow agent it started (five parents up).
async function inUltracode(session: string, client: any, directory: string): Promise<boolean> {
  if (![...guards.values()].some((g) => g.ultracode)) return false;
  for (const id of await lineage(session, client, directory)) if (guardOf(id).ultracode) return true;
  return false;
}

// /ultracode, its subagents and its workflow agents write files only in a linked worktree:
// the checkout a session starts in may be serving the owner live.
async function ultracodeTreeRule(call: Call, cmds: Cmd[] | undefined, client: any): Promise<string | undefined> {
  if (!EDIT_TOOLS.has(call.tool) && !cmds?.length) return undefined;
  if (!(await inUltracode(call.session, client, call.directory))) return undefined;
  const refuse = (p: string, top: string) =>
    `Refused: ${p} is in ${top}, a repository's main checkout, and /ultracode builds only in a worktree. ` +
    "Make one with worktree_create (for Atlas, under ~/Developer/Atlas-wt/<item>), give every builder and fixer its path as cwd, " +
    "and merge it after the final verify passes.";
  const paths: string[] = [];
  if (EDIT_TOOLS.has(call.tool)) paths.push(...filePaths(call).paths);
  for (const c of cmds ?? []) for (const t of writesOf(c).targets) for (const p of globPathsOf(t, c)) if (p) paths.push(p);
  for (const p of paths) {
    const top = primaryCheckout(p);
    if (top) return refuse(p, top);
  }
  return undefined;
}

function readBudgetRule(call: Call, g: Guard): string | undefined {
  if (!g.ultracode || g.planned || !READ_TOOLS.has(call.tool)) return undefined;
  if ((g.reads ?? 0) >= READ_BUDGET) {
    return `Refused: plan first, the survey is a workflow phase. You have made ${g.reads} reads of your own in this /ultracode session; ` +
      `write the plan with todowrite (two steps or more), then map the code with a workflow survey of readonly agents.`;
  }
  return undefined;
}

// A todo list is a plan when it holds two steps or more.
const isPlan = (args: any) =>
  Array.isArray(args?.todos) && args.todos.filter((t: any) => String(t?.content ?? "").trim()).length >= 2;

// Every rule, in order; the first refusal wins. Allowed calls count toward the read budget.
async function guardCall(call: Call, client?: any, budget = true): Promise<string | undefined> {
  realCache.clear();
  const g = guardOf(call.session);
  const command = commandOf(call);
  let cmds: Cmd[] | undefined;
  if (command !== undefined) cmds = parseCommands(String(command), cwdOf(call));
  const reason = credentialRule(call, cmds) ?? opaqueRule(cmds) ?? readonlyRule(call, g, cmds) ?? worktreeRule(call, cmds) ??
    (await ultracodeTreeRule(call, cmds, client)) ?? stagingRule(cmds) ?? selfPromptRule(cmds) ?? (await commitGate(call, cmds, client)) ??
    (budget ? readBudgetRule(call, g) : undefined);
  if (reason) {
    log(`guard ${call.session} ${call.tool}: ${reason.slice(0, 160)}`);
    return reason;
  }
  if (!budget) return undefined;
  if (call.tool === "todowrite" && g.ultracode && !g.planned && isPlan(call.args)) {
    g.planned = true;
    saveGuard(call.session, g);
  } else if (g.ultracode && !g.planned && READ_TOOLS.has(call.tool)) {
    g.reads = (g.reads ?? 0) + 1;
    saveGuard(call.session, g);
  }
  return undefined;
}

// A guard that throws refuses: a call it cannot check does not run.
const GUARD_BROKE = (e: any) =>
  `Refused: the parity guard could not check this call (${String(e?.message ?? e).slice(0, 120)}). ` +
  "Rewrite it more plainly: one command per line, no unusual globs or quoting.";

// ---- verdicts

function isPass(v: any) {
  return /^(pass|passed)$/i.test(String(v?.verdict ?? "").trim());
}

// Objects carrying a `verdict` field, anywhere in a value. With errors=true, a parallel(settle)
// failure ({error}) counts as a failed verdict.
function collectVerdicts(value: any, errors = false, depth = 0, out: any[] = []): any[] {
  if (depth > 6 || value === null || typeof value !== "object") return out;
  if (Array.isArray(value)) {
    for (const v of value) collectVerdicts(v, errors, depth + 1, out);
    return out;
  }
  if ("verdict" in value) { out.push(value); return out; }
  const keys = Object.keys(value);
  if (errors && keys.length === 1 && keys[0] === "error") {
    out.push({ verdict: "fail", reason: `the verify agent did not finish: ${value.error}` });
    return out;
  }
  for (const k of keys) collectVerdicts(value[k], errors, depth + 1, out);
  return out;
}

// Verdicts the plugin made from a reply: read from prose, or the fail for a reply naming none.
const MADE = ((G as any).madeVerdicts ??= new WeakSet<object>()) as WeakSet<object>;
const made = (v: any) => (MADE.add(v), v);

// A read-only agent's verdicts. A text reply's verdict is its first non-blank line, which
// starts with PASS or FAIL (PASSED and FAILED too, any case, "Verdict:" before it allowed).
// Markdown around it is read through: heading and quote marks, `*`, `_` and backticks, and a
// first line that is only "Verdict" (a heading) hands over to the next non-blank line. The
// rest of the reply is its reason. With noneFails, a reply naming no verdict is one fail.
function replyVerdicts(result: any, noneFails = false): any[] {
  let out: any[] = [];
  if (typeof result === "string") {
    const lines = result.split("\n");
    const plain = (l: string) => l.replace(/[*_`]/g, "").replace(/^[\s#>]+/, "");
    let i = lines.findIndex((l) => plain(l).trim());
    if (i >= 0 && /^verdict\s*:?\s*$/i.test(plain(lines[i]).trim())) {
      const j = lines.findIndex((l, k) => k > i && plain(l).trim());
      if (j > 0) i = j;
    }
    const m = i < 0 ? null : plain(lines[i]).match(/^\s*(?:verdict\s*:\s*)?(pass|fail)(?:ed)?\b[\s:.\-–—]*(.*)$/i);
    if (m) {
      const rest = [m[2], ...lines.slice(i + 1)].join("\n").trim();
      out = [made({ verdict: m[1].toLowerCase(), reason: clip1(rest || `the verify agent replied ${m[1].toUpperCase()} with no reason`, 4000) })];
    }
  } else {
    out = collectVerdicts(result);
  }
  if (out.length || !noneFails) return out;
  const said = typeof result === "string" ? result : JSON.stringify(result) ?? String(result);
  return [made({
    verdict: "fail",
    reason: `the verify agent's reply named no verdict (no first line starting PASS or FAIL, no verdict field): ${clip1(said.replace(/\s+/g, " ").trim(), 300)}`,
  })];
}

// A verifier or reviewer subagent started outside a workflow (the task tool, agent_spawn,
// agent_send, an @ mention): each reply it finishes is one run in its parent's verdicts, started
// when it was prompted (chat.message) and done when read. Its verdict is read as replyVerdicts
// reads one with noneFails: a reply naming none, or a turn that ended in an error, is a fail.
// A workflow's own agents are judged by the workflow instead, and a session with no parent
// records nothing. Each settlement is held in `settling` until saved, so the gate waits for it.
const settling = ((G as any).verifySettling ??= new Map<string, Promise<void>>()) as Map<string, Promise<void>>;

function settleVerifier(id: string | undefined, client: any, directory: string): Promise<void> {
  if (!id) return Promise.resolve();
  const busy = settling.get(id);
  if (busy) return busy;
  const g = guardOf(id, true);
  const asked = g.asked_at;
  if (asked === undefined || g.workflow || !VERIFY_TYPES.has(agentName(g.agent))) return Promise.resolve();
  delete g.asked_at;
  saveGuard(id, g);
  const work = (async () => {
    try {
      const parent = (await sessionInfo(id, client, directory)).parent;
      if (!parent) return;
      const last = await lastAssistant(id, directory).catch(() => undefined);
      const err = last ? errorOf(last) : "no reply";
      const vs = err
        ? [{ verdict: "fail", reason: `the verify agent did not finish: ${err}` }]
        : replyVerdicts(textOf(last), true);
      const ledger = new VerdictLedger(parent, `@${agentName(g.agent)} subagent ${id}`, asked);
      ledger.add(vs);
      ledger.finish();
    } catch (e: any) {
      log(`verifier ${id} not settled: ${e?.message ?? e}`);
    } finally {
      settling.delete(id);
    }
  })();
  settling.set(id, work);
  return work;
}


// ---- instructions (AGENTS.md / CLAUDE.md)
//
// opencode 1.19.5 (Instruction.systemPaths) loads the first that exists of
// ~/.config/opencode/AGENTS.md and ~/.claude/CLAUDE.md, then takes the first of AGENTS.md,
// CLAUDE.md, CONTEXT.md with any match from the session directory up to the worktree and loads
// every match of that name. OPENCODE_DISABLE_CLAUDE_CODE (or _PROMPT), which ./env sets, drops
// both CLAUDE.md entries, so a repo with only a CLAUDE.md gets its nearest one from here.
// OPENCODE_DISABLE_PROJECT_CONFIG skips the walk, so then the nearest AGENTS.md, else CLAUDE.md.

const flagOn = (name: string) => /^(1|true)$/i.test(process.env[name] ?? "");

function nearest(directory: string, worktree: string | undefined, name: string): string | undefined {
  const stop = worktree && under(directory, worktree) ? worktree : directory;
  let d = directory;
  for (let k = 0; k < 64; k++) {
    const p = join(d, name);
    if (existsSync(p)) return p;
    if (d === stop || dirname(d) === d) break;
    d = dirname(d);
  }
  return undefined;
}

function missingInstructions(directory: string, worktree?: string): string | undefined {
  if (flagOn("OPENCODE_DISABLE_PROJECT_CONFIG")) return nearest(directory, worktree, "AGENTS.md") ?? nearest(directory, worktree, "CLAUDE.md");
  if (!(flagOn("OPENCODE_DISABLE_CLAUDE_CODE") || flagOn("OPENCODE_DISABLE_CLAUDE_CODE_PROMPT"))) return undefined;
  if (nearest(directory, worktree, "AGENTS.md")) return undefined;
  return nearest(directory, worktree, "CLAUDE.md");
}

// ---- reading a child session that opencode cannot list in full
//
// opencode 1.19.5 answers 400 ("Expected OutputFormatJsonSchema") to any message listing that
// reaches a user message sent with a json_schema format, and so does its single-message read.
// The listing takes `limit` and a `before` cursor (base64url of {id, time}: messages older than
// that key), so the plugin reads around such a message without ever asking for it. A message id
// is "msg_" + 12 hex digits of (ms * 4096 + counter), low 48 bits, then 14 random characters.
// The plugin names each schema prompt's message itself and records it, and the event hook
// records every message of those sessions, so a read knows how many messages lie between two
// schema prompts and pages exactly that far.

type Track = { bad: Array<{ id: string; time: number }>; msgs: Array<{ id: string; time: number; role: string; parent?: string }> };
const TRACK_DIR = join(STATE_DIR, "schema");
const tracks = ((G as any).tracks ??= new Map<string, Track>()) as Map<string, Track>;
const ID_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
let idClock = { ms: 0, n: 0 };

// A message id as opencode makes one, ascending with time.
function messageId(): { id: string; time: number } {
  const now = Date.now();
  if (now !== idClock.ms) idClock = { ms: now, n: 0 };
  idClock.n++;
  const hex = ((BigInt(now) * 4096n + BigInt(idClock.n)) & 0xffffffffffffn).toString(16).padStart(12, "0");
  return { id: `msg_${hex}${[...randomBytes(14)].map((b) => ID_CHARS[b % 62]).join("")}`, time: now };
}

// The millisecond an id was made, given a time near it (its 48 bits hold ms modulo 2^36).
function idTime(id: string, near: number): number | undefined {
  const m = /^msg_([0-9a-f]{12})/.exec(id);
  if (!m) return undefined;
  const low = Math.floor(parseInt(m[1], 16) / 4096);
  const span = 2 ** 36;
  return low + Math.round((near - low) / span) * span;
}

const cursorBefore = (id: string, time: number) => Buffer.from(JSON.stringify({ id, time })).toString("base64url");
const trackFile = (session: string) => join(TRACK_DIR, `${session.replace(/[^A-Za-z0-9_-]/g, "_")}.json`);

// A session's record. A miss is remembered for 30 s, because every message.updated event of
// every session asks; a read passes fresh=true.
const untracked = ((G as any).untracked ??= new Map<string, number>()) as Map<string, number>;
function trackOf(session: string, fresh = false): Track | undefined {
  let t = tracks.get(session);
  if (!t) {
    if (!fresh && (untracked.get(session) ?? 0) > Date.now() - 30000) return undefined;
    try { t = JSON.parse(readFileSync(trackFile(session), "utf-8")) as Track; } catch {
      untracked.set(session, Date.now());
      if (untracked.size > 2000) untracked.delete(untracked.keys().next().value!);
      return undefined;
    }
    tracks.set(session, t);
  }
  return t;
}

function saveTrack(session: string, t: Track) {
  tracks.set(session, t);
  try {
    mkdirSync(TRACK_DIR, { recursive: true });
    const tmp = `${trackFile(session)}.${process.pid}.tmp`;
    writeFileSync(tmp, JSON.stringify(t));
    renameSync(tmp, trackFile(session));
  } catch (e: any) {
    log(`schema track for ${session} not saved: ${e?.message ?? e}`);
  }
}

function noteSchemaPrompt(session: string, id: string, time: number) {
  const t = trackOf(session, true) ?? { bad: [], msgs: [] };
  if (!t.bad.some((b) => b.id === id)) t.bad.push({ id, time });
  saveTrack(session, t);
}

// A message.updated event: every message of a tracked session is recorded once. Any user
// message there is a schema prompt (the plugin sent it), so it is one to page around.
function noteMessage(info: any) {
  const session = info?.sessionID, id = info?.id;
  if (!session || typeof id !== "string") return;
  const t = trackOf(session);
  if (!t || t.msgs.some((m) => m.id === id)) return;
  const time = Number(info.time?.created) || Date.now();
  t.msgs.push({ id, time, role: String(info.role ?? ""), parent: info.parentID });
  if (info.role === "user" && !t.bad.some((b) => b.id === id)) t.bad.push({ id, time: Math.min(time, idTime(id, time) ?? time) });
  saveTrack(session, t);
}

// The newest `want` messages of a session, oldest first, never asking for a schema prompt.
// stop ends the read early once a page holds a message it accepts. hidden counts the schema
// prompts left out. A session the plugin never sent a schema prompt to is read in one request;
// if that fails (a schema child from before tracking), the read pages one message at a time and
// steps over each prompt it meets, the parent of the oldest reply read so far.
async function readSession(client: any, id: string, directory: string, want: number, stop?: (m: any) => boolean) {
  const page = async (limit: number, before?: string) => {
    const r = await client.session.messages({ path: { id }, query: { directory, limit, ...(before ? { before } : {}) } });
    if (r?.error || !Array.isArray(r?.data)) return { error: JSON.stringify(r?.error ?? "no data").slice(0, 300) };
    return { data: r.data as any[], next: r.response?.headers?.get?.("x-next-cursor") as string | undefined };
  };
  const t = trackOf(id, true);
  // A workflow agent's session may hold schema prompts, unless its journal entry says it had none.
  const entry = t ? undefined : journalEntry(id);
  if (!t && (entry === undefined || entry.schema === false)) {
    const r = await page(want);
    if (!r.error) return { msgs: r.data!, hidden: 0 };
  }
  const bad = new Map<string, number>((t?.bad ?? []).map((b) => [b.id, b.time]));
  const known = (t?.msgs ?? []).filter((m) => !bad.has(m.id)).map((m) => m.id);
  const out: any[] = [];
  let before: string | undefined, below: string | undefined, hidden = 0, error: string | undefined;
  const isBelow = (x: string) => below === undefined || x < below;
  for (let k = 0; k < 200 && out.length < want; k++) {
    let limit = t ? want - out.length : 1;
    if (t) {
      const next = [...bad.keys()].filter(isBelow).sort().pop();
      if (next !== undefined) {
        const between = known.filter((m) => isBelow(m) && m > next).length;
        if (!between) { hidden++; before = cursorBefore(next, bad.get(next)!); below = next; continue; }
        limit = Math.min(limit, between);
      }
    }
    const r = await page(limit, before);
    if (r.error) {
      const oldest = out[out.length - 1]?.info;
      const parent = oldest?.parentID;
      if (t || !parent || parent === below) { error = r.error; break; }
      hidden++;
      before = cursorBefore(parent, idTime(parent, Number(oldest.time?.created) || Date.now()) ?? 0);
      below = parent;
      continue;
    }
    const got = r.data!;
    if (!got.length) break;
    for (let i = got.length - 1; i >= 0; i--) out.push(got[i]);
    const oldest = got[0].info ?? {};
    below = oldest.id;
    before = r.next ?? cursorBefore(oldest.id, Number(oldest.time?.created) || 0);
    if (stop && got.some(stop)) break;
    if (got.length < limit) break;
  }
  return { msgs: out.reverse(), hidden, error };
}

// The journal entry of a workflow agent's session, from the newest 50 runs.
function journalEntry(session: string): any {
  try {
    const root = join(STATE_DIR, "workflows");
    const runs = readdirSync(root).map((r) => join(root, r, "journal.jsonl")).filter(existsSync)
      .sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs).slice(0, 50);
    for (const j of runs) {
      for (const line of readFileSync(j, "utf-8").split("\n")) {
        if (!line.includes(session)) continue;
        try { const e = JSON.parse(line); if (e.session === session) return e; } catch {}
      }
    }
  } catch {}
  return undefined;
}

const promptFromJournals = (session: string): string | undefined => journalEntry(session)?.prompt || undefined;

function renderMessage(m: any) {
  const info = m.info ?? {};
  const head = info.role === "user" ? "## user" : `## assistant${info.agent ? ` @${info.agent}` : ""}${info.modelID ? ` (${info.modelID})` : ""}`;
  const body: string[] = [];
  for (const p of m.parts ?? []) {
    if (p.type === "text" && !p.synthetic) body.push(p.text);
    else if (p.type === "tool") {
      const st = p.state ?? {};
      const out = st.status === "error" ? `ERROR ${st.error}` : st.output ?? "";
      body.push(`-> ${p.tool} ${clip(JSON.stringify(st.input ?? {}), 300)}\n   ${clip(String(out), 600).replace(/\n/g, "\n   ")}`);
    }
  }
  if (info.structured !== undefined) body.push(`structured: ${clip(JSON.stringify(info.structured), 4000)}`);
  if (info.error) body.push(`error: ${errorOf(m)}`);
  return `${head}\n${body.join("\n")}`;
}

// ---------------------------------------------------------------- the plugin

const LONG_WORK =
  "You run inside a persistent server, so you can wait, watch and work indefinitely. " +
  "Never say you cannot monitor, wait or run something for a long time: use monitor, wakeup, cron_create, " +
  "bg_shell, task with background=true, or workflow, then end your turn; results arrive as new messages.";

// capabilities.md sits beside plugins/ in the config dir. It reaches the model through this
// plugin, not through `instructions`, so `opencode --pure` (no plugins, so none of these tools)
// is never told it has them. It is re-read whenever its mtime changes, because the server runs
// for days and an installed edit must reach the next turn without a restart.
const CAPABILITIES_FILE = join(dirname(fileURLToPath(import.meta.url)), "..", "capabilities.md");
let capabilitiesCache = { mtime: -1, text: LONG_WORK };
function capabilities(): string {
  try {
    const mtime = statSync(CAPABILITIES_FILE).mtimeMs;
    if (mtime !== capabilitiesCache.mtime) {
      capabilitiesCache = { mtime, text: readFileSync(CAPABILITIES_FILE, "utf-8").trim() };
    }
    return capabilitiesCache.text;
  } catch {
    return LONG_WORK;
  }
}

// The browser MCP, added through the config hook for the same reason.
const BROWSER_MCP = { type: "local", command: ["npx", "-y", "@playwright/mcp@latest"], enabled: true };

// The bash tool runs under the config's `shell`, else $SHELL (zsh on a Mac). The config hook
// sets bash, so the model's bash habits hold, and shell.env points BASH_ENV at a file that turns
// pipefail on for the tool's shell only (it unsets BASH_ENV, so scripts it runs are untouched).
// PARITY_BASH=0 leaves the shell alone; a zsh shell gets a note in the tool description instead.
const BASH_ENV_FILE = join(STATE_DIR, "bash_env");
const BASH_ENV_TEXT = "# Written by the parity plugin: the bash tool's shell runs with pipefail.\nset -o pipefail\nunset BASH_ENV\n";
let toolShell = basename(process.env.SHELL || "zsh");

function bashEnvFile() {
  try {
    if (!existsSync(BASH_ENV_FILE) || readFileSync(BASH_ENV_FILE, "utf-8") !== BASH_ENV_TEXT) {
      mkdirSync(STATE_DIR, { recursive: true });
      writeFileSync(BASH_ENV_FILE, BASH_ENV_TEXT);
    }
    return BASH_ENV_FILE;
  } catch {
    return undefined;
  }
}

const BASH_NOTE =
  "Commands run in bash (not zsh) with pipefail on, so a pipeline fails when any stage fails and ${PIPESTATUS[@]} works. " +
  "Take a repository root from `git rev-parse --show-toplevel`; never count dirnames.";
const ZSH_NOTE =
  "The shell is zsh, not bash: quote globs (an unmatched glob is an error), PIPESTATUS does not exist, and pipefail is off. " +
  "When a pipeline's exit status matters, run it as bash -o pipefail -c '...'.";

function liveJobs(session?: string) {
  return allJobs().filter((j) => !session || j.session === session || j.parent === session);
}

function describe(j: Job) {
  switch (j.kind) {
    case "wakeup": return `wakeup ${j.id} at ${new Date(j.fire_at).toLocaleString()}: ${j.reason ?? j.prompt.slice(0, 80)}`;
    case "cron": return `cron ${j.id} "${j.cron}" next ${new Date(j.next_at).toLocaleString()}: ${j.prompt.slice(0, 80)}`;
    case "shell": return `bg_shell ${j.id} pid ${j.pid}: ${j.command.slice(0, 100)}`;
    case "monitor": return `monitor ${j.id} pid ${j.pid}: ${j.description}`;
    case "agent": return `agent ${j.id} (${j.agent_name ?? "general"}): ${j.description}`;
    case "workflow": return `workflow ${j.id} started ${new Date(j.started_at).toLocaleString()}`;
    default: return `${j.kind} ${j.id}`;
  }
}

// Once per process: claim the server role, adopt orphaned jobs, then keep jobs.json in sync.
function boot() {
  if (G.loaded) return;
  G.loaded = true;
  try {
    if (PRIMARY) {
      mkdirSync(STATE_DIR, { recursive: true });
      writeFileSync(PRIMARY_FILE, JSON.stringify(ME));
    }
    adoptOrphans();
  } catch (e: any) {
    log(`boot failed: ${e?.message ?? e}`);
  }
  log(`pid ${ME.pid} (${COMMAND ?? "tui"}${PRIMARY ? ", server" : ""}) owns ${G.jobs.size} jobs`);
  const t = setInterval(() => {
    try {
      save();
      adoptOrphans();
    } catch (e: any) {
      log(`sync failed: ${e?.message ?? e}`);
    }
  }, SYNC_MS);
  t.unref?.();
}

function rearm(j: Job) {
  try {
    switch (j.kind) {
      case "wakeup": return armWakeup(j);
      case "cron": return armCron(j);
      case "shell": return watchShell(j);
      case "monitor":
        if (j.pid && pidAlive(j.pid)) killGroup(j.pid);
        if (j.deadline && !j.persistent && j.deadline < Date.now()) {
          dropJob(j.id);
          deliver(j, tag("monitor", { id: j.id, description: j.description, event: "timed_out" },
            "The server was down when this monitor's deadline passed."));
          return;
        }
        return startMonitor(j, true);
      case "agent":
        // Its owner died, and the child's run ended with it. Report what it left.
        j.started_at = 0;
        return trackAgent(j);
      case "workflow":
        if (G.runs.has(j.id)) return;
        dropJob(j.id);
        deliver(j, tag("workflow", { id: j.id, state: "interrupted" },
          `The opencode server restarted while this workflow ran. Finished agent calls are journaled. ` +
          `Call workflow with resume_run_id="${j.id}" (same script) to continue without repeating them.`));
        return;
    }
  } catch (e: any) {
    log(`rearm ${j.id} failed: ${e?.message ?? e}`);
  }
}

export const ParityPlugin = async ({ client, directory, worktree }: any) => {
  G.clients.set(directory, client);
  boot();

  const base = (ctx: any) => ({ session: ctx.sessionID, directory: ctx.directory ?? directory, agent: ctx.agent });

  return {
    tool: {
      wakeup: tool({
        description:
          "Schedule a message back to this session after a delay, then END YOUR TURN. Use it to come back " +
          "later: check a build in 20 minutes, look again tomorrow, keep a /loop going. Any delay works " +
          "(seconds to weeks) and survives server restarts. The prompt you give is delivered to you verbatim " +
          "inside <wakeup> when it fires, so write it as an instruction to your future self with the context you will need.",
        args: {
          delay_seconds: z.number().min(1).describe("Seconds from now"),
          prompt: z.string().describe("Instruction delivered to you when it fires"),
          reason: z.string().optional().describe("One short line: why you are waking up"),
        },
        async execute(a, ctx) {
          const job: Job = { ...base(ctx), id: newId("w"), kind: "wakeup", fire_at: Date.now() + a.delay_seconds * 1000,
            prompt: a.prompt, reason: a.reason, created_at: Date.now() };
          putJob(job);
          armWakeup(job);
          return `Wakeup ${job.id} set for ${new Date(job.fire_at).toLocaleString()}. End your turn now; it arrives as a new message.`;
        },
      }),

      cron_create: tool({
        description:
          "Schedule a prompt on a cron schedule (5 fields, local time: minute hour day-of-month month day-of-week; " +
          "@hourly/@daily also work). Each fire delivers the prompt to this session inside <cron>. " +
          "recurring=false fires once at the next match. Durable jobs survive server restarts.",
        args: {
          cron: z.string(),
          prompt: z.string(),
          recurring: z.boolean().optional().describe("Default true"),
          durable: z.boolean().optional().describe("Default true: persist across server restarts"),
        },
        async execute(a, ctx) {
          const next = nextCron(a.cron).getTime();
          const job: Job = { ...base(ctx), id: newId("c"), kind: "cron", cron: a.cron, prompt: a.prompt,
            recurring: a.recurring ?? true, durable: a.durable ?? true, next_at: next, created_at: Date.now() };
          G.jobs.set(job.id, job);
          armCron(job);
          return `Cron ${job.id} "${a.cron}" next fires ${new Date(job.next_at).toLocaleString()}${job.recurring ? " and repeats" : " once"}.`;
        },
      }),

      cron_list: tool({
        description: "List scheduled cron jobs and wakeups.",
        args: {},
        async execute() {
          const js = allJobs().filter((j) => j.kind === "cron" || j.kind === "wakeup");
          return js.length ? js.map(describe).join("\n") : "No cron jobs or wakeups.";
        },
      }),

      cron_delete: tool({
        description: "Delete a cron job or a pending wakeup by id.",
        args: { id: z.string() },
        async execute(a) {
          const j = G.jobs.get(a.id) ?? foreignJobs().find((f) => f.id === a.id);
          if (!j || (j.kind !== "cron" && j.kind !== "wakeup")) return `No cron job or wakeup ${a.id}.`;
          if (G.jobs.has(a.id)) dropJob(a.id);
          else removeForeign(a.id);
          return `Deleted ${a.id}.`;
        },
      }),

      bg_shell: tool({
        description:
          "Run a shell command in the background with no time limit (builds, test suites, downloads, servers). " +
          "Returns at once with an id; output goes to a log file. When it exits you get a <bg_shell> message with " +
          "the exit code and the last lines, so END YOUR TURN instead of polling. Use bg_output to peek, bg_kill to stop.",
        args: {
          command: z.string(),
          workdir: z.string().optional().describe("Defaults to the project directory"),
          notify: z.boolean().optional().describe("Default true: message this session when it exits"),
        },
        async execute(a, ctx) {
          const id = newId("s");
          const { log: logPath, code } = shellPaths(id);
          const cwd = a.workdir ? resolve(ctx.directory ?? directory, a.workdir) : (ctx.directory ?? directory);
          const child = spawn("/bin/bash", ["-c", 'bash -c "$0" >"$1" 2>&1 </dev/null; echo $? >"$2"', a.command, logPath, code], {
            cwd, detached: true, stdio: "ignore", env: process.env,
          });
          child.unref();
          const job: Job = { ...base(ctx), id, kind: "shell", command: a.command, pid: child.pid, workdir: cwd,
            started_at: Date.now(), notify: a.notify ?? true };
          putJob(job);
          watchShell(job);
          return `Started ${id} (pid ${child.pid}). Log: ${logPath}. You will get a <bg_shell> message when it exits; end your turn or keep working.`;
        },
      }),

      bg_output: tool({
        description: "Show the last lines of a background shell's or monitor's output and whether it is still running.",
        args: { id: z.string(), tail: z.number().optional().describe("Lines, default 50") },
        async execute(a) {
          const mon = G.jobs.get(a.id) ?? foreignJobs().find((f) => f.id === a.id);
          if (mon?.kind === "monitor" && !G.jobs.has(a.id)) {
            return `${a.id}: monitor running in another opencode process (pid ${mon.owner?.pid}); its output reaches its session as <monitor> messages.`;
          }
          if (mon?.kind === "monitor") {
            const lines = ((G as any).recent?.[a.id] ?? []).slice(-(a.tail ?? 50));
            return `${a.id}: monitor running (pid ${mon.pid})\n${lines.join("\n") || "(no output yet)"}`;
          }
          const { log: logPath, code } = shellPaths(a.id);
          if (!existsSync(logPath)) return `No background shell ${a.id}.`;
          const state = existsSync(code) ? `exited with code ${readFileSync(code, "utf-8").trim()}` : "running";
          return `${a.id}: ${state}\n${tailFile(logPath, a.tail ?? 50) || "(no output yet)"}`;
        },
      }),

      bg_kill: tool({
        description: "Stop a background shell or a monitor by id.",
        args: { id: z.string() },
        async execute(a) {
          const local = G.jobs.get(a.id);
          const j = local ?? foreignJobs().find((f) => f.id === a.id);
          if (!j) return `No running job ${a.id}.`;
          if (j.kind === "monitor") {
            if (local) stopMonitor(a.id);
            else removeForeign(a.id);
            return `Stopped monitor ${a.id}.`;
          }
          if (j.kind !== "shell") return `${a.id} is a ${j.kind}; use the matching stop tool.`;
          killGroup(j.pid);
          return `Sent SIGTERM to ${a.id} (pid ${j.pid}); you will get its exit message.`;
        },
      }),

      monitor: tool({
        description:
          "Watch something for as long as it takes: minutes, hours or days. Runs a shell command in the background; " +
          "EVERY LINE IT PRINTS TO STDOUT becomes an event delivered to you as a <monitor> message (lines arriving " +
          "together are batched), and you get a final event with the exit code when it ends. Start it, then END YOUR TURN. " +
          "Examples: `tail -f build.log | grep --line-buffered -E 'error|done'`; a loop that checks a condition every " +
          "30 s and prints when it changes; `while kill -0 PID 2>/dev/null; do sleep 30; done; echo finished`. " +
          "Use grep --line-buffered in pipes. No timeout unless you set timeout_ms. It is restarted if the server restarts.",
        args: {
          command: z.string(),
          description: z.string().describe("Short label shown in every event"),
          timeout_ms: z.number().optional().describe("Kill after this long; omit for no limit"),
          persistent: z.boolean().optional().describe("Ignore timeout_ms and run until stopped or the command exits"),
          workdir: z.string().optional(),
        },
        async execute(a, ctx) {
          const job: Job = { ...base(ctx), id: newId("m"), kind: "monitor", command: a.command, description: a.description,
            persistent: a.persistent ?? false, deadline: a.timeout_ms ? Date.now() + a.timeout_ms : undefined,
            workdir: a.workdir ? resolve(ctx.directory ?? directory, a.workdir) : undefined };
          startMonitor(job);
          return `Monitor ${job.id} running (pid ${job.pid}). Events arrive as <monitor> messages. End your turn now; do not poll or sleep. Stop it with bg_kill ${job.id}.`;
        },
      }),

      agent_spawn: tool({
        description:
          "Start a subagent in its own child session with its own context. background=true (default) returns at once; " +
          "its final answer arrives later as a <task> message, so do not poll. worktree runs it in that directory " +
          "(create one with worktree_create for isolation). Prefer the built-in task tool for ordinary subagents; use this " +
          "for worktree isolation, a different model or variant, or when task cannot run in the background.",
        args: {
          prompt: z.string(),
          description: z.string().describe("3-5 words"),
          agent: z.string().optional().describe("Agent name, default general"),
          background: z.boolean().optional(),
          model: z.string().optional().describe("provider/model, e.g. deepseek/deepseek-v4-pro"),
          variant: z.string().optional(),
          worktree: z.string().optional().describe("Directory the child works in"),
        },
        async execute(a, ctx) {
          const dir = a.worktree ? resolve(ctx.directory ?? directory, a.worktree) : (ctx.directory ?? directory);
          const created = await client.session.create({
            body: { parentID: ctx.sessionID, title: `${a.description} (@${a.agent ?? "general"} subagent)` },
            query: { directory: dir },
          });
          const id = created?.data?.id;
          if (!id) return `Could not create the child session: ${JSON.stringify(created?.error ?? {})}`;
          guards.set(id, { ...guardOf(id), parent: ctx.sessionID, created: Date.now() });
          if (READONLY_AGENTS.has(agentName(a.agent))) markReadonly(id, `@${agentName(a.agent)}`);
          sentByUs(a.prompt);
          const body: any = { agent: a.agent ?? "general", parts: [{ type: "text", text: a.prompt }] };
          const model = splitModel(a.model);
          if (model) body.model = model;
          if (a.variant) body.variant = a.variant;
          const started = Date.now();
          const job: Job = { id, kind: "agent", session: id, directory: dir, parent: ctx.sessionID,
            parent_directory: ctx.directory ?? directory, agent: ctx.agent, agent_name: a.agent ?? "general",
            description: a.description, started_at: started, round: 1 };
          if (a.background === false) {
            await client.session.promptAsync({ path: { id }, query: { directory: dir }, body });
            await waitIdle(id, dir, started, ctx.abort);
            const last = await lastAssistant(id, dir);
            const err = errorOf(last);
            return `<task id="${id}" state="${err ? "error" : "completed"}">\n${clip(err ? `${err}\n${textOf(last)}` : textOf(last), 30000)}\n</task>`;
          }
          trackAgent(job);
          await client.session.promptAsync({ path: { id }, query: { directory: dir }, body });
          return `Agent ${id} started in the background. Its answer arrives as a <task id="${id}"> message. Do not poll; continue or end your turn.`;
        },
      }),

      agent_send: tool({
        description: "Send another message to a subagent (from agent_spawn, task, or fork) by its session id. Its next reply comes back as a <task> message.",
        args: { id: z.string(), message: z.string() },
        async execute(a, ctx) {
          // Tracking moves to this process; the old owner drops its copy on its next sync.
          const prev = G.jobs.get(a.id) ?? removeForeign(a.id);
          const dir = prev?.directory ?? ctx.directory ?? directory;
          const job: Job = prev ?? { id: a.id, kind: "agent", session: a.id, directory: dir, parent: ctx.sessionID,
            parent_directory: ctx.directory ?? directory, agent: ctx.agent, description: "follow-up", round: 0 };
          job.round = (job.round ?? 0) + 1;
          job.started_at = Date.now();
          if (!prev || !G.jobs.has(a.id)) { delete job.owner; trackAgent(job); } else save();
          sentByUs(a.message);
          const r = await client.session.promptAsync({ path: { id: a.id }, query: { directory: dir }, body: { parts: [{ type: "text", text: a.message }] } });
          if (r?.response?.status >= 400) { dropJob(a.id); return `Could not reach ${a.id}: HTTP ${r.response.status}`; }
          return `Sent. The reply arrives as a <task id="${a.id}"> message.`;
        },
      }),

      agent_stop: tool({
        description: "Stop a running subagent, fork, or workflow by id.",
        args: { id: z.string() },
        async execute(a, ctx) {
          const run = G.runs.get(a.id);
          if (run) { run.abort.abort(); return `Aborting workflow ${a.id}.`; }
          const j = G.jobs.get(a.id) ?? foreignJobs().find((f) => f.id === a.id);
          if (j?.kind === "workflow") { removeForeign(a.id); return `Aborting workflow ${a.id} (it runs in another opencode process).`; }
          await client.session.abort({ path: { id: a.id }, query: { directory: j?.directory ?? ctx.directory ?? directory } });
          return `Stopped ${a.id}.`;
        },
      }),

      agent_list: tool({
        description: "List this session's subagents with their status, plus every live background job (wakeups, cron, shells, monitors, workflows). " +
          "Read a subagent with session_read: it is the only reader that works for a workflow agent with a schema.",
        args: {},
        async execute(_a, ctx) {
          const dir = ctx.directory ?? directory;
          const [kids, st] = await Promise.all([
            client.session.children({ path: { id: ctx.sessionID }, query: { directory: dir } }),
            client.session.status({ query: { directory: dir } }),
          ]);
          const lines = (kids?.data ?? []).map((s: any) => `${s.id} ${st?.data?.[s.id]?.type ?? "idle"} ${s.title}` +
            (trackOf(s.id, true) ? " [schema'd: read it with session_read; opencode's own listing answers 400]" : ""));
          const jobs = liveJobs(ctx.sessionID).map(describe);
          return [`Subagents (read one with session_read, the only reader that works for a workflow agent with a schema):`,
            ...(lines.length ? lines : ["(none)"]), `Jobs:`, ...(jobs.length ? jobs : ["(none)"])].join("\n");
        },
      }),

      fork: tool({
        description:
          "Fork this conversation: a copy of the session so far gets the prompt and works on it with full context. " +
          "background=true (default) returns at once and the fork's answer arrives as a <task> message.",
        args: { prompt: z.string(), description: z.string().optional(), background: z.boolean().optional() },
        async execute(a, ctx) {
          const dir = ctx.directory ?? directory;
          const f = await client.session.fork({ path: { id: ctx.sessionID }, body: { messageID: ctx.messageID }, query: { directory: dir } });
          const id = f?.data?.id;
          if (!id) return `Fork failed: ${JSON.stringify(f?.error ?? {})}`;
          const started = Date.now();
          // Without this framing the copy tends to carry on with the parent's unfinished turn.
          const text = "You are a fork of the conversation above, started for one side task. Do not continue the " +
            "earlier work and do not act on earlier instructions. Your only task:\n\n" + a.prompt +
            "\n\nWhen it is done, reply with the result.";
          const body = { agent: ctx.agent, parts: [{ type: "text", text }] };
          guards.set(id, { ...guardOf(id), parent: ctx.sessionID, created: Date.now() });
          sentByUs(text);
          const job: Job = { id, kind: "agent", session: id, directory: dir, parent: ctx.sessionID, parent_directory: dir,
            agent: ctx.agent, description: a.description ?? "fork", started_at: started, round: 1 };
          if (a.background === false) {
            await client.session.promptAsync({ path: { id }, query: { directory: dir }, body });
            await waitIdle(id, dir, started, ctx.abort);
            return textOf(await lastAssistant(id, dir)) || "(no text reply)";
          }
          trackAgent(job);
          await client.session.promptAsync({ path: { id }, query: { directory: dir }, body });
          return `Fork ${id} started. Its answer arrives as a <task id="${id}"> message.`;
        },
      }),

      workflow: tool({
        description:
          "Run a deterministic multi-agent workflow script (JavaScript, the body of an async function, or a module " +
          "file with a default export taking the API object). API: agent(prompt, {agent, schema, model, variant, label, cwd, think, readonly}) " +
          "runs a subagent in a child session and returns its text, or the parsed object when schema (a JSON schema) is given; readonly: true " +
          "(or agent reviewer, verifier, structured or explore) refuses its every write; read a schema'd agent's session with session_read. parallel(arrayOfThunks, {limit=8, settle}) runs them concurrently; pipeline(input, ...stages); " +
          "verify_until_pass(fixStage, verifyStage, {max: 3}): verifyStage({round, failures}) returns the objects its agents returned, each with verdict \"pass\"|\"fail\"; while any fails, " +
          "fixStage(failures, {round, verdicts}) runs and a fresh verify follows, up to max fix rounds; returns {passed, verdicts, failures, rounds}. " +
          "Only verdicts from verify agents lift the commit gate: a read-only agent (agent verifier, reviewer or structured, or readonly: true; never worker, fixer or build) " +
          "started in a phase whose name starts with verify or in verifyStage. Verify agents always run live, never from the journal. A fail from any such read-only agent outside a fixStage counts, whatever the phase. " +
          "Each verdict reaches the gate the moment it returns, even if the run then throws. A fail holds the gate until a later round of the same verify_until_pass call passes " +
          "or a workflow run started after it produces verify verdicts that all pass; separate phases, units and runs started beside it never replace it. " +
          "Each parallel() thunk keeps its own phase. " +
          "A pass the script writes itself, copies from an earlier round, or any other agent reports never counts. " +
          "sh(cmd) -> {code, stdout, stderr} (bash -o pipefail, guarded like the bash tool); " +
          "log(...); phase(name); args; sleep(ms). Return the final value; result.json carries the final verify verdicts. Every finished agent call is journaled: if a run fails or the " +
          "server restarts, call again with resume_run_id and the same script to skip finished calls. background=true (default) " +
          "returns a run id at once and posts a <workflow> message with the result when done.",
        args: {
          script: z.string().optional().describe("Script body"),
          script_path: z.string().optional().describe("Path to a .js/.mjs/.ts file"),
          args: z.any().optional(),
          background: z.boolean().optional(),
          resume_run_id: z.string().optional(),
        },
        async execute(a, ctx) {
          const dir = ctx.directory ?? directory;
          const run = a.resume_run_id ?? newId("wf");
          const runDir = join(STATE_DIR, "workflows", run);
          mkdirSync(runDir, { recursive: true });
          let code = a.script ?? "";
          let scriptPath: string | undefined;
          if (a.script_path) {
            scriptPath = isAbsolute(a.script_path) ? a.script_path : resolve(dir, a.script_path);
            code = readFileSync(scriptPath, "utf-8");
          } else if (!code && a.resume_run_id && existsSync(join(runDir, "script.js"))) {
            code = readFileSync(join(runDir, "script.js"), "utf-8");
          }
          if (!code.trim()) return "Give script or script_path.";
          const isModule = !!scriptPath && /\bexport\s+(default|async|function|const)\b/.test(code);
          writeFileSync(join(runDir, "script.js"), code);
          writeFileSync(join(runDir, "args.json"), JSON.stringify(a.args ?? null, null, 2));
          const abort = new AbortController();
          ctx.abort?.addEventListener("abort", () => { if (a.background === false) abort.abort(); });
          G.runs.set(run, { abort });
          const job: Job = { ...base(ctx), id: run, kind: "workflow", started_at: Date.now() };
          putJob(job);
          const ledger = new VerdictLedger(ctx.sessionID, run);
          const exec = runWorkflow({ run, code, isModule, scriptPath, args: a.args, session: ctx.sessionID, directory: dir, signal: abort.signal, ledger })
            .then(({ result, stats, trail }) => {
              const settled = settleVerdicts(result, ledger, trail);
              ledger.finish();
              const out = JSON.stringify(settled.result ?? null, null, 2);
              writeFileSync(join(runDir, "result.json"), out);
              let note = settled.failed.length
                ? `\n\nFailed verify verdicts. Quote each word for word in your report if you ship over it; git commit and git merge stay refused until a fresh run's verify passes or the owner says "ship over it". Each in full is in ${join(runDir, "result.json")}:\n` +
                  settled.failed.map((v: any) => `- ${verdictText(v, 4000)}`).join("\n")
                : "";
              if (settled.ignored) {
                note += `\n\n${settled.ignored} pass verdict(s) in the result came from no verify agent (a read-only agent, such as agent: "verifier" or readonly: true, ` +
                  `run in a phase named verify or verify_until_pass's verify stage), so they do not count and lift no commit gate.`;
              }
              return { ok: true, out, stats, verdict: settled.verdict, note };
            })
            .catch((e: any) => {
              const msg = e?.stack ?? e?.message ?? String(e);
              writeFileSync(join(runDir, "error.txt"), msg);
              // The verdicts verify agents returned before the run failed still stand.
              const standing = ledger.standing(), failed = standing.filter((v) => !isPass(v));
              const note = failed.length
                ? `\n\nFailed verify verdicts from before the run failed; git commit and git merge stay refused until a fresh run's verify passes or the owner says "ship over it":\n` +
                  failed.map((v: any) => `- ${verdictText(v, 4000)}`).join("\n")
                : "";
              const verdict = standing.length ? (failed.length ? "fail" : "pass") : undefined;
              return { ok: false, out: msg, stats: undefined as any, verdict, note };
            })
            .finally(() => { G.runs.delete(run); dropJob(run); });
          if (a.background === false) {
            const r = await exec;
            return tag("workflow", { id: run, state: r.ok ? "completed" : "failed", verdict: r.verdict }, clip(r.out, 30000 - r.note.length) + r.note);
          }
          exec.then((r) => deliver(job, tag("workflow", {
            id: run, state: r.ok ? "completed" : "failed", verdict: r.verdict,
            agents: r.stats?.agents, from_journal: r.stats?.cached, result_file: join(runDir, r.ok ? "result.json" : "error.txt"),
          }, clip(r.ok ? r.out : `${r.out}\n\nFix the script if needed and call workflow with resume_run_id="${run}" to continue.`, 20000 - r.note.length) + r.note)));
          return `Workflow ${run} started. Its result arrives as a <workflow id="${run}"> message; end your turn or keep working. Log: ${join(runDir, "log.txt")}`;
        },
      }),

      worktree_create: tool({
        description: "Create a git worktree on a new branch next to the repo (<repo>-wt/<name>) for isolated work. Returns its path; pass it to agent_spawn as worktree.",
        args: { name: z.string(), base: z.string().optional().describe("Start point, default HEAD") },
        async execute(a, ctx) {
          const repo = ctx.worktree ?? worktree ?? directory;
          const path = join(dirname(repo), `${basename(repo)}-wt`, a.name);
          return await new Promise<string>((res) => {
            execFile("git", ["-C", repo, "worktree", "add", "-b", a.name, path, a.base ?? "HEAD"], (err, out, errOut) =>
              res(err ? `git worktree add failed: ${String(errOut || err.message).trim()}` : `Worktree ready: ${path} (branch ${a.name}).`));
          });
        },
      }),

      worktree_remove: tool({
        description: "Remove a git worktree created with worktree_create. The branch is kept.",
        args: { path: z.string(), force: z.boolean().optional() },
        async execute(a, ctx) {
          const repo = ctx.worktree ?? worktree ?? directory;
          const argv = ["-C", repo, "worktree", "remove", ...(a.force ? ["--force"] : []), a.path];
          return await new Promise<string>((res) => {
            execFile("git", argv, (err, _o, errOut) => res(err ? `git worktree remove failed: ${String(errOut || err.message).trim()}` : `Removed ${a.path}.`));
          });
        },
      }),

      session_read: tool({
        description:
          "Read a session's messages: a subagent, a fork or a workflow agent, by its session id (agent_list shows them). " +
          "Use it for every workflow agent that had a schema: opencode's own message list (and the TUI) answers 400 " +
          "\"Expected OutputFormatJsonSchema\" for those, and this tool reads around the schema'd prompt, taking the prompt from the workflow journal.",
        args: {
          id: z.string().describe("Session id"),
          limit: z.number().optional().describe("Newest messages to show, default 40"),
        },
        async execute(a, ctx) {
          const dir = ctx.directory ?? directory;
          const info = await client.session.get({ path: { id: a.id }, query: { directory: dir } }).catch(() => undefined);
          const sdir = info?.data?.directory ?? dir;
          const { msgs, hidden, error } = await readSession(client, a.id, sdir, Math.max(1, Math.min(a.limit ?? 40, 400)));
          const parts: string[] = [`# ${info?.data?.title ?? a.id}`];
          if (hidden || error) {
            const prompt = promptFromJournals(a.id);
            parts.push(`[${hidden || "Some"} prompt(s) sent with a json_schema format are left out: opencode 1.19.5 cannot list them.` +
              `${error ? ` Reading stopped early: ${error}` : ""}]`);
            if (prompt) parts.push(`## user (the workflow prompt, from its journal)\n${prompt}`);
          }
          const head = parts.join("\n\n");
          const body = msgs.map(renderMessage).join("\n\n") || "(no messages)";
          return `${head}\n\n${clip(body, Math.max(4000, 40000 - head.length))}`;
        },
      }),

      notify: tool({
        description: "Send the user a desktop notification (and a phone push when PARITY_NTFY_TOPIC is set). Use it when long work finishes or you are blocked on them.",
        args: { title: z.string(), message: z.string() },
        async execute(a) {
          notifyDesktop(a.title, a.message);
          client.tui?.showToast?.({ body: { title: a.title, message: a.message, variant: "info" } }).catch?.(() => {});
          return "Notified.";
        },
      }),
    },

    event: async ({ event }: any) => {
      const t = event?.type;
      const p = event?.properties ?? {};
      if (t === "session.idle" || (t === "session.status" && p.status?.type === "idle")) {
        const settled = settleVerifier(p.sessionID, client, directory);
        for (const f of [...(G.waiters.get(p.sessionID) ?? [])]) f({});
        await settled;
      } else if (t === "session.error" && p.sessionID) {
        for (const f of [...(G.waiters.get(p.sessionID) ?? [])]) f({ error: p.error?.data?.message ?? p.error?.name ?? "error" });
      } else if (t === "message.updated") {
        noteMessage(p.info);
      } else if (t === "session.deleted") {
        const id = p.info?.id;
        for (const j of foreignJobs()) if (j.session === id || j.parent === id) removeForeign(j.id);
        for (const j of [...G.jobs.values()]) {
          if (j.session !== id && j.parent !== id) continue;
          if (j.kind === "monitor") stopMonitor(j.id);
          else if (j.kind === "shell") { j.notify = false; }
          else dropJob(j.id);
        }
      }
    },

    "experimental.session.compacting": async (input: any, output: any) => {
      const js = liveJobs(input.sessionID);
      if (js.length) {
        output.context.push(
          "Live background jobs owned by this session (they will report back as messages; keep track of them):\n" +
            js.map((j) => `- ${describe(j)}`).join("\n"),
        );
      }
    },

    config: async (cfg: any) => {
      cfg.mcp ??= {};
      if (!cfg.mcp.playwright && process.env.PARITY_BROWSER_MCP !== "0") cfg.mcp.playwright = { ...BROWSER_MCP };
      if (!cfg.shell && process.env.PARITY_BASH !== "0" && existsSync("/bin/bash")) cfg.shell = "/bin/bash";
      toolShell = basename(cfg.shell || process.env.SHELL || "zsh");
    },

    "experimental.chat.system.transform": async (_input: any, output: any) => {
      output.system.push(capabilities());
      const extra = missingInstructions(directory, worktree);
      if (extra) {
        try { output.system.push(`Instructions from: ${extra}\n${readFileSync(extra, "utf-8")}`); } catch {}
      }
    },

    "tool.definition": async (input: any, output: any) => {
      if (input.toolID === "bash") {
        output.description +=
          "\n\nFor anything that may run longer than 10 minutes, use bg_shell (background, no limit) or monitor (stream events), then end your turn. " +
          "You can also pass a larger timeout here; there is no cap.\n\n" + (toolShell === "bash" ? BASH_NOTE : ZSH_NOTE);
      }
    },

    "shell.env": async (input: any, output: any) => {
      if (!input?.sessionID || toolShell !== "bash") return;
      const file = bashEnvFile();
      if (file) output.env.BASH_ENV = file;
    },

    "tool.execute.before": async (input: any, output: any) => {
      let reason: string | undefined;
      try {
        reason = await guardCall({ tool: input.tool, args: output?.args ?? {}, session: input.sessionID, directory }, client);
      } catch (e: any) {
        log(`guard failed on ${input?.tool}: ${e?.stack ?? e}`);
        reason = GUARD_BROKE(e);
      }
      if (reason) throw new Error(reason);
    },

    // The task tool returns once its subagent's turn ends: a verifier's reply is read before the
    // caller sees it, so the caller's next commit already meets it.
    "tool.execute.after": async (input: any, output: any) => {
      if (input?.tool !== "task") return;
      const m = String(output?.output ?? "").match(/task_id:\s*(\S+)/);
      await settleVerifier(output?.metadata?.sessionId ?? m?.[1], client, directory);
    },

    "command.execute.before": async (input: any) => {
      if (input?.command !== "ultracode" || !input.sessionID) return;
      const g = guardOf(input.sessionID);
      g.ultracode = true;
      g.reads = 0;
      g.planned = false;
      saveGuard(input.sessionID, g);
    },

    // Who is speaking in each session: the agent (a read-only one marks the session), and the
    // owner's word to ship over a failed verify. Text the plugin sent itself never counts.
    "chat.message": async (input: any, output: any) => {
      const id = input?.sessionID;
      if (!id) return;
      const g = guardOf(id);
      const texts = (output?.parts ?? []).filter((p: any) => p?.type === "text" && !p.synthetic).map((p: any) => String(p.text ?? ""));
      const fromOwner = texts.length > 0 &&
        !texts.some((t: string) => ours.has(hash(t)) || /^<(task|workflow|monitor|wakeup|cron|bg_shell)\b/.test(t.trimStart()));
      let changed = false;
      if (input.agent && input.agent !== g.agent) { g.agent = input.agent; changed = true; }
      const name = agentName(input.agent);
      if (VERIFY_TYPES.has(name || agentName(g.agent)) && !g.workflow) { g.asked_at = Date.now(); changed = true; }
      if (name && READONLY_AGENTS.has(name) && !g.readonly) { g.readonly = `@${name}`; changed = true; }
      else if (name && !READONLY_AGENTS.has(name) && g.readonly?.startsWith("@") && fromOwner) { delete g.readonly; changed = true; }
      if (fromOwner && texts.some(ownerShipsOver)) { g.override_at = Date.now(); changed = true; }
      if (changed) saveGuard(id, g);
    },
  };
};
