"""IT's model server: a `libr-ai` task, filed on the Mac, run on the cluster.

ai.laureateinstitute.org is Open WebUI over Ollama on IT's DGX Spark. Only
the compute nodes resolve it, so the Mac files a `libr-ai` relay request and
the relay submits it as a Slurm job (`submit`) that runs
`board/scripts/libr-ai-task.sh`: opencode, once, unattended and read-only, in
the subject's directory. The job's log is the model's answer, and the relay's
ordinary job report carries it back, because the subject's phi is false.

The constraint: IT's server keeps every chat. So a request is refused unless
the subject's tutorboard.json says `"phi": false` (`jobs.validate`), the relay
refuses again unless its output may be published (`code.output_open`), and
the task script refuses a fenced directory through ai-config's policy. A PHI
subject uses Colibri, which runs on our own hardware.
"""

import os
import time

from . import jobs

# What `coder` opens on, and what a request names when it names nothing.
MODEL = "gpt-oss:120b"

# The job: no GPU, since the model runs on IT's server, and an hour is far
# more than one answer takes. Its log lands in the subject's ignored
# relay/state/, beside the wrapper.
HEADER = [
    "#SBATCH --job-name=libr-ai",
    "#SBATCH --partition=c3_short",
    "#SBATCH --time=01:00:00",
    "#SBATCH --ntasks=1",
    "#SBATCH --cpus-per-task=2",
    "#SBATCH --mem=4G",
    "#SBATCH --output=relay/state/libr-ai-%j.out",
    "#SBATCH --error=relay/state/libr-ai-%j.err",
]

TASK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))), "scripts", "libr-ai-task.sh")


def ask(root, brief, label="", session="", model="", push=True):
    """The Mac's `board libr-ai`: a `libr-ai` relay request from subject
    `root`, checked, committed and pushed. `{ok, id, said, problems}`."""
    brief = (brief or "").strip()
    if not brief:
        return {"ok": False, "problems": ["say what the task is"]}
    taken = set(r["id"] for r in jobs.requests(root))
    req = {"id": jobs.new_id(label, "libr-ai", taken), "kind": "libr-ai",
           "brief": brief, "filed": round(time.time(), 3)}
    for key, value in (("label", label), ("session", session),
                       ("model", model)):
        if value:
            req[key] = value
    ok, problems = jobs.check(root, req)
    if problems:
        return {"ok": False, "problems": list(problems)}
    hidden = jobs.request_visible(root)
    if hidden:
        return {"ok": False, "problems": [hidden]}
    changed = jobs.dirty(root)
    if changed:
        return {"ok": False, "problems": [jobs.dirty_said(root, changed)]}
    path, done, said = jobs.file_request(root, ok, push=push)
    if not done:
        return {"ok": False, "id": ok["id"], "problems": [
            "the request is written at %s but did not reach the cluster: %s"
            % (os.path.relpath(path, root), said)]}
    return {"ok": True, "id": ok["id"], "problems": [],
            "said": "request %s filed and pushed; the relay's next pass "
                    "submits it, and the answer comes back as its report"
                    % ok["id"]}


def submit(ws, req, run, now, sbatch_env, ran_at):
    """The relay's half: write the brief beside the wrapper, in the subject's
    ignored relay/state/, and submit the task script. `(record, why)`."""
    sdir = jobs.state_dir(ws)
    os.makedirs(sdir, exist_ok=True)
    brief = os.path.join(sdir, req["id"] + ".brief")
    with open(brief, "w", encoding="utf-8") as fh:
        fh.write(req["brief"])
    model = req.get("model") or MODEL
    return jobs.submit_script(
        ws, req.get("label"), HEADER, ["bash", TASK, ws, brief, model],
        req["id"], "libr-ai %s: %s" % (model, req["brief"][:100]),
        run=run, now=now, sbatch_env=sbatch_env,
        extra={"request": req["id"], "kind": "libr-ai", "ran_at": ran_at})
