#!/usr/bin/env python3
"""IT's model server: a `libr-ai` request filed, run, and its answer reported.

What the checks are about:

  * ONLY AN OPEN SUBJECT. IT's server keeps every chat, so a request from a
    subject whose tutorboard.json does not say `"phi": false` is refused on
    the Mac, refused again by the relay when filed anyway, and refused a third
    time by the task script.
  * A REQUEST RUNS AS A JOB. The relay submits `libr-ai-task.sh` with the
    brief beside the wrapper, in the subject's ignored relay/state/.
  * THE ANSWER COMES BACK. The job's log is the model's answer, and the
    report carries it, so the woken session reads it.
  * READ-ONLY. The opencode config denies the shell, edits, the web and
    every path outside the subject.

Git is real (a bare origin and two clones); Slurm is a table; opencode is a
script that prints its prompt's last line.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tutorboard import jobs, libr_ai, relay                     # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def git(cwd, *args):
    p = subprocess.run(["git"] + list(args), cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=False)
    return p.stdout.decode("utf-8", "replace").strip()


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


class Done:
    def __init__(self, code=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


class Slurm:
    def __init__(self):
        self.calls, self.scripts, self.queue, self.next_id = [], {}, {}, 700

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        name = os.path.basename(argv[0])
        if name == "sbatch":
            self.next_id += 1
            jid = str(self.next_id)
            self.scripts[jid] = (argv[-1], kw.get("cwd"))
            self.queue[jid] = "PENDING"
            return Done(0, jid + "\n")
        if name == "scontrol":
            return Done(0, "JobId=%s StdOut=logs/job-%%j.out "
                           "StdErr=logs/job-%%j.err\n" % argv[-1])
        if name == "squeue":
            return Done(0, "".join("%s|%s\n" % kv
                                   for kv in sorted(self.queue.items())))
        raise AssertionError("unexpected command %r" % argv)

    def run_job(self, jid):
        script, cwd = self.scripts[jid]
        os.makedirs(os.path.join(cwd, "logs"), exist_ok=True)
        with open(os.path.join(cwd, "logs", "job-%s.out" % jid), "w") as out, \
                open(os.path.join(cwd, "logs", "job-%s.err" % jid), "w") as err:
            p = subprocess.run(["bash", script], cwd=cwd, stdout=out,
                               stderr=err)
        self.queue.pop(jid, None)
        return p.returncode


POLICY = ("import re\n\ndef names_phi(text):\n"
          "    return bool(re.search(r'SESSION-\\d+', str(text)))\n")
# ai-config's generic adapter, standing in: a path with a `phi` part is fenced.
GENERIC = ("import sys\n"
           "p = sys.argv[sys.argv.index('--path') + 1]\n"
           "sys.exit(1 if 'phi' in p.split('/') else 0)\n")
# opencode, standing in: says which config and model it ran with, and the
# task's own words, which are the prompt's last line.
OPENCODE = """#!/bin/bash
echo "config $(basename "$OPENCODE_CONFIG")"
echo "model $3"
printf '%s\\n' "${@: -1}" | tail -n 1
"""

base = tempfile.mkdtemp(prefix="tutor-libr-ai-")
saved = dict(os.environ)
try:
    # --- validate, pure -----------------------------------------------------
    req = {"id": "q1", "kind": "libr-ai", "brief": "what does knn.py do?"}
    ok, probs = jobs.validate(req, [], set(), {}, phi_false=True)
    check("a libr-ai request from an open subject validates",
          probs == [] and ok["brief"] == "what does knn.py do?")
    ok, probs = jobs.validate(req, [], set(), {}, phi_false=False)
    check("and is refused where phi is not false, naming Colibri",
          ok is None and any("Colibri" in p for p in probs))
    ok, probs = jobs.validate(dict(req, model="gpt-oss:20b"), [], set(), {},
                              phi_false=True)
    check("a model name rides along", probs == [] and ok["model"] == "gpt-oss:20b")
    ok, probs = jobs.validate(dict(req, model="x; rm -rf"), [], set(), {},
                              phi_false=True)
    check("a model that is not a name is refused",
          ok is None and any("model" in p for p in probs))
    cfg = load(os.path.join(ROOT, "scripts", "libr-ai-task.json"))
    perm = (cfg or {}).get("permission") or {}
    check("the task's opencode config denies the shell, edits, the web and "
          "every path outside the subject",
          all(perm.get(k) == "deny" for k in ("bash", "edit", "webfetch",
                                              "websearch", "external_directory",
                                              "task"))
          and cfg.get("enabled_providers") == ["libr-ai"])

    # --- two subjects, through git --------------------------------------------
    origin = os.path.join(base, "origin.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin],
                   check=True)
    seed = os.path.join(base, "seed")
    os.makedirs(seed)
    git(seed, "init", "-q", "-b", "main")
    for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
        git(seed, "config", k, v)
    write(os.path.join(seed, ".gitignore"),
          "**/relay/state/\n/relay/state.json\n/relay/.lock\nai-config/\n")
    for name, phi in (("Open", False), ("Closed", True)):
        ws = os.path.join(seed, "projects", name)
        write(os.path.join(ws, "tutorboard.json"),
              json.dumps({"name": name, "phi": phi}))
        write(os.path.join(ws, ".gitignore"), "logs/\n")
        write(os.path.join(ws, "knn.py"), "print('neighbours')\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "seed")
    git(seed, "remote", "add", "origin", origin)
    git(seed, "push", "-q", "-u", "origin", "main")

    def clone(name):
        where = os.path.join(base, name)
        git(base, "clone", "-q", origin, where)
        for k, v in (("user.email", "%s@example.com" % name),
                     ("user.name", name)):
            git(where, "config", k, v)
        return where

    mac, cluster = clone("mac"), clone("cluster")
    write(os.path.join(cluster, "ai-config", "policy", "phi.py"), POLICY)
    write(os.path.join(cluster, "ai-config", "adapters", "generic.py"), GENERIC)
    home = os.path.join(base, "home")
    write(os.path.join(home, ".config", "libr-ai", "key"), "sk-test\n")
    fake_bin = os.path.join(base, "bin")
    write(os.path.join(fake_bin, "opencode"), OPENCODE)
    os.chmod(os.path.join(fake_bin, "opencode"), 0o755)
    os.environ["HOME"] = home
    os.environ["PATH"] = fake_bin + os.pathsep + os.environ.get("PATH", "")
    os.environ["SLURM_JOB_ID"] = "999"
    os.environ["COLI_QUEUE_ROOT"] = os.path.join(base, "queue")
    os.makedirs(os.environ["COLI_QUEUE_ROOT"])
    from tutorboard import colibri as coli
    coli._all_jobs = lambda: []

    m_open = os.path.join(mac, "projects", "Open")
    m_closed = os.path.join(mac, "projects", "Closed")
    c_open = os.path.join(cluster, "projects", "Open")

    got = libr_ai.ask(m_closed, "read the notes", push=False)
    check("the Mac refuses to file from a PHI subject",
          not got["ok"] and any("phi" in p for p in got["problems"])
          and not os.path.isdir(os.path.join(m_closed, "relay", "requests")))
    got = libr_ai.ask(m_open, "what does knn.py do?", label="knn",
                      session="20261010-090000", push=False)
    check("and files from an open one", got["ok"])
    rid = got.get("id")
    git(mac, "push", "-q")

    # A request from the PHI subject written by hand, skipping the Mac's check.
    sneak = {"id": "sneak", "kind": "libr-ai", "brief": "read the notes",
             "filed": time.time()}
    write(os.path.join(m_closed, "relay", "requests", "sneak.json"),
          json.dumps(sneak))
    git(mac, "add", "-A")
    git(mac, "commit", "-q", "-m", "a request filed by hand")
    git(mac, "push", "-q")

    slurm = Slurm()
    summary = relay.run_pass(cluster, run=slurm)
    check("the relay submits the open subject's request",
          rid in summary["submitted"] and not summary["error"])
    check("and refuses the hand-filed one from the PHI subject",
          "sneak" in summary["refused"])
    rep = load(os.path.join(c_open, "relay", "reports", rid + ".json"))
    jid = rep and rep.get("jobid")
    check("its report says submitted, with the job id",
          rep and rep["state"] == "submitted" and jid in slurm.scripts)
    script = open(slurm.scripts[jid][0], encoding="utf-8").read()
    check("the job runs the task script on the default model, in c3_short",
          "libr-ai-task.sh" in script and "gpt-oss:120b" in script
          and "--partition=c3_short" in script)
    brief = os.path.join(c_open, "relay", "state", rid + ".brief")
    check("the brief waits beside the wrapper, where git cannot see it",
          os.path.isfile(brief)
          and git(cluster, "check-ignore", "-q",
                  os.path.relpath(brief, cluster)) == "")

    check("the job runs and exits 0", slurm.run_job(jid) == 0)
    summary = relay.run_pass(cluster, run=slurm)
    rep = load(os.path.join(c_open, "relay", "reports", rid + ".json"))
    out = "\n".join(rep.get("output") or []) if isinstance(
        rep.get("output"), list) else str(rep.get("output") or "")
    check("it completes, and the report carries the answer",
          rep["state"] == "completed" and "what does knn.py do?" in out
          and "config libr-ai-task.json" in out
          and "libr-ai/gpt-oss:120b" in out)
    git(mac, "pull", "-q", "--rebase")
    rec = next((r for r in jobs.relayed(m_open) if r["request"] == rid), None)
    said = jobs.relay_sense(m_open, rec) if rec else ""
    check("the woken session reads the answer, as IT's model's",
          "what does knn.py do?" in said and "IT's model server" in said)

    # The task script refuses a PHI subject on its own, too.
    c_closed = os.path.join(cluster, "projects", "Closed")
    write(os.path.join(base, "b.txt"), "x")
    p = subprocess.run(["bash", libr_ai.TASK, c_closed,
                        os.path.join(base, "b.txt"), "gpt-oss:120b"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    check("the task script refuses a subject whose phi is not false",
          p.returncode == 3 and b"phi is false" in p.stderr
          and b"config" not in p.stdout)
finally:
    os.environ.clear()
    os.environ.update(saved)
    shutil.rmtree(base, ignore_errors=True)

print()
print("%d FAILURES" % len(fails) if fails else "IT's model answers, and only "
      "where nothing fenced can reach it")
sys.exit(1 if fails else 0)
