"""The project's job environment refuses missing data roots."""
import os
import json
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
check("the job environment loads the shared trap",
      'source "$_JOB_ENV_LIB/relay_trap.sh"' in open(os.path.join(LIB, "job_env.sh")).read())
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
