// parity: the long-running half of an agent harness, as OpenCode tools.
//
// Wakeups, cron, background shells, monitors, background agents, forks, workflow scripts,
// worktrees and notifications. Every job reports back by posting a message into the session
// that started it (client.session.promptAsync), so the model can end its turn and be woken.
// That only works while an opencode process stays alive: run `opencode serve` (the
// com.mikeyferguson.opencode-serve LaunchAgent) and attach to it.
//
// State: $PARITY_STATE_DIR, else $XDG_STATE_HOME/opencode/parity, else
// ~/.local/state/opencode/parity. jobs.json holds every durable job; it is re-armed when the
// plugin loads. One registry per process (globalThis), so several instances (one per
// directory) never arm a job twice.
import { tool } from "@opencode-ai/plugin";
import { spawn, execFile } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import {
  appendFileSync, existsSync, mkdirSync, readFileSync, renameSync, statSync, writeFileSync,
  openSync, readSync, closeSync,
} from "node:fs";
import { homedir } from "node:os";
import { basename, dirname, isAbsolute, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const z = tool.schema;

// ---------------------------------------------------------------- state and registry

const STATE_DIR =
  process.env.PARITY_STATE_DIR ||
  join(process.env.XDG_STATE_HOME || join(homedir(), ".local", "state"), "opencode", "parity");
const JOBS_FILE = join(STATE_DIR, "jobs.json");
const LOG_FILE = join(STATE_DIR, "parity.log");
const MAX_TIMEOUT = 2 ** 31 - 1;

type Job = Record<string, any> & { id: string; kind: string; session: string; directory: string };

type Registry = {
  loaded: boolean;
  jobs: Map<string, Job>;
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

function save() {
  mkdirSync(STATE_DIR, { recursive: true });
  const durable = [...G.jobs.values()].filter((j) => j.durable !== false);
  const tmp = `${JOBS_FILE}.${process.pid}.tmp`;
  writeFileSync(tmp, JSON.stringify(durable, null, 2));
  renameSync(tmp, JOBS_FILE);
}

function loadJobs(): Job[] {
  try {
    const data = JSON.parse(readFileSync(JOBS_FILE, "utf-8"));
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

function putJob(job: Job) {
  G.jobs.set(job.id, job);
  save();
}

function dropJob(id: string) {
  G.timers.get(id)?.cancel();
  G.timers.delete(id);
  if (G.jobs.delete(id)) save();
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
  const dow = cronField(f[4].replace(/\b7\b/g, "0"), 0, 6, DAYS);
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

// Reads only the newest messages: opencode 1.19.5 cannot list a user message that carried a
// json_schema format, so a full listing of a schema child session fails.
async function lastAssistant(sessionID: string, directory: string) {
  const client = clientFor(directory);
  let lastErr: any;
  for (const limit of [1, 4, 16, 64]) {
    const r = await client.session.messages({ path: { id: sessionID }, query: { directory, limit } });
    if (r?.error) { lastErr = r.error; continue; }
    const msgs: any[] = r?.data ?? [];
    for (let i = msgs.length - 1; i >= 0; i--) if (msgs[i].info?.role === "assistant") return msgs[i];
    if (msgs.length < limit) return undefined;
  }
  if (lastErr) throw new Error(`could not read session ${sessionID}: ${JSON.stringify(lastErr).slice(0, 300)}`);
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
  if (G.jobs.get(job.id)?.reported === job.round) return;
  let text = "", error: string | undefined;
  try {
    const last = await lastAssistant(job.id, job.directory);
    text = textOf(last);
    error = errorOf(last);
    if (!last || !(last.info.time?.completed)) error ??= "the agent stopped before finishing";
  } catch (e: any) {
    error = e?.message ?? String(e);
  }
  job.reported = job.round;
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
  cwd?: string; think?: boolean; retries?: number;
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
  session: string; directory: string; signal: AbortSignal;
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
  const client = clientFor(opts.directory);
  const children = new Set<string>();
  opts.signal.addEventListener("abort", () => {
    for (const id of children) client.session.abort({ path: { id }, query: { directory: opts.directory } }).catch(() => {});
  });
  const wlog = (...parts: any[]) => {
    const line = parts.map((p) => (typeof p === "string" ? p : JSON.stringify(p))).join(" ");
    appendFileSync(logPath, `${new Date().toISOString()} ${line}\n`);
  };
  const phase = (name: string) => wlog(`== phase: ${name}`);

  async function agent(prompt: string, o: AgentOpts = {}) {
    if (opts.signal.aborted) throw new Error("workflow aborted");
    const base = hash(JSON.stringify([prompt, o.agent ?? "", o.schema ?? null, o.model ?? "", o.think ?? false]));
    const n = (seen.get(base) ?? 0) + 1;
    seen.set(base, n);
    const key = `${base}#${n}`;
    const label = o.label ?? prompt.slice(0, 60).replace(/\s+/g, " ");
    if (journal.has(key)) {
      stats.cached++;
      wlog(`agent (journal) ${label}`);
      return journal.get(key);
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
    const attempts = (o.retries ?? 2) + 1;
    let lastErr = "";
    for (let attempt = 1; attempt <= attempts; attempt++) {
      let text = prompt;
      if (attempt > 1) text = `Your previous reply failed: ${lastErr}. Try again.\n\n${prompt}`;
      const body: any = { agent: o.agent ?? "general", parts: [{ type: "text", text }] };
      const model = splitModel(o.model);
      if (model) body.model = model;
      if (o.variant) body.variant = o.variant;
      if (o.schema && !o.think) {
        // No retryCount: the server accepts it but then fails to list the session's messages.
        body.format = { type: "json_schema", schema: o.schema };
        body.variant = o.variant ?? "nothink";
      } else if (o.schema) {
        body.parts[0].text += `\n\nReply with only a JSON value matching this JSON schema, no prose:\n${JSON.stringify(o.schema)}`;
      }
      const started = Date.now();
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
      appendFileSync(journalPath, JSON.stringify({ key, label, ok: true, session: id, result }) + "\n");
      wlog(`agent done ${label}`);
      return result;
    }
    stats.failed++;
    appendFileSync(journalPath, JSON.stringify({ key, label, ok: false, session: id, error: lastErr }) + "\n");
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
          out[i] = await thunks[i]();
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

  function sh(cmd: string, o: { cwd?: string; timeout_ms?: number } = {}) {
    return new Promise<{ code: number; stdout: string; stderr: string }>((res) => {
      execFile("/bin/bash", ["-c", cmd], {
        cwd: o.cwd ? resolve(opts.directory, o.cwd) : opts.directory,
        timeout: o.timeout_ms ?? 0, maxBuffer: 64 * 1024 * 1024,
      }, (err: any, stdout, stderr) => {
        res({ code: err ? (typeof err.code === "number" ? err.code : 1) : 0, stdout: String(stdout), stderr: String(stderr) });
      });
    });
  }

  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
  const api = { agent, parallel, pipeline, sh, log: wlog, phase, args: opts.args, sleep, run: opts.run };
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
  return { result, stats };
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

// ---------------------------------------------------------------- the plugin

const LONG_WORK =
  "You run inside a persistent server, so you can wait, watch and work indefinitely. " +
  "Never say you cannot monitor, wait or run something for a long time: use monitor, wakeup, cron_create, " +
  "bg_shell, task with background=true, or workflow, then end your turn; results arrive as new messages.";

function liveJobs(session?: string) {
  return [...G.jobs.values()].filter((j) => !session || j.session === session || j.parent === session);
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

function boot(directory: string) {
  if (G.loaded) {
    // Jobs for this directory that were saved by a crashed process but never armed.
    for (const j of G.jobs.values()) if (j.directory === directory && !G.timers.has(j.id) && !G.procs.has(j.id)) rearm(j);
    return;
  }
  G.loaded = true;
  for (const j of loadJobs()) G.jobs.set(j.id, j);
  for (const j of [...G.jobs.values()]) rearm(j);
  log(`loaded ${G.jobs.size} jobs`);
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
        // The server restarted: the child's run ended with it. Report what it left.
        G.timers.set(j.id, { cancel: () => {} });
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
  boot(directory);

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
          const js = [...G.jobs.values()].filter((j) => j.kind === "cron" || j.kind === "wakeup");
          return js.length ? js.map(describe).join("\n") : "No cron jobs or wakeups.";
        },
      }),

      cron_delete: tool({
        description: "Delete a cron job or a pending wakeup by id.",
        args: { id: z.string() },
        async execute(a) {
          const j = G.jobs.get(a.id);
          if (!j || (j.kind !== "cron" && j.kind !== "wakeup")) return `No cron job or wakeup ${a.id}.`;
          dropJob(a.id);
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
          const mon = G.jobs.get(a.id);
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
          const j = G.jobs.get(a.id);
          if (!j) return `No running job ${a.id}.`;
          if (j.kind === "monitor") { stopMonitor(a.id); return `Stopped monitor ${a.id}.`; }
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
          const prev = G.jobs.get(a.id);
          const dir = prev?.directory ?? ctx.directory ?? directory;
          const job: Job = prev ?? { id: a.id, kind: "agent", session: a.id, directory: dir, parent: ctx.sessionID,
            parent_directory: ctx.directory ?? directory, agent: ctx.agent, description: "follow-up", round: 0 };
          job.round = (job.round ?? 0) + 1;
          job.started_at = Date.now();
          if (!prev) trackAgent(job); else save();
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
          const j = G.jobs.get(a.id);
          await client.session.abort({ path: { id: a.id }, query: { directory: j?.directory ?? ctx.directory ?? directory } });
          return `Stopped ${a.id}.`;
        },
      }),

      agent_list: tool({
        description: "List this session's subagents with their status, plus every live background job (wakeups, cron, shells, monitors, workflows).",
        args: {},
        async execute(_a, ctx) {
          const dir = ctx.directory ?? directory;
          const [kids, st] = await Promise.all([
            client.session.children({ path: { id: ctx.sessionID }, query: { directory: dir } }),
            client.session.status({ query: { directory: dir } }),
          ]);
          const lines = (kids?.data ?? []).map((s: any) => `${s.id} ${st?.data?.[s.id]?.type ?? "idle"} ${s.title}`);
          const jobs = liveJobs(ctx.sessionID).map(describe);
          return [`Subagents:`, ...(lines.length ? lines : ["(none)"]), `Jobs:`, ...(jobs.length ? jobs : ["(none)"])].join("\n");
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
          "file with a default export taking the API object). API: agent(prompt, {agent, schema, model, variant, label, cwd, think}) " +
          "runs a subagent in a child session and returns its text, or the parsed object when schema (a JSON schema) is given; " +
          "parallel(arrayOfThunks, {limit=8, settle}) runs them concurrently; pipeline(input, ...stages); sh(cmd) -> {code, stdout, stderr}; " +
          "log(...); phase(name); args; sleep(ms). Return the final value. Every finished agent call is journaled: if a run fails or the " +
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
          const exec = runWorkflow({ run, code, isModule, scriptPath, args: a.args, session: ctx.sessionID, directory: dir, signal: abort.signal })
            .then(({ result, stats }) => {
              const out = JSON.stringify(result ?? null, null, 2);
              writeFileSync(join(runDir, "result.json"), out);
              return { ok: true, out, stats };
            })
            .catch((e: any) => {
              const msg = e?.stack ?? e?.message ?? String(e);
              writeFileSync(join(runDir, "error.txt"), msg);
              return { ok: false, out: msg, stats: undefined as any };
            })
            .finally(() => { G.runs.delete(run); dropJob(run); });
          if (a.background === false) {
            const r = await exec;
            return tag("workflow", { id: run, state: r.ok ? "completed" : "failed" }, clip(r.out, 30000));
          }
          exec.then((r) => deliver(job, tag("workflow", {
            id: run, state: r.ok ? "completed" : "failed",
            agents: r.stats?.agents, from_journal: r.stats?.cached, result_file: join(runDir, r.ok ? "result.json" : "error.txt"),
          }, clip(r.ok ? r.out : `${r.out}\n\nFix the script if needed and call workflow with resume_run_id="${run}" to continue.`, 20000))));
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
        for (const f of [...(G.waiters.get(p.sessionID) ?? [])]) f({});
      } else if (t === "session.error" && p.sessionID) {
        for (const f of [...(G.waiters.get(p.sessionID) ?? [])]) f({ error: p.error?.data?.message ?? p.error?.name ?? "error" });
      } else if (t === "session.deleted") {
        const id = p.info?.id;
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

    "experimental.chat.system.transform": async (_input: any, output: any) => {
      output.system.push(LONG_WORK);
    },

    "tool.definition": async (input: any, output: any) => {
      if (input.toolID === "bash") {
        output.description +=
          "\n\nFor anything that may run longer than 10 minutes, use bg_shell (background, no limit) or monitor (stream events), then end your turn. " +
          "You can also pass a larger timeout here; there is no cap.";
      }
    },
  };
};
