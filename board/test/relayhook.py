#!/usr/bin/env python3
"""A failed cluster job says what failed, behind RELAY:, and nothing else.

What the checks are about:

  * ON FAILURE ONLY. `slurm_jobs/lib/relay_trap.sh` prints the recipe, the
    exit, the line it stopped after and the checkout; `relay_hook.py`, loaded
    into every Python through `sitecustomize.py`, prints the exception type,
    file and line, the inputs by name and count, and shapes. A job that
    succeeds prints none of it.
  * NEVER A VALUE. No exception message, no row, no patient-level file name,
    no location: a path is its `.env` key, and a basename only under a key
    whose files are aggregates. PSYCH-ASR names no file at all.
  * THE JOB'S STATUS. The trap changes no exit code, writes no file, and
    chains a recipe's own cleanup.
  * WIRED. Every TRD-EHR recipe sources it; every PSYCH-ASR recipe gets it
    through `job_env.sh`; the two copies of the Python are one file.

Runs the real library files, copied into temporary workspaces.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
from tutorboard import jobs, relay                                     # noqa: E402

TRD = os.path.join(REPO, "research", "TRD-EHR")
PSY = os.path.join(REPO, "research", "PSYCH-ASR")
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


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def relay_out(text):
    return [l for l in text.splitlines() if l.startswith("RELAY:")]


# --- wired -------------------------------------------------------------------------
LIB = ("relay_hook.py", "sitecustomize.py")
check("the two workspaces' Python helpers are one file",
      all(read(os.path.join(TRD, "slurm_jobs", "lib", f))
          == read(os.path.join(PSY, "slurm_jobs", "lib", f)) for f in LIB))
SOURCE = 'source "${SLURM_SUBMIT_DIR:-$PWD}/slurm_jobs/lib/relay_trap.sh"'
recipes = []
for dirpath, _, files in os.walk(os.path.join(TRD, "slurm_jobs")):
    recipes += [os.path.join(dirpath, f) for f in files if f.endswith(".sbatch")]
unwired, misplaced, trapped = [], [], []
for path in sorted(recipes):
    lines = read(path).splitlines()
    rel = os.path.relpath(path, TRD)
    if lines.count(SOURCE) != 1:
        unwired.append(rel)
        continue
    at = lines.index(SOURCE)
    before = [l for l in lines[1:at] if l.strip() and not l.startswith("#")]
    if before not in ([], ["set -e"]):
        misplaced.append(rel)
    if any(re.match(r"\s*trap\s.*\bEXIT\b", l) for l in lines):
        trapped.append(rel)
check("every TRD-EHR recipe (%d) sources relay_trap.sh once" % len(recipes),
      len(recipes) >= 45 and unwired == [])
check("first: after `set -e` where it has one, before every other command",
      misplaced == [])
check("and none sets an EXIT trap of its own, which would replace it",
      trapped == [] and "relay_on_exit cleanup" in read(os.path.join(
          TRD, "slurm_jobs", "review", "judge_prompt_comparison.sbatch")))
psy = sorted(f for f in os.listdir(os.path.join(PSY, "slurm_jobs"))
             if f.endswith(".sbatch"))
check("every PSYCH-ASR recipe sources job_env.sh, which sources the trap",
      psy and all("source slurm_jobs/lib/job_env.sh" in read(
          os.path.join(PSY, "slurm_jobs", f)) for f in psy)
      and 'source "$_JOB_ENV_LIB/relay_trap.sh"' in read(
          os.path.join(PSY, "slurm_jobs", "lib", "job_env.sh")))
for ws in (TRD, PSY):
    for name in LIB + ("relay_trap.sh",):
        p = subprocess.run(["git", "check-ignore", "-q",
                            os.path.join("slurm_jobs", "lib", name)], cwd=ws)
        check("%s: git sees slurm_jobs/lib/%s"
              % (os.path.basename(ws), name), p.returncode != 0)

# --- the behaviour, in a copy ------------------------------------------------------
base = tempfile.mkdtemp(prefix="tutor-relayhook-")
PY = sys.executable


def workspace(src, name):
    """A git workspace holding `src`'s library, data outside it."""
    ws = os.path.join(base, name)
    shutil.copytree(os.path.join(src, "slurm_jobs", "lib"),
                    os.path.join(ws, "slurm_jobs", "lib"))
    write(os.path.join(ws, "scripts", "__init__.py"), "")
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c",
                    "user.name=t", "commit", "-q", "--allow-empty", "-m",
                    "start"], cwd=ws, check=True)
    return ws


