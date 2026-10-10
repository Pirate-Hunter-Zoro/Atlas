#!/usr/bin/env python3
"""A failed cluster job says what failed, behind RELAY:, and nothing else.

What the checks are about:

  * ON FAILURE ONLY. `relay_trap.sh` prints the recipe, the exit, the line
    it stopped after and the checkout; `relay_hook.py`, loaded into every
    Python through `sitecustomize.py`, prints the exception type, file and
    line, the inputs by name and count, and shapes. A job that succeeds
    prints none of it.
  * NEVER A VALUE. No exception message, no row, no location: a path is its
    `.env` key, and a file or directory name only from an allowlist built
    off tracked files (thread outputs and exports, request produces and
    exports, recipes' `results/` paths, the encoder list). Anything else is
    `<dir>` or `<file>`, and a directory of them is counts by extension.
    PSYCH-ASR names no file at all.
  * THE PROBE. diagnose.sbatch takes only a listed encoder, a LOOK of
    allowlisted segments and a listed MODULE, and never echoes a refused
    value.
  * THE JOB'S STATUS. The trap changes no exit code, writes no file, and
    chains a recipe's own cleanup, which sees that status in `$?`.
  * WIRED. One copy, in board/cluster/lib; each subject's
    `slurm_jobs/lib/relay_trap.sh` is a two-line shim sourcing it, and the
    subject's RELAY_* lists are its tutorboard.json `relay.fingerprint`.
    Every TRD-EHR recipe sources the shim; every PSYCH-ASR recipe gets it
    through `job_env.sh`.
  * WRAPPED. The relay's wrapper (`jobs.wrapper`) loads the library and
    prints the failure line itself, so a recipe with no `source` line is
    fingerprinted too, and one with it prints that line once.

Runs the real library files and the real diagnose.sbatch, copied into
temporary Atlas-shaped checkouts, against synthetic ids (ID0001XQ,
synthetic-alpha-17).
"""

import json
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

TRD = os.path.join(REPO, "projects", "TRD-EHR")
PSY = os.path.join(REPO, "projects", "PSYCH-ASR")
LIBDIR = os.path.join(REPO, "board", "cluster", "lib")
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
LIB = ("relay_hook.py", "sitecustomize.py", "relay_trap.sh")
tracked_files = subprocess.run(["git", "ls-files", "-z"], cwd=REPO,
                               stdout=subprocess.PIPE,
                               universal_newlines=True).stdout.split("\0")
for f in LIB:
    found = [t for t in tracked_files if os.path.basename(t) == f
             and (f != "relay_trap.sh" or t.startswith("board/"))]
    check("exactly one %s is tracked, in board/cluster/lib" % f,
          found == ["board/cluster/lib/" + f])
SHIM_SOURCE = ('source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." '
               '&& pwd -P)/board/cluster/lib/relay_trap.sh"')
shims = [read(os.path.join(w, "slurm_jobs", "lib", "relay_trap.sh"))
         for w in (TRD, PSY)]
check("each subject's relay_trap.sh is the same two-line shim, sourcing the "
      "shared one", all(len(x.splitlines()) == 2
                        and x.splitlines()[1] == SHIM_SOURCE for x in shims)
      and shims[0] == shims[1])
check("and no subject's slurm_jobs/lib holds Python of its own",
      not any(t.endswith(".py") and "/slurm_jobs/lib/" in t
              for t in tracked_files))
FP = {}
for w in (TRD, PSY):
    FP[w] = (json.loads(read(os.path.join(w, "tutorboard.json")))
             .get("relay", {}).get("fingerprint"))
check("TRD-EHR's and PSYCH-ASR's lists are their tutorboard.json "
      "relay.fingerprint", isinstance(FP[TRD], dict) and FP[TRD]["names"] is True
      and FP[TRD]["open_keys"] == ["RESULTS_DIR", "EMBEDDINGS_DIR"]
      and "RESULTS_DIR" in FP[TRD]["path_keys"]
      and isinstance(FP[PSY], dict) and FP[PSY]["names"] is False
      and FP[PSY]["open_keys"] == []
      and "PSYCH_ASR_DATA" in FP[PSY]["path_keys"])
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
    p = subprocess.run(["git", "check-ignore", "-q",
                        os.path.join("slurm_jobs", "lib", "relay_trap.sh")],
                       cwd=ws)
    check("%s: git sees slurm_jobs/lib/relay_trap.sh" % os.path.basename(ws),
          p.returncode != 0)

