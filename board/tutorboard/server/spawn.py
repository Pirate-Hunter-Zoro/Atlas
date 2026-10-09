"""Running the board's own commands, from inside the board.

A route that runs `board ...` or asks `tutor --agents` shells out here, so
there is one implementation rather than two that drift. Turns are not started
here: the runner (`runner/service.py`) takes them.
"""

import os
import subprocess
import sys

from .. import paths


# A SERVER HAS NO STANDARD INPUT, AND A CHILD THAT INHERITS ONE THAT IS CLOSED
# DOES NOT RUN AT ALL.
#
# Both helpers below inherited this process's stdin. A board started by launchd,
# or detached by `board start`, has fd 0 closed -- so the python3 they spawn
# dies before it reaches its first line, with:
#
#     Fatal Python error: init_sys_streams: can't initialize sys standard streams
#     OSError: [Errno 9] Bad file descriptor
#
# which is what a board started by a supervisor recorded when it was asked to
# hand its tutor over: the answer it got back was an interpreter crash where a
# wrap-up should have been. Every route that runs a command goes through these
# two functions, so on such a machine none of them could do anything -- and
# each returned a plausible non-zero and was reported as an ordinary failure.
_NO_STDIN = subprocess.DEVNULL


def board_cli(repo, args, timeout=90, given=None, session=None):
    """Drive the board command line from inside the server, for /switch.

    `repo` is the directory it runs in. `session` is the session directory
    it works on (`TUTORBOARD_SESSION`); a route serving a stored session
    passes its own, so the command never reaches another.

    `given` is text for its stdin (`board thread add` reads the thread there);
    without it stdin is closed, for the reason `_NO_STDIN` gives.
    """
    cli = os.path.join(paths.TOOL, "bin", "board")
    env = None
    if session:
        env = dict(os.environ, TUTORBOARD_SESSION=session)
    try:
        p = subprocess.run([sys.executable, cli] + list(args),
                           stdin=_NO_STDIN if given is None else None,
                           input=None if given is None else given.encode("utf-8"),
                           cwd=repo, stdout=subprocess.PIPE, env=env,
                           stderr=subprocess.STDOUT, timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def tutor_cli(args, timeout=30):
    """Drive the launcher from inside the server: `tutor --agents --json`,
    and the old workspace routes until their deletion."""
    cli = os.path.join(paths.TOOL, "bin", "tutor")
    try:
        p = subprocess.run([sys.executable, cli] + list(args),
                           cwd=paths.TOOL, stdin=_NO_STDIN,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