def run(ws, recipe, body, env=None):
    path = os.path.join(ws, "slurm_jobs", recipe)
    write(path, body)
    clean = dict((k, v) for k, v in os.environ.items()
                 if not k.startswith(("SLURM_", "RELAY_"))
                 and k != "PYTHONPATH")
    clean.update(env or {})
    p = subprocess.run(["bash", path], cwd=ws, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True,
                       env=clean)
    return p.returncode, p.stdout + p.stderr


try:
    ws = workspace(TRD, "trd")
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ws,
                         stdout=subprocess.PIPE,
                         universal_newlines=True).stdout.strip()
    data = os.path.join(base, "lab")
    write(os.path.join(data, "results", "sweep", "k_sweep.csv"),
          "k,auc\n1,0.6\n2,0.7\n")
    write(os.path.join(data, "patients", "1234567.json"), "{}")
    write(os.path.join(data, "person.csv"), "id,dob\n1234567,1950\n")
    env = {"RESULTS_DIR": os.path.join(data, "results"),
           "PATIENT_JSON_DIR": os.path.join(data, "patients"),
           "PERSON_CSV_PATH": os.path.join(data, "person.csv")}
    write(os.path.join(ws, "scripts", "fit.py"), """import os


class Frame:
    shape = (2, 2)


def main():
    sweep = os.path.join(os.environ["RESULTS_DIR"], "sweep", "k_sweep.csv")
    one = os.path.join(os.environ["PATIENT_JSON_DIR"], "1234567.json")
    people = os.environ["PERSON_CSV_PATH"]
    frame = Frame()
    value = "patient 1234567 has value 9.3"
    open(os.path.join(os.environ["RESULTS_DIR"], "trained", "lr.joblib"))


if __name__ == "__main__":
    main()
""")
    write(os.path.join(ws, "scripts", "fine.py"), "print('fine')\n")

    code, out = run(ws, "ok.sbatch", """#!/bin/bash
set -e
%s
set -u
%s -m scripts.fine
""" % (SOURCE, PY), env)
    check("a job that succeeds prints no RELAY: line, and exits 0",
          code == 0 and "fine" in out and relay_out(out) == [])

    code, out = run(ws, "sweep.sbatch", """#!/bin/bash
set -e
%s
set -u
cleanup() { echo "cleanup ran"; }
relay_on_exit cleanup
STATUS=0
%s -m scripts.fit || STATUS=$?
%s -m scripts.fine
exit "${STATUS}"
""" % (SOURCE, PY, PY), env)
    said = relay_out(out)
    m = re.search(r"RELAY: error FileNotFoundError at scripts/fit\.py:(\d+) "
                  r"in main$", "\n".join(said), re.M)
    check("a Python step that fails prints its exception type, file, line "
          "and function", m is not None)
    check("the step and the recipe it ran in",
          "RELAY: step scripts.fit, recipe slurm_jobs/sweep.sbatch" in said)
    check("the missing file by its .env key, named under RESULTS_DIR",
          "RELAY: missing RESULTS_DIR/trained/lr.joblib" in said)
    check("the inputs it held: an aggregate by name and rows, patient-level "
          "files withheld and never opened",
          "RELAY: input RESULTS_DIR/sweep/k_sweep.csv rows 2" in said
          and "RELAY: input PATIENT_JSON_DIR/<withheld> ext json" in said
          and "RELAY: input PERSON_CSV_PATH" in said)
    check("and the shape of what it held",
          "RELAY: shape main.frame Frame (2, 2)" in said)
    check("then the recipe's line: its exit, and the checkout",
          said[-1] == "RELAY: recipe slurm_jobs/sweep.sbatch failed: exit 1, "
          "checkout %s" % sha)
    whole = "\n".join(said)
    check("never the message, a value, a patient id or a location",
          "9.3" not in whole and "1234567" not in whole
          and data not in whole and "/" + os.path.basename(base) not in whole
          and all(len(l) <= 200 for l in said))
    check("the status is the job's, its cleanup still runs, and no exit "
          "file is written", code == 1 and "cleanup ran" in out
          and not os.path.exists(os.path.join(ws, "relay")))
    sites, step = jobs.failure_sites([l[len("RELAY:"):].strip()
                                      for l in said])
    check("and the Mac reads the file and line back out of it",
          m is not None and sites == ["scripts/fit.py:%s" % m.group(1)]
          and step == "")
    names_phi = None
    try:
        from tutorboard import leaving
        names_phi = leaving.policy(REPO)
    except Exception:                                    # noqa: BLE001
        names_phi = None
    kept = relay.relay_lines(out, names_phi)
    check("every one of them survives the report's scrub%s" % (
        " and the lab's PHI policy" if names_phi else ""),
        len(kept) == len(said) and not any("<path>" in l for l in kept))

    code, out = run(ws, "stop.sbatch", """#!/bin/bash
set -e
%s
set -u
echo one
false
echo never
""" % SOURCE)
    check("a command that stops a `set -e` recipe: the line it stopped at",
          code == 1 and "never" not in out and relay_out(out) == [
              "RELAY: recipe slurm_jobs/stop.sbatch failed: exit 1 after "
              "line 6, checkout %s" % sha]
          and jobs.failure_sites([relay_out(out)[0][7:]]) == ([], "6"))
    code, out = run(ws, "twelve.sbatch", """#!/bin/bash
%s
exit 12
""" % SOURCE)
    check("an explicit exit keeps its code, with no `set -e` and no Slurm "
          "variable set", code == 12 and relay_out(out) == [
              "RELAY: recipe slurm_jobs/twelve.sbatch failed: exit 12, "
              "checkout %s" % sha])
    spool = os.path.join(base, "spool", "job77")
    write(os.path.join(spool, "slurm_script"), """#!/bin/bash
set -e
%s
set -u
false
""" % SOURCE)
    p = subprocess.run(["bash", os.path.join(spool, "slurm_script")], cwd=ws,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True,
                       env=dict(os.environ, SLURM_SUBMIT_DIR=ws,
                                SLURM_JOB_NAME="neighbor_count_sweep"))
    check("a bare sbatch, run from Slurm's spool, is named by its job name",
          p.returncode == 1 and relay_out(p.stdout) == [
              "RELAY: recipe neighbor_count_sweep failed: exit 1 after line "
              "5, checkout %s" % sha])
    code, out = run(ws, "lib.sbatch", """#!/bin/bash
set -e
%s
%s -c 'import json; json.loads("{")'
""" % (SOURCE, PY))
    said = relay_out(out)
    check("an error a library raised names the library's own file and line",
          code == 1 and any(l.startswith("RELAY: error json.decoder."
                                         "JSONDecodeError") for l in said)
          and any(re.match(r"RELAY: raised in json/decoder\.py:\d+$", l)
                  for l in said)
          and "RELAY: step python -c, recipe slurm_jobs/lib.sbatch" in said)

    code, out = run(ws, "diagnose.sbatch", """#!/bin/bash
set -e
%s
%s -m relay_hook --look "${LOOK:-}" --module scripts.fit
""" % (SOURCE, PY), dict(env, LOOK="RESULTS_DIR/sweep"))
    said = relay_out(out)
    check("the probe a diagnostic runs: the checkout, which keys are set, a "
          "listing by name and count, whether a module is found",
          code == 0 and said[0] == "RELAY: probe checkout %s, recipe "
          "slurm_jobs/diagnose.sbatch" % sha
          and "RELAY: env PATIENT_JSON_DIR dir" in said
          and "RELAY: has RESULTS_DIR/sweep/k_sweep.csv rows 2" in said
          and "RELAY: module scripts.fit found" in said
          and not any("1234567" in l or data in l for l in said))
    refused = []
    for look in ("PATIENT_JSON_DIR", "RESULTS_DIR/../patients"):
        code, out = run(ws, "diagnose.sbatch", """#!/bin/bash
%s
%s -m relay_hook --look "${LOOK}"
""" % (SOURCE, PY), dict(env, LOOK=look))
        refused.append(code == 0 and "1234567" not in out
                       and any("refused" in l for l in relay_out(out)))
    check("and it lists nothing outside the aggregate keys", all(refused))

    # --- PSYCH-ASR: no file is named at all -----------------------------------------
    pws = workspace(PSY, "psy")
    write(os.path.join(pws, "phi", "inbox", "P123_s2.wav"), "RIFF")
    write(os.path.join(pws, "scripts", "join.py"), """import os


def main():
    audio = os.path.join(os.environ["PSYCH_ASR_DATA"], "inbox", "P123_s2.wav")
    turns = os.path.join("phi", "stage1", "P123_s2.rttm")
    open(turns)


if __name__ == "__main__":
    main()
""")
    code, out = run(pws, "join.sbatch", """#!/bin/bash
set -e
source slurm_jobs/lib/job_env.sh
%s -m scripts.join
""" % PY)
    said = relay_out(out)
    check("PSYCH-ASR: a failure names its location key and extension, no file",
          code == 1 and "RELAY: missing PSYCH_ASR_DATA/<withheld> ext rttm"
          in said and "RELAY: input PSYCH_ASR_DATA/<withheld> ext wav" in said
          and not any("P123" in l or "phi/" in l or ".rttm" in l
                      for l in said))
    check("and its lines survive the PHI policy whole",
          len(relay.relay_lines(out, names_phi)) == len(said))
finally:
    shutil.rmtree(base, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a failed job prints what failed and where, by name and count, and a "
      "job that succeeds prints nothing")
