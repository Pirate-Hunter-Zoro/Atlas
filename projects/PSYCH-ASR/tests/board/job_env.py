"""The project's job environment refuses missing data roots, gives each grid run its own
Stage 1 directory, and every recipe parses."""
import os
import json
import re
import shutil
import subprocess
import sys
import tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
SUBJECT = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(SUBJECT))
LIB = os.path.join(SUBJECT, "slurm_jobs", "lib")
BASH = "/bin/bash"
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        print(detail)
def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
with open(os.path.join(SUBJECT, "tutorboard.json")) as fh:
    config = json.load(fh)
fingerprint = config["relay"]["fingerprint"]
check("the subject publishes no data filenames",
      fingerprint["names"] is False and fingerprint["open_keys"] == []
      and "PSYCH_ASR_DATA" in fingerprint["path_keys"])
recipes = [name for name in os.listdir(os.path.join(SUBJECT, "slurm_jobs"))
           if name.endswith(".sbatch")]
check("every recipe loads the guarded job environment", bool(recipes) and all(
    "source slurm_jobs/lib/job_env.sh" in open(os.path.join(SUBJECT, "slurm_jobs", name)).read()
    for name in recipes))
activate = re.search(r"^activate_env\(\) \{\n(.*?)^\}",
                     open(os.path.join(LIB, "job_env.sh")).read(), re.S | re.M)
check("activate_env turns off pyannote telemetry",
      activate is not None and re.search(r"^\s*export PYANNOTE_METRICS_ENABLED=0\s*$",
                                         activate.group(1), re.M) is not None)
check("the job environment loads the shared trap",
      'source "$_JOB_ENV_LIB/relay_trap.sh"' in open(os.path.join(LIB, "job_env.sh")).read())
# Stage 1's directory comes from job_env.sh alone, which knows the grid run it is in.
assigning = [(name, line.strip()) for name in recipes
             for line in open(os.path.join(SUBJECT, "slurm_jobs", name))
             if re.match(r"\s*STAGE1_DIR=", line)]
check("every recipe that names STAGE1_DIR takes it from PSYCH_ASR_STAGE1_DIR",
      all("PSYCH_ASR_STAGE1_DIR" in line for _, line in assigning), assigning)
for name in ("stage1_grid.sbatch", "stage1c_join_grid.sbatch", "preflight_models.sbatch"):
    check("the grid recipe %s exists" % name, name in recipes)
# The relay reads `#RELAY-VAR NAME PATTERN` from the header, up to the first line that
# is neither blank nor a comment -- a copy of board/tutorboard/jobs.py's own rule.
VAR_LINE_RE = re.compile(r"^#RELAY-VAR\s+(\S+)\s+(\S.*?)\s*$")
declared = {}
for line in open(os.path.join(SUBJECT, "slurm_jobs", "stage1_grid.sbatch")):
    s = line.strip()
    if s and not s.startswith("#"):
        break
    m = VAR_LINE_RE.match(s)
    if m:
        declared[m.group(1)] = m.group(2)
check("the grid recipe declares exactly its five variables",
      sorted(declared) == ["GRID_DRY_RUN", "GRID_REJOIN", "GRID_STOPWATCHES",
                           "GRID_TAGGERS", "GRID_TYPISTS"], sorted(declared))
check("its axis variables take colon lists and nothing else",
      re.fullmatch(declared.get("GRID_TYPISTS", "x"), "parakeet:canary") is not None
      and re.fullmatch(declared.get("GRID_TYPISTS", "x"), "a/b") is None
      and re.fullmatch(declared.get("GRID_REJOIN", "x"), "12345") is not None)
shell = sorted(os.path.join("slurm_jobs", n) for n in os.listdir(os.path.join(SUBJECT, "slurm_jobs"))
               if n.endswith((".sbatch", ".sh")))
shell += [os.path.join("slurm_jobs", "lib", "job_env.sh"), os.path.join("scripts", "stage_models.sh")]
unparsed = [n for n in shell
            if subprocess.run([BASH, "-n", os.path.join(SUBJECT, n)], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).returncode != 0]
