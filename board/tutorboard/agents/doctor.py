"""`tutor doctor`: one built-in recipe, proved against its live provider."""

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

from tutorboard import keys, seeing
from tutorboard.agents import recipes, usage
from tutorboard.course import config
from tutorboard.net import egress
from tutorboard.runner import turn as runturn
from tutorboard.course import repo as course_repo

DOCTOR_TURN_SECONDS = 600

# The workspace check the coding turn has to pass. `%(want)d` is the answer,
# written in by `cmd_doctor`, so the check is a fact about the run.
DOCTOR_CHECK = '''import os, subprocess, sys
want = "%(want)d"
if not os.path.isfile("sum.py"):
    sys.exit("FAIL: no sum.py")
got = subprocess.run([sys.executable, "sum.py"], capture_output=True,
                     text=True).stdout.strip()
if got != want:
    sys.exit("FAIL: sum.py printed %%r, not %%s" %% (got, want))
if not os.path.isfile("out.txt") or open("out.txt").read().strip() != want:
    sys.exit("FAIL: out.txt does not hold %%s" %% want)
print("PASS")
'''

DOCTOR_TEXT_PROMPT = (
    "This is a check of the tutoring harness, run by `tutor doctor`. Do exactly "
    "this and nothing else. Write a file live/cards/001.md holding one short "
    "sentence that greets the student. Also remember this code word for later in "
    "this conversation: %(secret)s. Do not write the code word to any file and "
    "do not repeat it in your reply. Then stop."
)
DOCTOR_RESUME_PROMPT = (
    "Same conversation, next turn. What code word did I ask you to remember in "
    "my previous message? Answer from memory, in one line. Do not read any file "
    "or run any command to find it."
)
DOCTOR_CODE_PROMPT = (
    "This is a check of the coding tools, run by `tutor doctor`. Do the work; "
    "do not explain it.\n"
    "1. Create a file sum.py that prints the sum of the integers from 1 to 10.\n"
    "2. Run `python3 sum.py` in the shell.\n"
    "3. With your edit tool, change the 10 in sum.py to %(n)d. Edit the "
    "existing file; do not rewrite it.\n"
    "4. Run `python3 sum.py > out.txt` in the shell.\n"
    "5. Run `python3 check.py` in the shell, and stop when it prints PASS."
)
DOCTOR_IMAGE_PROMPT = (
    "This is a check of image reading, run by `tutor doctor`. There is an image "
    "file, slate.png, in this directory. Open it with your own file-reading "
    "tool and look at it. Write the six digits printed on it, and nothing else, "
    "into seen.txt. Use only your file-reading and file-writing tools: run no "
    "shell command and ask no other service. If you cannot see the image, "
    "write CANNOT into seen.txt instead: never guess."
)
DOCTOR_SEE_PROMPT = ("What six-digit number is printed on the second image? "
                     "Answer with the digits only.")

# The names a harness gives its file-changing and shell tools, as reported in
# OpenCode's `tool_use` events.
EDIT_TOOLS = ("edit", "multiedit", "patch", "apply_patch")
WRITE_TOOLS = ("write",) + EDIT_TOOLS
SHELL_TOOLS = ("bash", "shell")


def doctor_asked(spec):
    """`(harness, model)` a recipe's turns ASK for: argv[0] and its `-m`."""
    argv = list(spec.get("headless_first") or spec.get("headless") or [])
    model = None
    for flag in ("-m", "--model"):
        if flag in argv and argv.index(flag) + 1 < len(argv):
            model = argv[argv.index(flag) + 1]
    return os.path.basename((argv or spec.get("cmd") or ["?"])[0]), model


def doctor_route(spec):
    """What a recipe asks for, as one phrase. A claim, not a measurement."""
    harness, model = doctor_asked(spec)
    host = recipes.probe_host(recipes.agent_probe_urls(spec) or [])
    return "%s%s%s" % (harness, " -m %s" % model if model else "",
                       " -> %s" % host if host else "")