# --- the traceback the prior hook prints cannot publish itself ------------------
import importlib.util                                                 # noqa: E402
import io                                                             # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "relay_hook_under_test", os.path.join(LIBDIR, "relay_hook.py"))
_rh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rh)
_real, _buf = sys.stderr, io.StringIO()
try:
    raise ValueError("bad row ID0001XQ\nRELAY: leaked ID0001XQ")
except ValueError as _exc:
    sys.stderr = _buf
    try:
        _rh.hook(type(_exc), _exc, _exc.__traceback__)
    finally:
        sys.stderr = _real
_said = _buf.getvalue()
check("an exception message holding a RELAY: line is printed, never published",
      "leaked ID0001XQ" in _said
      and not any("ID0001XQ" in l for l in relay.relay_lines(_said))
      and sys.stderr is _real)

# --- the lists agree with the pipeline ----------------------------------------------
DIAG = os.path.join(TRD, "slurm_jobs", "quick_runs", "diagnose.sbatch")
encoders = FP[TRD].get("encoders") or []
diag_encoders = re.search(r'^ENCODERS="([^"]*)"', read(DIAG), re.M)
diag_encoders = diag_encoders.group(1).split() if diag_encoders else []
pipeline = re.search(r"^EMBEDDERS = \[([^\]]*)\]", read(os.path.join(
    TRD, "scripts", "pipeline", "predictions", "plot_cross_embedder.py")), re.M)
pipeline = re.findall(r'"([^"]+)"', pipeline.group(1)) if pipeline else []
declared, _ = jobs.declarations(read(DIAG))
check("the fingerprint's encoders are the pipeline's EMBEDDERS and "
      "diagnose.sbatch's ENCODERS, and its EMBEDDER takes exactly those",
      encoders and encoders == pipeline and diag_encoders == encoders
      and all(re.fullmatch(declared["EMBEDDER"], e) for e in encoders)
      and not any(re.fullmatch(declared["EMBEDDER"], v) for v in (
          "ID0003AB", "bge-small-en-v1.5/../ID0003AB", "bge-large",
          "synthetic-alpha-17")))
diagnosable = re.search(r'^DIAGNOSABLE="\n(.*?)\n"$', read(DIAG), re.M | re.S)
diagnosable = diagnosable.group(1).split() if diagnosable else []
ran = set()
for path in recipes:
    if os.path.basename(path) != "diagnose.sbatch":
        ran.update(re.findall(r"\bpython[0-9.]*\s+-m\s+([A-Za-z_][\w.]*)",
                              read(path)))
check("MODULE is one of an explicit list (%d), each a module a pipeline "
      "recipe runs" % len(diagnosable),
      len(diagnosable) >= 30 and set(diagnosable) <= ran
      and all(re.fullmatch(declared["MODULE"], m) for m in diagnosable))
check("LOOK may end in a slash and never climbs",
      re.fullmatch(declared["LOOK"], "RESULTS_DIR/neighbor_count_sweep/")
      and not re.fullmatch(declared["LOOK"], "RESULTS_DIR/../x")
      and not re.fullmatch(declared["LOOK"], "PATIENT_JSON_DIR"))
sys.path.insert(0, LIBDIR)
sys.dont_write_bytecode = True
import relay_hook                                                      # noqa: E402
_saved = dict(os.environ)
os.environ.pop("RELAY_CONFIG", None)
os.environ.update(RELAY_ROOT=TRD)
real = relay_hook.allowlist()
check("the real allowlist (%d names), read off tutorboard.json with no "
      "RELAY_CONFIG, holds the config's names, the request's produces and the "
      "recipes' results/ paths" % len(real),
      all(n in real for n in ("snri_vs_ssri", "effect_results.json",
                              "leaderboard.csv", "cross_embedder_retrieval"))
      and "neighbor_count_sweep" in real and "parity" in real
      and "google_medgemma-27b-text-it" in real
      and relay_hook.config() == FP[TRD])