check("every recipe and script parses", not unparsed, unparsed)
base = tempfile.mkdtemp(prefix="jobenv-")
try:
    # --- job_env.sh: a missing data root stops the job ------------------------
    # Atlas-shaped: the subject's relay_trap.sh is a shim sourcing the shared
    # one four levels up, in board/cluster/lib.
    ws = os.path.join(base, "projects", "ws")
    shutil.copytree(LIB, os.path.join(ws, "slurm_jobs", "lib"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(ROOT, "board", "cluster", "lib"),
                    os.path.join(base, "board", "cluster", "lib"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    recipe = os.path.join(ws, "slurm_jobs", "job.sbatch")
    put(recipe, "#!/bin/bash\nset -e\nsource slurm_jobs/lib/job_env.sh\n"
                "echo reached\n")

    def job(extra=None):
        e = dict(os.environ)
        e.pop("PSYCH_ASR_DATA", None)
        e.update(extra or {})
        return subprocess.run([BASH, recipe], cwd=ws, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, env=e)

    p = job()
    check("job_env.sh stops a job whose phi/ is missing",
          p.returncode != 0 and "reached" not in p.stdout
          and "RELAY: data root PSYCH_ASR_DATA does not exist" in p.stderr, p.stderr)
    check("and does not create it", not os.path.exists(os.path.join(ws, "phi")))
    check("its RELAY: line names no path",
          not any(l.startswith("RELAY:") and (base in l or os.path.realpath(base) in l)
                  for l in p.stderr.splitlines()),
          p.stderr)
    gone = os.path.join(base, "elsewhere", "data-root")
    p = job({"PSYCH_ASR_DATA": gone})
    check("an override pointing nowhere stops the job too, creating nothing",
          p.returncode != 0 and "reached" not in p.stdout
          and not os.path.exists(os.path.join(base, "elsewhere")), p.stderr)
    os.makedirs(os.path.join(ws, "phi"))
    p = job()
    check("with the data root present the job runs on",
          p.returncode == 0 and "reached" in p.stdout, p.stderr)
    # --- job_env.sh: each grid run writes into its own directory ---------------
    put(recipe, '#!/bin/bash\nset -e\nsource slurm_jobs/lib/job_env.sh\n'
                'echo "dir=${PSYCH_ASR_STAGE1_DIR#"$PSYCH_ASR_DATA"}"\n'
                'echo "same=$([ "$STAGE1_DIR" = "$PSYCH_ASR_STAGE1_DIR" ] && echo yes)"\n')
    p = job({"PSYCH_ASR_GRID": "t"})
    check("a grid child's Stage 1 directory is stage1/grid-<id>",
          p.returncode == 0 and "dir=/stage1/grid-t" in p.stdout and "same=yes" in p.stdout,
          p.stdout + p.stderr)
    p = job()
    check("without a grid id it is stage1 itself",
          p.returncode == 0 and "dir=/stage1\n" in p.stdout, p.stdout + p.stderr)
    for bad in ("a/b", "..", "../x"):
        p = job({"PSYCH_ASR_GRID": bad})
        check("a grid id %r stops the job" % bad,
              p.returncode != 0 and "dir=" not in p.stdout
              and "RELAY: grid id refused" in p.stderr, p.stdout + p.stderr)
    check("and nothing was created for it", not os.path.exists(os.path.join(ws, "phi", "stage1")))
    shutil.copy(os.path.join(SUBJECT, "tutorboard.json"), ws)
    put(os.path.join(ws, ".gitignore"), "phi/\n__pycache__/\n")
    put(os.path.join(ws, "scripts", "__init__.py"), "")
    put(os.path.join(ws, "phi", "inbox", "synthetic.wav"), "RIFF")
    put(os.path.join(ws, "scripts", "join.py"),
        'import os\n'
        'audio = os.path.join(os.environ["PSYCH_ASR_DATA"], "inbox", "synthetic.wav")\n'
        'open(os.path.join("phi", "stage1", "synthetic.rttm"))\n')
    for args in (["init", "-q"], ["add", "."],
                 ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "fixture"]):
        subprocess.run(["git", "-C", ws] + args, check=True)
    put(recipe, '#!/bin/bash\nset -e\nsource slurm_jobs/lib/job_env.sh\n"%s" -m scripts.join\n' % sys.executable)
    p = job()
    lines = [line for line in (p.stdout + p.stderr).splitlines() if line.startswith("RELAY:")]
    check("a failure names only the location key and extension",
          p.returncode == 1
          and "RELAY: missing PSYCH_ASR_DATA/<file 2 deep> ext rttm" in lines
          and "RELAY: input PSYCH_ASR_DATA/<file 2 deep> ext wav" in lines
          and not any("synthetic" in line or "phi/" in line for line in lines), lines)
finally:
    shutil.rmtree(base, ignore_errors=True)
sys.exit(1 if fails else 0)
