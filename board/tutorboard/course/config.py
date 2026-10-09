"""What a subject's `tutorboard.json` says, and a session's mode.
"""

import json
import os
import re
import shlex


# A session's MODE, in `session.json`: who writes the code. `teach` withholds
# it; `do` writes it. A session opens in teach and changes only by `board mode`,
# `POST /mode`, or the tutor obeying "do it". Nothing infers `do`.
MODES = ("teach", "do")


def clean_mode(mode):
    """A mode from a request, or None if it is not one. Never raises."""
    mode = str(mode or "").strip().lower()
    return mode if mode in MODES else None


def mode_of(state):
    """The session's mode: `do` only where `session.json` says so, else teach."""
    return "do" if clean_mode((state or {}).get("mode")) == "do" else "teach"


def read_config(root):
    """What a subject's `tutorboard.json` says: `name`, `phi`, `check`, `relay`.

    Everything is optional. `stance`, `aim`, `subtitle` and `mode` left in a
    file are ignored, and so is `agent`: who takes a turn is the machine's
    one provider setting (`recipes.resolve`). `name` defaults
    to the directory name with dashes as spaces. `phi` stays literal -- True or
    False exactly as written, None for anything else -- because only a literal
    False opens check output (`code.output_open`, which also wants False at
    HEAD, no fence and the policy loaded). `relay` is the file's object, else
    {}. `check` is validated by `clean_check`; `check_problems` and
    `check_line` are derived from it.
    """
    try:
        with open(os.path.join(root, "tutorboard.json"), "r", encoding="utf-8") as fh:
            said = json.load(fh) or {}
    except (OSError, ValueError):
        said = {}
    if not isinstance(said, dict):
        said = {}
    phi = said.get("phi")
    relay = said.get("relay")
    cfg = {
        "name": said.get("name")
        or os.path.basename(os.path.abspath(root)).replace("-", " "),
        "phi": phi if isinstance(phi, bool) else None,
        "relay": relay if isinstance(relay, dict) else {},
    }
    cfg["check"], cfg["check_problems"] = clean_check(said.get("check"))
    cfg["check_line"] = check_line(cfg["check"])
    return cfg


# ---------------------------------------------------------------------------
# a workspace's CHECK: what `board check` and each `board code` step run
# ---------------------------------------------------------------------------
#
#     "check": "uv run --extra test python -m pytest tests -q"
#
# A string is one shell command for the whole workspace: it runs as `bash -c`
# and has no placeholders. The object form says the same without a shell, and
# can also check only what is held:
#
#     "check": {"all": ["go", "test", "./..."],
#               "one": ["go", "test", "./{dir}/..."],
#               "path": ["/usr/local/go/bin"]}
#
# `all` checks the whole workspace and `one` checks the held paths, through the
# placeholders `{dir}`, `{file}` and `{module}` (`code.check_spec` fills them).
# `argv[0]` is one of `CHECK_PROGRAMS` or a workspace script, which the check
# requires tracked and unchanged at HEAD. It runs without a shell, with `path`
# put in front of PATH.
CHECK_PROGRAMS = ("go", "lake", "uv", "python3", "bash", "make")
CHECK_HOLES = ("{dir}", "{file}", "{module}")
_HOLE_RE = re.compile(r"\{[^}]*\}")


def check_program(word):
    """Is this an allowed `argv[0]`: a named program, or a workspace script?

    A script is a workspace path with a directory or an extension in it, so a
    bare program name that is not one of `CHECK_PROGRAMS` is refused rather
    than read as a file nobody wrote."""
    word = str(word or "")
    if word in CHECK_PROGRAMS:
        return True
    rel = word.replace("\\", "/")
    return (bool(rel) and not rel.startswith(("/", "~", "-"))
            and ".." not in rel.split("/") and "{" not in rel
            and ("/" in rel or "." in os.path.basename(rel)))


def _leaves(word):
    """Does this word of a check name a path outside the workspace? An
    absolute or home path, or a `..` step, anywhere in it: after `--opt=`,
    or inside a `bash -c` line. A check runs from the workspace root, and its
    output is judged by that workspace's fence, so it may not reach into
    another one."""
    for part in _WORD_SPLIT.split(str(word).replace("\\", "/")):
        if part.startswith(("/", "~", "$")) or ".." in part.split("/"):
            return True
    return False


_WORD_SPLIT = re.compile(r"[\s;&|()<>'\"=`:,]+")


def check_line(chk):
    """The workspace check as one command line, for the brief. "" if none."""
    if not chk:
        return ""
    if chk.get("line"):
        return chk["line"]
    return " ".join(chk.get("all") or chk.get("one") or [])


def clean_check(raw):
    """`(check, problems)` for a `tutorboard.json` `check`. None if absent."""
    if raw is None or raw == "":
        return None, []
    if isinstance(raw, str):
        line = raw.strip()
        if not line or _HOLE_RE.search(line):
            return None, ["`check`, as a string, is one shell command with no "
                          "placeholders; `{dir}`, `{file}` and `{module}` need "
                          "the object form"]
        try:
            words = shlex.split(line)
        except ValueError:
            return None, ["`check` is not a command a shell can read"]
        out = [w for w in words if _leaves(w)]
        if out:
            return None, ["`check` names %s, outside the workspace"
                          % ", ".join(out[:3])]
        return {"all": ["bash", "-c", line], "line": line}, []
    if not isinstance(raw, dict):
        return None, ["`check` must be a shell command, or an object with "
                      "`all` and/or `one`"]
    out, problems = {}, []
    for key in ("all", "one"):
        argv = raw.get(key)
        if argv is None:
            continue
        if (not isinstance(argv, list) or not argv
                or not all(isinstance(w, str) and w for w in argv)):
            problems.append("`check.%s` must be a list of words" % key)
            continue
        if not check_program(argv[0]):
            problems.append("`check.%s` starts with %r, which is neither one of "
                            "%s nor a workspace script"
                            % (key, argv[0], ", ".join(CHECK_PROGRAMS)))
            continue
        out_of = [w for w in argv if _leaves(w)]
        if out_of:
            problems.append("`check.%s` names %s, outside the workspace"
                            % (key, ", ".join(out_of[:3])))
            continue
        holes = [x for w in argv for x in _HOLE_RE.findall(w)]
        wrong = [x for x in holes if x not in CHECK_HOLES or key == "all"]
        if wrong:
            problems.append("`check.%s` has %s; only `one` may hold one, and "
                            "only %s" % (key, ", ".join(sorted(set(wrong))),
                                         ", ".join(CHECK_HOLES)))
            continue
        out[key] = list(argv)
    path = raw.get("path")
    if path is not None:
        if (not isinstance(path, list)
                or not all(isinstance(d, str) and os.path.isabs(d) for d in path)):
            problems.append("`check.path` must be a list of absolute directories")
        else:
            out["path"] = list(path)
    if not (out.get("all") or out.get("one")):
        return None, problems or ["`check` names neither `all` nor `one`"]
    return out, problems


# ---------------------------------------------------------------------------
# An assistant's NAME from a request: only its shape is checked here. Who takes
# a turn is the machine's one provider setting (`recipes.resolve`).
# ---------------------------------------------------------------------------
AGENT_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,31}$")


def clean_agent(agent):
    """An assistant name from a request, or None if it is not one. Never raises."""
    agent = str(agent or "").strip().lower()
    return agent if AGENT_RE.match(agent) else None