def turn_session(said):
    """The conversation id a turn reported, or "" if it reported none.

    OpenCode's events carry `sessionID`, Claude Code's result `session_id`,
    Codex's `thread.started` a `thread_id`. The last one seen wins.
    """
    found = ""
    for line in (said or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if isinstance(d, dict):
            for key in ("sessionID", "session_id", "thread_id"):
                if isinstance(d.get(key), str) and d[key]:
                    found = d[key]
    return found


def session_models(harness, session, root, env=None):
    """`(models, problem)`: every assistant message's `provider/model` in an
    OpenCode session, read from `opencode export` rather than from the argv
    that asked for it. `problem` is a sentence when the export cannot say."""
    try:
        got = subprocess.run([harness, "--pure", "export", session],
                             cwd=root, env=runturn.at_root(root, env),
                             stdin=subprocess.DEVNULL, capture_output=True,
                             text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], "`%s export %s` did not run: %s" % (harness, session, exc)
    out = got.stdout or ""
    try:
        data = json.loads(out[out.index("{"):])
    except ValueError:
        return [], "`%s export %s` gave no session (exit %d)" % (
            harness, session, got.returncode)
    models = []
    for m in data.get("messages") or []:
        info = (m or {}).get("info") or {}
        if info.get("role") == "assistant":
            models.append("%s/%s" % (info.get("providerID"), info.get("modelID")))
    if not models:
        return [], "session %s holds no answer from any model" % session
    return models, None


def doctor_priced(row):
    """A cost row carries a dollar figure: a rate, and `usd` present and a
    number. $0.0 is a price; a missing key is not."""
    usd = row.get("usd")
    return (isinstance(row.get("rate"), dict) and bool(row["rate"])
            and isinstance(usd, (int, float)) and not isinstance(usd, bool))


def doctor_tools(said):
    """The tools a turn used, in order, from OpenCode's events. None if unknown."""
    events = usage.opencode_events(said)
    if not events:
        return None
    return [str((d.get("part") or {}).get("tool") or "")
            for d in events if d.get("type") == "tool_use"]


def cmd_doctor(cfg, args):
    """Prove one BUILT-IN recipe against its live provider, in a scratch workspace.

        tutor doctor              the deepseek recipe
        tutor doctor claude       any other built-in recipe
        tutor doctor --keep       and leave the workspace for reading

    Five checks, one line each. The header names what the recipe asks for;
    each turn's line names what its session recorded (`opencode export`), and
    an answer from any other model fails that check:

      1. a text turn: `headless_first` writes a card and exits 0;
      2. a coding turn: the turn writes a file, edits it, runs it through the
         shell, and the workspace's `check` -- still byte for byte doctor's --
         passes;
      3. a resumed turn: `headless` remembers a word given in turn 1, in a
         session both turns name;
      4. an image, twice: (a) the turn opens a PNG with its own tools; (b) the
         recipe's `vision` route reads one through `seeing.ask`, with the witness
         code drawn in the strip and absent from the prompt. 4b must pass; 4a
         failing means the turn prompts must send images through `board see`;
      5. usage and price: every turn wrote a line to `live/cost.jsonl`, priced
         off the recipe's table when it has one. `tutor cost` on the workspace
         is printed beneath.

    THE BUILT-IN RECIPE, NOT THIS MACHINE'S. A copy in the machine config
    shadows the built-in field by field (`config_shadows`), and a proof of the
    copy says nothing about what the repository ships. The copy is named when
    there is one. Nothing outside the scratch workspace is written: no
    stand-down, no allowance mark, no cost line in a course. Exits 1 on any
    failure, and the workspace is then kept.
    """
    import tempfile
    keep = "--keep" in args
    named = [a for a in args if not a.startswith("-")]
    name = named[0] if named else "deepseek"
    built = recipes.DEFAULT_CONFIG["agents"].get(name)
    if not isinstance(built, dict) or not (built.get("headless")
                                           or built.get("headless_first")):
        print("tutor doctor: there is no built-in headless recipe called '%s'"
              % name, file=sys.stderr)
        return 2
    if recipes.only_bars(cfg, name):
        print("tutor doctor: %s; `tutor agent only --off` before proving '%s'"
              % (recipes.only_bars(cfg, name), name), file=sys.stderr)
        return 2
    spec = json.loads(json.dumps(built))
    first = spec.get("headless_first") or spec.get("headless")
    resume = spec.get("headless") or first
    route = doctor_route(spec)
    harness, want = doctor_asked(spec)
    # WHAT RAN IS READ BACK FROM THE SESSION, not from this argv: an OpenCode
    # turn's session is exported and every answer in it must name `want`.
    confirms = spec.get("usage") == "opencode-json" and bool(want)
    print("tutor doctor: the built-in `%s` recipe, which asks for %s"
          % (name, route))
    shadow = recipes.config_shadows().get(name)
    if shadow:
        print("  %s holds its own copy of `%s` (%s differ). Turns on this "
              "machine run that copy; these checks run the built-in."
              % (recipes.CONFIG, name, ", ".join(shadow)))

    stop = (recipes.missing_command(spec.get("cmd")) or recipes.missing_command(first))
    stop = (("`%s` is not on the path here" % stop) if stop else None)
    if not stop and keys.unkeyed(spec):
        stop = "%s is not in %s" % (keys.unkeyed(spec), keys.store())
    own = recipes.agent_probe_urls(spec)
    if not stop and own and not egress.egress_ok(urls=own, timeout=8):
        stop = "%s does not answer from this machine" % recipes.probe_host(own)
    if stop:
        print("FAIL  every check: %s" % stop)
        return 1

    box = tempfile.mkdtemp(prefix="tutor-doctor-")
    ws = os.path.join(box, "workspace")
    live = course_repo.session_dir(ws)
    os.makedirs(os.path.join(live, "cards"))
    secret = "%s-%d" % (("heron", "quartz", "lantern", "maple")[os.urandom(1)[0] % 4],
                        1000 + int.from_bytes(os.urandom(2), "big") % 9000)
    n = 20 + os.urandom(1)[0] % 80
    with open(os.path.join(ws, "tutorboard.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": "tutor doctor", "stance": "do",
                   "check": "python3 check.py"}, fh)
    check_bytes = (DOCTOR_CHECK % {"want": n * (n + 1) // 2}).encode("utf-8")
    with open(os.path.join(ws, "check.py"), "wb") as fh:
        fh.write(check_bytes)
    git = ["git", "-C", ws, "-c", "user.name=tutor doctor",
           "-c", "user.email=doctor@localhost"]
    for step in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "doctor"]):
        subprocess.run(git[:3] + step if step[0] == "init" else git + step,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # The log is beside the workspace rather than in it, so the resumed turn
    # cannot find the code word by reading the first turn's output.
    logpath = os.path.join(box, "agent.log")
    log = open(logpath, "a", buffering=1)
    env = runturn.turn_environment(spec)
    turns = [0]
    passed = []

    # Set by `turn` when the session's own record names another model: the
    # check then fails whatever the turn did.
    astray = [None]

    def turn(template, prompt, fresh):
        turns[0] += 1
        astray[0] = None
        cmd = usage.with_usage(spec, [a.replace("{prompt}", prompt) for a in template])
        log.write("\n=== doctor turn %d (%s) ===\n"
                  % (turns[0], "fresh" if fresh else "resumed"))
        mark = os.path.getsize(logpath)
        t0 = time.time()
        try:
            rc, timed_out = runturn.run_turn(cmd, ws, log, DOCTOR_TURN_SECONDS, env=env)
        except OSError as exc:
            rc, timed_out = 127, False
            log.write("!! %s\n" % exc)
        said = usage.turn_output(logpath, mark, cap=4000000)
        usage.record_cost(live, log, turns[0], name, fresh,
                          usage.read_turn_usage(logpath, mark, spec.get("usage"), spec))
        err = None
        if timed_out:
            err = "timed out after %d s" % DOCTOR_TURN_SECONDS
        elif rc != 0:
            err = usage.failure_reason(said, "exit %d" % rc)
        elif usage.result_object_error(said):
            err = "the agent reported a failure and exited 0"
        elif seeing.blind_answer(usage.turn_text(said)):
            err = ("the model answered around %s"
                   % seeing.blind_answer(usage.turn_text(said)))
        where = "%s (provider not confirmed: no session export)" % route
        if confirms and not err:
            sid = turn_session(said)
            models, problem = (session_models(harness, sid, ws, env) if sid
                               else ([], "the turn reported no session id"))
            stray = sorted(set(m for m in models if m != want))
            seen = ", ".join(sorted(set(models))) or "?"
            where = "%s -> %s in %s" % (harness, seen, sid or "no session")
            if problem:
                astray[0] = "provider unconfirmed: %s" % problem
            elif stray:
                astray[0] = ("%d of %d answers came from %s, not %s"
                             % (sum(m != want for m in models), len(models),
                                ", ".join(stray), want))
        return err, said, time.time() - t0, where, astray[0]

    def line(number, label, ok, how, where=route):
        passed.append(ok)
        print("%s  %-3s %-15s %s: %s" % ("PASS" if ok else "FAIL", number, label,
                                        where, how))
        sys.stdout.flush()

    def tools_note(said):
        used = doctor_tools(said)
        return "" if used is None else "; tools %s" % (", ".join(used) or "none")

    # 1, then 3 straight after it, so `--continue` resumes turn 1's session.
    err, said1, took, at, off = turn(
        first, DOCTOR_TEXT_PROMPT % {"secret": secret}, True)
    err = err or off
    card = os.path.join(live, "cards", "001.md")
    wrote = os.path.isfile(card) and os.path.getsize(card) > 0
    line("1", "text turn", not err and wrote,
         "%s (%.0f s)" % (err or ("card written, exit 0" if wrote
                                  else "exit 0 but no live/cards/001.md"), took),
         where=at)

    err, said3, took, at, off = turn(resume, DOCTOR_RESUME_PROMPT, False)
    on_disk = []
    for top, dirs, files in os.walk(ws):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            try:
                with open(os.path.join(top, f), encoding="utf-8",
                          errors="replace") as fh:
                    if secret in fh.read():
                        on_disk.append(f)
            except OSError:
                pass
    # A MISSING ID IS NOT THE SAME SESSION. Without both ids nothing says the
    # resume continued turn 1 rather than some other conversation.
    one, two = turn_session(said1), turn_session(said3)
    same = bool(one and two) and one == two
    recalled = secret in usage.turn_text(said3)
    line("3", "resumed turn",
         not err and not off and recalled and not on_disk and same,
         "%s (%.0f s)" % (
             err or ("cannot tell whether it resumed turn 1: turn %s "
                     "reported no session id" % " and turn ".join(
                         t for t, sid in (("1", one), ("3", two)) if not sid)
                     if not (one and two)
                     else off if off
                     else "the code word was written to %s, so recalling it "
                          "proves nothing" % ", ".join(on_disk) if on_disk
                     else "resumed a different session (%s, not %s)" % (two, one)
                     if not same
                     else "recalled turn 1's code word%s"
                     % (" in session %s" % one if one else "") if recalled
                     else "did not recall turn 1's code word: %s"
                     % usage.turn_text(said3).strip()[:120].replace("\n", " ")),
             took), where=at + ", --continue")

    err, said2, took, at, off = turn(first, DOCTOR_CODE_PROMPT % {"n": n}, True)
    err = err or off
    # THE CHECK IS DOCTOR'S, BYTE FOR BYTE, or its PASS is the model's word.
    # The turn has a shell and an edit tool in the same directory.
    try:
        with open(os.path.join(ws, "check.py"), "rb") as fh:
            intact = fh.read() == check_bytes
    except OSError:
        intact = False
    # `-I`: the script's directory is not on the import path, so a module the
    # turn dropped beside check.py cannot stand in for one check.py imports.
    chk, _ = config.clean_check("python3 -I check.py")
    if not intact:
        verdict, checked = ["check.py is not the file doctor wrote, so its "
                            "verdict proves nothing"], False
    else:
        try:
            ran = subprocess.run(chk["all"], cwd=ws, capture_output=True,
                                 text=True, timeout=60, env=runturn.at_root(ws))
            verdict = (ran.stdout + ran.stderr).strip().splitlines()[-1:] or [""]
            checked = ran.returncode == 0
        except (OSError, subprocess.TimeoutExpired) as exc:
            verdict, checked = [str(exc)], False
    used = doctor_tools(said2)
    tooled = used is None or (any(t in EDIT_TOOLS for t in used)
                              and any(t in SHELL_TOOLS for t in used)
                              and any(t in WRITE_TOOLS for t in used))
    line("2", "coding turn", not err and checked and tooled,
         "%s%s (%.0f s)" % (
             err or ("workspace check passed" if checked and tooled
                     else "workspace check passed, but no edit and shell tool "
                          "call was seen" if checked
                     else "workspace check failed: %s" % verdict[0][:120]),
             tools_note(said2), took), where=at)

    code_a = seeing._code()
    seeing._token_png(code_a, os.path.join(ws, "slate.png"))
    err, said4, took, at, off = turn(first, DOCTOR_IMAGE_PROMPT, True)
    err = err or off
    try:
        with open(os.path.join(ws, "seen.txt"), encoding="utf-8") as fh:
            seen = fh.read().strip()
    except OSError:
        seen = ""
    read_it = re.sub(r"\D", "", code_a) in re.sub(r"\D", "", seen)
    # ITS OWN READ, AND NOTHING ELSE. The right digits prove only that
    # something saw the image; a turn that shelled out to another provider
    # gets them too. So where the harness reports its tools, the slate must have
    # been opened with `read` and no other tool may have run.
    used = doctor_tools(said4)
    opened = used is None or any(
        (d.get("part") or {}).get("tool") == "read"
        and str(((d.get("part") or {}).get("state") or {}).get("input", {})
                .get("filePath", "")).endswith("slate.png")
        for d in usage.opencode_events(said4) if d.get("type") == "tool_use")
    # Listing and searching local files sends nothing anywhere, so a turn that
    # looked for the slate before opening it still proves its own read.
    other = sorted(set(t for t in (used or [])
                       if t not in ("read", "write", "glob", "list", "grep")))
    line("4a", "image, own read", not err and read_it and opened and not other,
         "%s%s (%.0f s)" % (
             err or ("used %s besides its own read, so the digits prove "
                     "nothing about it" % ", ".join(other) if other
                     else "never opened slate.png with its read tool"
                     if not opened
                     else "read %s off slate.png" % code_a if read_it
                     else "wrote %r for %s" % (seen[:40], code_a)),
             tools_note(said4), took), where=at)

    vision = spec.get("vision") or {}
    where = ("%s %s" % (recipes.probe_host([vision["endpoint"]]), vision.get("model"))
             if vision.get("endpoint")
             else " ".join((vision.get("cmd") or ["?"])[:1]))
    where = "seeing.ask -> %s" % where
    code_b = seeing._code()
    page = seeing._token_png(code_b, os.path.join(box, "page.png"))
    asked = {}
    real_code, real_answer = seeing._code, seeing._answer

    def drawn():
        asked["code"] = real_code()
        return asked["code"]

    def sent(settings, images, prompt):
        asked["prompt"] = prompt
        return real_answer(settings, images, prompt)
    seeing._code, seeing._answer = drawn, sent
    t0 = time.time()
    try:
        if not vision:
            raise seeing.Refused("the recipe has no `vision` block")
        got, problem = seeing.ask(dict(vision), [page], DOCTOR_SEE_PROMPT), None
    except seeing.Refused as exc:
        got, problem = "", str(exc)
    finally:
        seeing._code, seeing._answer = real_code, real_answer
    digits = lambda s: re.sub(r"\D", "", s or "")
    hidden = bool(asked.get("code")) and digits(asked["code"]) not in digits(
        asked.get("prompt"))
    right = digits(code_b) in digits(got)
    line("4b", "image, board see", not problem and hidden and right,
         "%s (%.0f s)" % (
             problem[:200] if problem
             else "the witness code %s was in the prompt" % asked.get("code")
             if not hidden
             else "witness %s read back from the strip, absent from the "
                  "prompt; page read as %s" % (asked["code"], code_b) if right
             else "witness read back, but the page came back as %r, not %s"
             % (got[:40], code_b),
             time.time() - t0), where=where)

    rows = usage.read_costs(ws)
    if not spec.get("usage"):
        ok = True
        how = ("this recipe reports no usage, so its turns are recorded with no "
               "dollar figure and `tutor cost` says so")
    elif len(rows) != turns[0] or not all(r.get("tokens") for r in rows):
        ok = False
        how = ("%d of %d turns wrote a line to live/cost.jsonl; the `%s` parser "
               "found no usage in the rest" % (len(rows), turns[0], spec["usage"]))
    elif spec.get("prices") and not all(doctor_priced(r) for r in rows):
        ok = False
        how = "the turns were counted but `priced` wrote no dollar figure"
    else:
        ok = True
        total = sum(r.get("usd", 0) for r in rows)
        how = ("%d turns, %s tokens, $%.4f%s, recorded in live/cost.jsonl"
               % (len(rows), usage.thousands(sum(r.get("tokens", 0) for r in rows)),
                  total, " at the %s rate" % rows[-1]["rate"]["window"]
                  if rows[-1].get("rate") else " as the agent reported it"
                  if total else " (no price table)"))
    line("5", "usage and price", ok, how,
         where="%s parser" % (spec.get("usage") or "no"))
    if rows:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            usage.cost_report(cfg, {"dir": os.path.basename(os.path.abspath(ws)),
                                    "root": os.path.abspath(ws)})
        print("\ntutor cost %s:" % ws)
        for text in buf.getvalue().rstrip().splitlines():
            print("  " + text)
    log.close()

    good = all(passed)
    if good and not keep:
        shutil.rmtree(box, ignore_errors=True)
    else:
        print("\nworkspace kept: %s (the turns' output is in %s)" % (ws, logpath))
    print("\n%s" % ("all %d checks passed" % len(passed) if good
                    else "%d of %d checks failed"
                    % (passed.count(False), len(passed))))
    return 0 if good else 1