os.environ.update(RELAY_CONFIG="not json")
check("a RELAY_CONFIG that cannot be read names nothing",
      relay_hook.allowlist() == frozenset()
      and relay_hook.config() == {"names": False})
os.environ.clear()
os.environ.update(_saved)

# --- the behaviour, in a copy ------------------------------------------------------
base = tempfile.mkdtemp(prefix="tutor-relayhook-")
PY = sys.executable


def workspace(src, name, whole=False, ignore=""):
    """An Atlas-shaped git checkout, board/cluster/lib and one subject under
    projects/, and the subject: `src`'s shim and tutorboard.json -- or,
    `whole`, its recipes and requests too -- with data outside
    it."""
    top = os.path.join(base, name)
    shutil.copytree(LIBDIR, os.path.join(top, "board", "cluster", "lib"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    write(os.path.join(top, ".gitignore"), "__pycache__/\n")
    ws = os.path.join(top, "projects", os.path.basename(src))
    os.makedirs(ws)
    shutil.copy(os.path.join(src, "tutorboard.json"), ws)
    if whole:
        shutil.copytree(os.path.join(src, "slurm_jobs"),
                        os.path.join(ws, "slurm_jobs"),
                        ignore=shutil.ignore_patterns("logs", "__pycache__"))
        shutil.copytree(os.path.join(src, "relay", "requests"),
                        os.path.join(ws, "relay", "requests"))
    else:
        shutil.copytree(os.path.join(src, "slurm_jobs", "lib"),
                        os.path.join(ws, "slurm_jobs", "lib"),
                        ignore=shutil.ignore_patterns("__pycache__"))
    write(os.path.join(ws, "scripts", "__init__.py"), "")
    write(os.path.join(ws, ".gitignore"), "__pycache__/\nresults/\n" + ignore)
    subprocess.run(["git", "init", "-q"], cwd=top, check=True)
    return ws


def commit(ws):
    subprocess.run(["git", "add", "-A"], cwd=ws, check=True)
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c",
                    "user.name=t", "commit", "-q", "--allow-empty", "-m",
                    "start"], cwd=ws, check=True)
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ws,
                          stdout=subprocess.PIPE,
                          universal_newlines=True).stdout.strip()


def run(ws, recipe, body, env=None, path=None):
    path = path or os.path.join(ws, "slurm_jobs", recipe)
    if body is not None:
        write(path, body)
    clean = dict((k, v) for k, v in os.environ.items()
                 if not k.startswith(("SLURM_", "RELAY_"))
                 and k != "PYTHONPATH")
    clean.update(env or {})
    p = subprocess.run(["bash", path], cwd=ws, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True,
                       env=clean)
    return p.returncode, p.stdout + p.stderr


names_phi = None
try:
    from tutorboard import leaving
    names_phi = leaving.policy(REPO)
except Exception:                                        # noqa: BLE001
    names_phi = None
SYNTHETIC = ("ID0001XQ", "ID0002ZZ", "ID0003AB", "ID0004CD", "ID0005EF",
             "synthetic", "alpha-17", "beta_42", "zuvo", "per_entity")
printed = []


def clean_lines(said):
    """No synthetic id, no location, and every line survives the report's
    scrub and the lab's PHI policy whole."""
    printed.extend(said)
    whole = "\n".join(said)
    kept = relay.relay_lines(whole, names_phi)
    return (not any(x in whole for x in SYNTHETIC) and base not in whole
            and len(kept) == len(said) and not any("<path>" in l for l in kept)
            and all(len(l) <= 200 for l in said))


