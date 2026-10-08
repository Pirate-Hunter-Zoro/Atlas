"""The Mac's git sync: a workspace caught up before a session, and the hear pull.

`sync` fast-forwards one repository and never fatally. `hear_pass` pulls Atlas
when it is due, then hears every workspace's cluster reports. T10 folds this
into gitops.
"""

import os
import subprocess
import time

from tutorboard import atlas, jobs, worktree


def sync(root, quiet=False, timeout=60, say=None):
    """Pull whatever another machine pushed, before the session starts.

    The point of the handoff is that a course can be picked up somewhere else,
    and a handoff written on the machine you left is worth nothing to the one
    you arrive on until it is fetched. So every session begins by catching up.

    Fast-forward only, and never fatal. A session that will not start because a
    branch diverged is worse than a session that starts a commit behind and says
    so -- the person is holding an iPad and cannot fix a merge from there.

    And it does not touch a repository somebody is part-way through an operation
    in. A course is somewhere its owner works, not only somewhere they are
    taught; a fast-forward arriving in the middle of their rebase is the tutor
    reaching into a terminal it knows nothing about.

    `timeout` bounds the pull, the one step that waits on a network. `say`,
    where given, hears every line `quiet` would otherwise drop.
    """
    def tell(msg):
        if say is not None:
            say(msg.strip())
        elif not quiet:
            print(msg)
    if not worktree.git_dir(root):
        return None
    busy = worktree.busy_reason(root)
    if busy:
        tell("  not synced: %s here, so the repository is left exactly as it is"
             % busy)
        return False
    # A pull needs the index too, so a lock a killed git left behind stops a
    # session opening up to date just as surely as it stops a commit. Rubbish
    # goes out here as well; a lock somebody is holding is left, and the pull
    # below fails and says so in the usual way.
    cleared = worktree.clear_stale_lock(root)
    if cleared:
        tell("  " + cleared)
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="/bin/false")
    def git(*args, **kw):
        return subprocess.run(["git"] + list(args), cwd=root, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=kw.get("timeout", 45))
    try:
        if git("remote", "get-url", "origin").returncode != 0:
            return None
        before = git("rev-parse", "HEAD").stdout.decode().strip()
        # Fast-forward only: git refuses, moving nothing, where an edit here
        # is a file the pull would change.
        p = git("pull", "--ff-only", timeout=timeout)
        after = git("rev-parse", "HEAD").stdout.decode().strip()
    except (OSError, subprocess.TimeoutExpired):
        tell("  could not reach the remote; working with what is here")
        return False
    if p.returncode != 0:
        out = p.stdout.decode("utf-8", "replace").strip().splitlines()
        tell("  not synced: %s" % (out[-1] if out else "pull failed"))
        if say is None:
            tell("  the session will start anyway, on what is here")
        return False
    if before != after:
        n = git("rev-list", "--count", "%s..%s" % (before, after)).stdout.decode().strip()
        tell("  pulled %s commit(s) from another machine" % n)
    return True

# THE MAC'S EAR. On a machine without Slurm the cluster's reports arrive by
# pull, every `jobs.PULL_EVERY` seconds in every state. The timer runs `tutor
# pull --hear` every twenty seconds and this decides; every run then hears
# every workspace (`[job]` for a request's report, `[coach]` for a held step's
# check), because a hand pull may have moved HEAD in between.
HEAR_STAMP = os.path.join(os.path.expanduser("~"), ".local", "state",
                          "tutor-pull.heard")


# ai-config is the one private repository nested inside Atlas and ignored by it.
# Courses and projects are Atlas's own tracked content, so nothing else is ever
# cloned here; bootstrap.sh carries the same URL.
AI_CONFIG = "ai-config"
AI_CONFIG_URL = "https://github.com/Pirate-Hunter-Zoro/ai-config.git"


def adopt_private(base, quiet=True, run=subprocess.run):
    """Clone or adopt ai-config when this checkout lacks its repository,
    through `bootstrap.sh --private-only`. True if it ran.

    The only clone a pull pass ever attempts: every course and project is
    tracked by Atlas itself.
    """
    if os.path.exists(os.path.join(base, AI_CONFIG, ".git")):
        return False
    script = os.path.join(base, "board", "bootstrap.sh")
    if not os.path.isfile(script):
        return False
    try:
        p = run(["bash", script, "--private-only"], cwd=base,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, timeout=600,
                env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    except (OSError, subprocess.SubprocessError):
        return False
    if not quiet:
        print((p.stdout or "").rstrip())
    return True


def hear_pass(base=None, stamp=None, now=None, force=False, quiet=True,
              pull=None):
    """Pull Atlas when due, then hear every workspace's reports.

    `(pulled, interval, heard)`: `pulled` is None where nothing was pulled
    because the relay owns pulls here (Slurm), True where the pull ran, False
    where it was not due or failed. Never raises.
    """
    if jobs.has_slurm():
        return None, 0, []
    stamp = stamp or HEAR_STAMP
    now = time.time() if now is None else float(now)
    try:
        base = base or atlas.root()
        roots = [w["root"] for w in atlas.workspaces(base)]
    except Exception:                                        # noqa: BLE001
        return False, 0, []
    from tutorboard import holds

    interval = jobs.PULL_EVERY
    try:
        with open(stamp, "r", encoding="utf-8") as fh:
            last = float(fh.read().strip() or 0)
    except (OSError, ValueError):
        last = 0
    pulled = False
    if force or jobs.pull_due(last, now, interval):
        # ONE PULL: every course and project is Atlas's own content. ai-config
        # is adopted first when it is missing, and nothing else is cloned.
        adopt_private(base, quiet=quiet)
        try:
            pulled = (pull or sync)(base, quiet=quiet) is True
        except Exception:                                    # noqa: BLE001
            pulled = False
        try:
            os.makedirs(os.path.dirname(stamp), exist_ok=True)
            with open(stamp, "w", encoding="utf-8") as fh:
                fh.write("%f\n" % now)
        except OSError:
            pass
    heard = []
    for root in roots:
        for rec in jobs.hear(root, now=now):
            heard.append(dict(rec, workspace=atlas.identify(root) or root))
        try:
            woke = holds.wake(root, now=now)
        except Exception:                                    # noqa: BLE001
            woke = []
        for rep in woke:
            heard.append({"request": rep.get("id"), "state": "coach",
                          "thread": rep.get("thread"),
                          "workspace": atlas.identify(root) or root})
    return pulled, interval, heard