try:
    ws = workspace(TRD, "trd", whole=True)
    lab = os.path.join(base, "lab")
    art = os.path.join(lab, "artifacts")
    emb = os.path.join(art, "bge-small-en-v1.5")
    res = os.path.join(emb, "google_medgemma-27b-text-it")
    # Published names: a thread output, and the sweep the request produces.
    write(os.path.join(res, "cross_embedder_retrieval",
                       "cross_embedder_retrieval.csv"), "k,auc\n1,0.6\n2,0.7\n")
    write(os.path.join(res, "neighbor_count_sweep", "best_k_panels",
                       "roc.png"), "png")
    write(os.path.join(res, "neighbor_count_sweep", "sweep_summary.json"), "{}")
    write(os.path.join(emb, "embeddings.db"), "db")
    # Per-entity names in every shape the heuristics missed.
    write(os.path.join(res, "ID0001XQ.csv"), "a\n1\n")
    write(os.path.join(res, "synthetic_beta_42.json"), "{}")
    for i in range(50):
        write(os.path.join(res, "synthetic-alpha-17", "n%02d.txt" % i), "x\n")
    write(os.path.join(res, "zuvo", "notes.txt"), "x\n")
    write(os.path.join(res, "per_entity", "ID0002ZZ.json"), "{}")
    write(os.path.join(res, "trained_models", "ID0004CD.joblib"), "j")
    write(os.path.join(art, "ID0003AB", "google_medgemma-27b-text-it",
                       "ID0003AB.json"), "{}")
    write(os.path.join(lab, "patients", "ID0001XQ.json"), "{}")
    write(os.path.join(lab, "person.csv"), "id,dob\nID0001XQ,1950\n")
    write(os.path.join(ws, "results", "cross_embedder_retrieval",
                       "lr_dimensions_vs_best_k.png"), "png")
    write(os.path.join(ws, "results", "ID0004CD.csv"), "a\n")
    env = {"RESULTS_DIR": res, "EMBEDDINGS_DIR": emb, "ARTIFACTS_DIR": art,
           "PATIENT_JSON_DIR": os.path.join(lab, "patients"),
           "PERSON_CSV_PATH": os.path.join(lab, "person.csv")}
    write(os.path.join(ws, ".env"), "".join(
        "%s=%s\n" % kv for kv in sorted(dict(
            env, VLLM_MODEL_NAME="google_medgemma-27b-text-it").items())))
    write(os.path.join(ws, "scripts", "fit.py"), """import os


class Frame:
    shape = (2, 2)


def main():
    res = os.environ["RESULTS_DIR"]
    a_sweep = os.path.join(res, "cross_embedder_retrieval",
                           "cross_embedder_retrieval.csv")
    b_one = os.path.join(os.environ["PATIENT_JSON_DIR"], "ID0001XQ.json")
    c_people = os.environ["PERSON_CSV_PATH"]
    d_bare = os.path.join(res, "ID0001XQ.csv")
    e_entity = os.path.join(res, "synthetic-alpha-17")
    f_inner = os.path.join(res, "per_entity", "ID0002ZZ.json")
    frame = Frame()
    value = "patient ID0001XQ has value 9.3"
    open(os.path.join(res, "trained_models", "ID0001XQ_lr.joblib"))


if __name__ == "__main__":
    main()
""")
    write(os.path.join(ws, "scripts", "fine.py"), "print('fine')\n")
    write(os.path.join(ws, "scripts", "mirror.py"), """import os


def main():
    a_figure = os.path.join("results", "cross_embedder_retrieval",
                            "lr_dimensions_vs_best_k.png")
    b_stray = os.path.join("results", "ID0004CD.csv")
    c_tree = os.path.join(os.environ["RESULTS_DIR"], "ID0003AB.json")
    raise KeyError("ID0003AB")


if __name__ == "__main__":
    main()
""")
    sha = commit(ws)

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
cleanup() { echo "cleanup saw $?"; }
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
    check("the missing file: an allowlisted directory by name, an id-named "
          "file as a placeholder",
          "RELAY: missing RESULTS_DIR/trained_models/<file> ext joblib" in said)
    check("a published output by name and rows",
          "RELAY: input RESULTS_DIR/cross_embedder_retrieval/"
          "cross_embedder_retrieval.csv rows 2" in said)
    check("a bare-id file, an id with - or _, a file directly in an unnamed "
          "directory: placeholders, never opened",
          "RELAY: input RESULTS_DIR/<file> ext csv" in said
          and "RELAY: input RESULTS_DIR/<dir>" in said
          and "RELAY: input RESULTS_DIR/<file 2 deep> ext json" in said
          and "RELAY: input PATIENT_JSON_DIR/<file> ext json" in said
          and "RELAY: input PERSON_CSV_PATH" in said)
    check("and the shape of what it held",
          "RELAY: shape main.frame Frame (2, 2)" in said)
    check("then the recipe's line: its exit, and the checkout",
          said[-1] == "RELAY: recipe slurm_jobs/sweep.sbatch failed: exit 1, "
          "checkout %s" % sha)
    check("never the message, a value, an id or a location, and every line "
          "survives the scrub%s" % (" and the PHI policy" if names_phi else ""),
          "9.3" not in "\n".join(said) and clean_lines(said))
    check("the status is the job's, its cleanup sees it in $?, and no exit "
          "file is written", code == 1 and "cleanup saw 1" in out
          and not os.path.exists(os.path.join(ws, "relay", "state")))
    sites, step = jobs.failure_sites([l[len("RELAY:"):].strip()
                                      for l in said])
    check("and the Mac reads the file and line back out of it",
          m is not None and sites == ["scripts/fit.py:%s" % m.group(1)]
          and step == "")

    code, out = run(ws, "mirror.sbatch", """#!/bin/bash
%s
%s -m scripts.mirror
""" % (SOURCE, PY), dict(env, RESULTS_DIR=os.path.join(
        art, "ID0003AB", "google_medgemma-27b-text-it")))
    said = relay_out(out)
    check("in the workspace: a published output by name, an untracked stray "
          "as a placeholder; a RESULTS_DIR moved into a per-patient tree "
          "names nothing of it",
          code == 1 and "RELAY: error KeyError at scripts/mirror.py:9 in main"
          in said
          and "RELAY: input results/cross_embedder_retrieval/"
          "lr_dimensions_vs_best_k.png bytes 3" in said
          and "RELAY: input results/<file> ext csv" in said
          and "RELAY: input RESULTS_DIR/<file> ext json" in said
          and clean_lines(said))

    code, out = run(ws, "two.sbatch", """#!/bin/bash
%s
one() { echo "one saw $?"; true; }
two() { echo "two saw $?"; }
relay_on_exit one
relay_on_exit two
exit 7
""" % SOURCE)
    check("every cleanup sees the job's status, not the cleanup before it",
          code == 7 and "one saw 7" in out and "two saw 7" in out)
    code, out = run(ws, "fine.sbatch", """#!/bin/bash
%s
done_() { echo "cleanup saw $?"; }
relay_on_exit done_
false || true
""" % SOURCE)
    check("and a job that succeeds hands its cleanup 0",
          code == 0 and "cleanup saw 0" in out and relay_out(out) == [])

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

    # --- under the relay's wrapper ---------------------------------------------------
    def wrapped(recipe, body, env=None):
        """`bash <wrapper>` as a node runs it: jobs.wrapper around `bash
        <recipe>`, with the fingerprint `submit_recipe` gives it."""
        full = os.path.join(ws, "slurm_jobs", recipe)
        write(full, body)
        sdir = os.path.join(ws, "relay", "state")
        os.makedirs(sdir, exist_ok=True)
        exitfile = os.path.join(sdir, recipe.replace(".", "-") + ".exit")
        script = exitfile[:-len(".exit")] + ".sbatch"
        write(script, jobs.wrapper(
            [], ["bash", full], exitfile,
            fp=jobs.fingerprint(ws, "slurm_jobs/" + recipe)))
        code, out = run(ws, "", None, env, path=script)
        with open(exitfile) as fh:
            return code, out, fh.read().strip()

    code, out, wrote = wrapped("bare.sbatch", """#!/bin/bash
%s -m scripts.fit
""" % PY, env)
    said = relay_out(out)
    check("wrapped, a recipe with no source line still fingerprints: the "
          "Python's failure, named off RELAY_CONFIG",
          code == 1 and wrote == "1"
          and any(re.match(r"RELAY: error FileNotFoundError at "
                           r"scripts/fit\.py:\d+ in main$", l) for l in said)
          and "RELAY: step scripts.fit, recipe slurm_jobs/bare.sbatch" in said
          and "RELAY: missing RESULTS_DIR/trained_models/<file> ext joblib"
          in said and clean_lines(said))
    check("and the wrapper's failure line, with the checkout",
          said[-1:] == ["RELAY: recipe slurm_jobs/bare.sbatch failed: exit 1, "
                        "checkout %s" % sha])
    code, out, wrote = wrapped("stopped.sbatch", """#!/bin/bash
set -e
%s
set -u
echo one
false
echo never
""" % SOURCE)
    said = relay_out(out)
    check("wrapped, a recipe that sources the trap says the line it stopped "
          "after, and the failure line comes once, from the wrapper",
          code == 1 and wrote == "1" and said == [
              "RELAY: recipe slurm_jobs/stopped.sbatch stopped after line 6",
              "RELAY: recipe slurm_jobs/stopped.sbatch failed: exit 1, "
              "checkout %s" % sha]
          and jobs.failure_sites([l[7:] for l in said]) == ([], "6"))
    code, out, wrote = wrapped("fine.sbatch", """#!/bin/bash
%s
echo fine
""" % SOURCE)
    check("and a wrapped job that succeeds prints no RELAY: line",
          code == 0 and wrote == "0" and relay_out(out) == [])
    check("a request may not set a RELAY_ variable, whatever a recipe "
          "declares", jobs.declarations(
              "#!/bin/bash\n#RELAY-VAR RELAY_CONFIG .*\n")[0] == {})

    # --- the probe: the real diagnose.sbatch, module and conda stubbed --------------
    shim = os.path.join(base, "shim")
    os.makedirs(shim)
    os.symlink(PY, os.path.join(shim, "python"))
    probe_env = {"PATH": shim + os.pathsep + os.environ.get("PATH", ""),
                 "SLURM_SUBMIT_DIR": ws,
                 "BASH_FUNC_module%%": "() { :; }",
                 "BASH_FUNC_conda%%": "() { echo :; }"}
    for k in env:
        probe_env[k] = ""

    def diagnose(**extra):
        code, out = run(ws, "", None, dict(probe_env, **extra),
                        path=os.path.join(ws, "slurm_jobs", "quick_runs",
                                          "diagnose.sbatch"))
        return code, relay_out(out)

    code, said = diagnose()
    PROBE = said
    check("the probe: the checkout, which keys are set, by kind",
          code == 0 and said[0] == "RELAY: probe checkout %s, recipe "
          "slurm_jobs/quick_runs/diagnose.sbatch" % sha
          and any(l.startswith("RELAY: env dir:") and "PATIENT_JSON_DIR" in l
                  for l in said)
          and any(l.startswith("RELAY: env unset:") for l in said))
    check("published outputs by name, with counts",
          "RELAY: has RESULTS_DIR/cross_embedder_retrieval/"
          "cross_embedder_retrieval.csv rows 2" in said
          and "RELAY: has RESULTS_DIR/neighbor_count_sweep entries 2" in said
          and "RELAY: has RESULTS_DIR/neighbor_count_sweep/best_k_panels "
          "entries 1" in said)
    check("the rest of a directory as counts by extension: bare-id, - and _ "
          "ids, short ids, a 50-file per-entity directory, a file inside an "
          "unnamed directory",
          "RELAY: has RESULTS_DIR/<file> x2: csv 1, json 1" in said
          and "RELAY: has RESULTS_DIR/<dir> x3: files 52 (json 1, txt 51), "
          "dirs 0" in said
          and "RELAY: has RESULTS_DIR/neighbor_count_sweep/<file> x1: json 1"
          in said
          and "RELAY: has RESULTS_DIR/trained_models/<file> x1: joblib 1"
          in said)
    check("and none of it names an id, a location, or fails the scrub",
          clean_lines(said))

    code, said = diagnose(LOOK="RESULTS_DIR/neighbor_count_sweep/")
    check("LOOK with a trailing slash lists that directory, three levels",
          code == 0 and "RELAY: has RESULTS_DIR/neighbor_count_sweep/"
          "best_k_panels entries 1" in said
          and "RELAY: has RESULTS_DIR/neighbor_count_sweep/best_k_panels/"
          "<file> x1: png 1" in said and clean_lines(said))
    code, said = diagnose(LOOK="RESULTS_DIR/./trained_models")
    check("LOOK normalises `.`, and an id-named file in a named directory "
          "is a count", code == 0
          and "RELAY: has RESULTS_DIR/trained_models/<file> x1: joblib 1"
          in said and clean_lines(said))
    refused = []
    for look in ("RESULTS_DIR/per_entity", "RESULTS_DIR/synthetic-alpha-17",
                 "RESULTS_DIR/zuvo/", "RESULTS_DIR/../ID0003AB",
                 "PATIENT_JSON_DIR", "ARTIFACTS_DIR/ID0003AB"):
        code, said = diagnose(LOOK=look)
        refused.append(code == 0 and any("refused" in l for l in said)
                       and not any(l.startswith("RELAY: has") for l in said)
                       and clean_lines(said))
    check("LOOK at an unnamed directory, out of a key, or at another key is "
          "refused without echoing it", all(refused))
    code, said = diagnose(EMBEDDER="ID0003AB")
    check("EMBEDDER outside ENCODERS is refused before anything is "
          "listed, and not echoed", code == 12
          and "RELAY: probe EMBEDDER refused: not one of ENCODERS"
          in said and not any(l.startswith("RELAY: has") for l in said)
          and clean_lines(said))
    code, said = diagnose(EMBEDDER="bge-small-en-v1.5 bge-en-icl")
    check("two listed names in one EMBEDDER are refused: a whole word only",
          code == 12 and "RELAY: probe EMBEDDER refused: not one of ENCODERS"
          in said and clean_lines(said))
    code, said = diagnose(EMBEDDER="bge-small-en-v1.5")
    check("a listed EMBEDDER re-derives its directories",
          code == 0 and "RELAY: has RESULTS_DIR/cross_embedder_retrieval/"
          "cross_embedder_retrieval.csv rows 2" in said and clean_lines(said))
    code, said = diagnose(MODULE="scripts.ID0001XQ")
    check("MODULE outside the list is refused, and not echoed",
          code == 12 and "RELAY: probe MODULE refused: not one of DIAGNOSABLE"
          in said and clean_lines(said))
    code, said = diagnose(
        MODULE="scripts.pipeline.predictions.neighbor_count_sweep")
    check("a listed MODULE is looked for, not run",
          code == 0 and "RELAY: module scripts.pipeline.predictions."
          "neighbor_count_sweep missing" in said)
    code, out = run(ws, "bare.sbatch", """#!/bin/bash
%s
%s -m relay_hook --module scripts.fit --look RESULTS_DIR/zuvo
""" % (SOURCE, PY), env)
    said = relay_out(out)
    check("the probe run bare refuses a module no recipe runs, and a LOOK "
          "of an unnamed segment", code == 0
          and "RELAY: module refused: not one a tracked recipe runs" in said
          and "RELAY: look refused: RESULTS_DIR/<dir> names a directory that "
          "is not a published output" in said and clean_lines(said))

    # --- PSYCH-ASR: no file is named at all -----------------------------------------
    pws = workspace(PSY, "psy", ignore="phi/\n")
    write(os.path.join(pws, "phi", "inbox", "ID0005EF_s2.wav"), "RIFF")
    write(os.path.join(pws, "scripts", "join.py"), """import os


def main():
    audio = os.path.join(os.environ["PSYCH_ASR_DATA"], "inbox",
                         "ID0005EF_s2.wav")
    turns = os.path.join("phi", "stage1", "ID0005EF_s2.rttm")
    open(turns)


if __name__ == "__main__":
    main()
""")
    commit(pws)
    code, out = run(pws, "join.sbatch", """#!/bin/bash
set -e
source slurm_jobs/lib/job_env.sh
%s -m scripts.join
""" % PY)
    said = relay_out(out)
    check("PSYCH-ASR: a failure names its location key and extension, no file",
          code == 1 and "RELAY: missing PSYCH_ASR_DATA/<file 2 deep> ext rttm"
          in said and "RELAY: input PSYCH_ASR_DATA/<file 2 deep> ext wav"
          in said and not any("phi/" in l or ".rttm" in l for l in said))
    check("and its lines survive the PHI policy whole", clean_lines(said))
    print()
    print("what the probe printed for the fixture:")
    for line in PROBE:
        print("    " + line)
finally:
    shutil.rmtree(base, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a failed job prints what failed and where, by allowlisted name and "
      "count, and a job that succeeds prints nothing")
