#!/usr/bin/env python3
"""The brief and the recap ride in the prompt.

    python3 test/injected.py

`loop.take_turn` renders both in-process and hands them to the provider: as a
system prompt where the recipe has `system_args` (claude's
`--append-system-prompt`), else above the prompt. The prompt says they are
above and not to fetch them. A fake provider records its argv; nothing here
touches a real session, port or provider.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
sys.path.insert(0, BOARD)

box = tempfile.mkdtemp(prefix="tutor-injected-")
CONFIG_HOME = os.path.join(box, "config")
os.environ["XDG_CONFIG_HOME"] = CONFIG_HOME
os.environ["BOARD_STATE_DIR"] = os.path.join(box, "state")
os.environ["BOARD_NO_TAILNET"] = "1"
os.environ["TUTORBOARD_TRASH"] = os.path.join(box, "trash")
for name in ("TUTORBOARD_SESSION", "TUTORBOARD_TURN", "TUTORBOARD_PORT"):
    os.environ.pop(name, None)

from tutorboard import brief, sessions  # noqa: E402
from tutorboard.agents import recipes  # noqa: E402
from tutorboard.course import config as course_config  # noqa: E402
from tutorboard.runner import loop, prompts  # noqa: E402

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)[:600]) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def git(*args, cwd):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t"] + list(args),
                   cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   check=True)


CALLS = os.path.join(box, "calls.jsonl")
FAKE = os.path.join(box, "bin", "fake-provider")
write(FAKE, "#!/usr/bin/env python3\nimport json, sys\n"
            "with open(%r, 'a') as fh:\n"
            "    fh.write(json.dumps({'argv': sys.argv[1:]}) + '\\n')\n" % CALLS)
os.chmod(FAKE, 0o755)


def configure(default):
    write(os.path.join(CONFIG_HOME, "tutor-board", "config.json"), json.dumps({
        "provider": default, "vision_agent": default,
        "headless_timeout": 60, "doing_timeout": 60, "handoff_timeout": 60,
        "agents": {
            "plain": {"cmd": [FAKE], "label": "Plain",
                      "headless_first": [FAKE, "{prompt}"], "usage": "none"},
            "sys": {"cmd": [FAKE], "label": "Sys",
                    "headless_first": [FAKE, "-p", "{prompt}"],
                    "system_args": ["--append-system-prompt", "{system}"],
                    "usage": "none"},
        }}))


def last_call():
    with open(CALLS) as fh:
        return json.loads(fh.read().splitlines()[-1])["argv"]


# --- a temp Atlas: one course, its RULES.md committed, its TUTOR.md --------
atlas = os.path.join(box, "atlas")
course = os.path.join(atlas, "courses", "Demo")
write(os.path.join(course, "tutorboard.json"), json.dumps({"name": "Demo", "phi": False}))
write(os.path.join(course, "RULES.md"), "# Rules\n\n- never make the owner transcribe.\n")
write(os.path.join(course, "TUTOR.md"),
      "# Demo\n\n## Where things are\n\nnotes in ch01.\n\n## Now\n\ncosets next.\n")
write(os.path.join(atlas, ".gitignore"), "/sessions/\n")
git("init", "-q", "-b", "main", cwd=atlas)
git("add", "-A", cwd=atlas)
git("commit", "-qm", "fixture", cwd=atlas)

sid = sessions.new("injected", base=atlas)["id"]
sessions.bind(sid, "courses/Demo", base=atlas)
repo = sessions.repo(sid, atlas)
for n, (kind, title) in enumerate((("lesson", "Groups, defined"),
                                   ("question", "Is Z under + a group?"),
                                   ("lesson", "Subgroups")), 1):
    write(os.path.join(repo.cards, "%04d-c%d.md" % (n, n)),
          "---\nkind: %s\ntitle: %s\n---\n\nbody of card %d, NEWEST-MARK-%d\n"
          % (kind, title, n, n))
with open(repo.path("turns.jsonl"), "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"id": "t0001", "rev": 1, "t": 1.0, "iso": "2026-10-09 10:00:00",
                         "answers": "0002", "text": "yes, inverses are negatives"}) + "\n")


def ctx_for(name):
    cfg = recipes.load_config()
    logpath = os.path.join(repo.live, "agent.log")
    return loop.Ctx(cfg=cfg, course={"root": repo.root, "dir": "Demo",
                                     "name": course_config.read_config(repo.root)["name"]},
                    repo=repo, root=repo.root, cwd=atlas, live=repo.live,
                    log=open(logpath, "a", buffering=1), logpath=logpath,
                    agent_name=name, spec=cfg["agents"][name], turns=0,
                    env=dict(os.environ), sid=sid, striking=[None, None, 0])


def turn(name, message):
    configure(name)
    ctx = ctx_for(name)
    try:
        loop.take_turn(ctx, message)
    finally:
        ctx.log.close()
    return last_call()


FETCHING = ("Run these two commands", "Run `board brief`", "Run `board recap`",
            "`board brief` -- the method", "`board recap` -- the lesson")

try:
    # --- a lesson turn, on a provider with no system prompt ---------------
    argv = turn("plain", "[2026-10-09 10:01:00] what is a coset?")
    prompt = argv[-1]
    check("a lesson turn's prompt opens with the brief",
          prompt.startswith("=== THE BRIEF"), prompt[:200])
    check("the brief is the rendered one: the method, RULES.md at HEAD, TUTOR.md",
          "THE LESSON IS EXERCISES" in prompt
          and "never make the owner transcribe" in prompt
          and "cosets next." in prompt, prompt[:2000])
    check("the recap follows it: every card a line, the newest in full, the open "
          "question, their turn",
          "=== THE RECAP" in prompt and "Groups, defined" in prompt
          and "NEWEST-MARK-3" in prompt and "NEWEST-MARK-1" not in prompt
          and "<- answered" in prompt and "inverses are negatives" in prompt)
    check("then the turn's own prompt, with the inbox",
          prompt.index("=== END OF THE BRIEF AND THE RECAP")
          < prompt.index("You are running headless")
          < prompt.index("what is a coset?"))
    check("which says both are above and not to fetch them",
          "The brief and the recap are above" in prompt
          and "Do not run `board brief` or `board recap`" in prompt)
    check("and carries no instruction to fetch them",
          not [f for f in FETCHING if f in prompt],
          [f for f in FETCHING if f in prompt])

    # --- the same turn on a recipe with system_args (claude's shape) -------
    argv = turn("sys", "[2026-10-09 10:02:00] and a normal subgroup?")
    i = argv.index("--append-system-prompt") if "--append-system-prompt" in argv else -1
    system = argv[i + 1] if i >= 0 else ""
    check("a recipe with system_args is handed both as its system prompt",
          system.startswith("=== THE BRIEF") and "=== THE RECAP" in system
          and "THE LESSON IS EXERCISES" in system and "NEWEST-MARK-3" in system,
          argv[:3])
    prompt = argv[argv.index("-p") + 1]
    check("and its prompt is the turn's own, not a second copy",
          prompt.startswith("You are running headless") and "=== THE BRIEF" not in prompt
          and "and a normal subgroup?" in prompt)

    # --- a revision reads neither; an [unfinished] report the recap --------
    argv = turn("plain", "[2026-10-09 10:03:00] [revise] fix page 2 of docs/a/a.pdf")
    check("a revision is handed neither", "=== THE" not in argv[-1], argv[-1][:200])
    argv = turn("plain", "[2026-10-09 10:04:00] [unfinished] The turn before this "
                         "one exited with sessions/x/cards/0003-c3.md still the "
                         "placeholder.")
    check("an [unfinished] report is handed the recap and not the brief",
          argv[-1].startswith("=== THE RECAP") and "=== THE BRIEF" not in argv[-1]
          and "The recap of the lesson is above" in argv[-1])

    # --- the wrap-up reads the brief and the recap above its prompt ---------
    configure("plain")
    ctx = ctx_for("plain")
    try:
        loop.wrap_up(ctx)
    finally:
        ctx.log.close()
    prompt = last_call()[-1]
    check("the wrap-up is handed the brief, with TUTOR.md, and the recap, and "
          "told to fetch neither",
          prompt.startswith("=== THE BRIEF") and "=== THE RECAP" in prompt
          and "This session is ending now" in prompt
          and "Do not run `board brief` or `board recap`" in prompt
          and "`board memo <section>`" in prompt
          and "Run `board recap`" not in prompt)

    # --- the size guard ----------------------------------------------------
    with open(repo.path("turns.jsonl"), "a", encoding="utf-8") as fh:
        for k in range(2, 260):
            fh.write(json.dumps({"id": "t%04d" % k, "rev": 1, "t": float(k),
                                 "iso": "2026-10-09 11:%02d:00" % (k % 60),
                                 "text": "a long remark about cosets %d " % k * 4})
                     + "\n")
    whole = brief.recap(repo)
    guarded = brief.guarded_recap(repo)
    check("a recap past the limit is the compact one (%d > %d >= %d)"
          % (len(whole), brief.RECAP_LIMIT, len(guarded)),
          len(whole) > brief.RECAP_LIMIT >= len(guarded))
    check("which keeps the newest card whole and one line per earlier card",
          "NEWEST-MARK-3" in guarded and "Groups, defined" in guarded
          and "Is Z under + a group?" in guarded and "NEWEST-MARK-1" not in guarded)
    check("and drops their earlier turns, saying where they are",
          "their turns so far" not in guarded
          and "earlier turn(s) of theirs not listed" in guarded)
    argv = turn("plain", "[2026-10-09 12:00:00] go on")
    check("and that is what a turn is handed",
          "earlier turn(s) of theirs not listed" in argv[-1]
          and "their turns so far" not in argv[-1])
    p = subprocess.run([sys.executable, os.path.join(BOARD, "bin", "board"), "recap"],
                       env=dict(os.environ, TUTORBOARD_SESSION=repo.live,
                                TUTORBOARD_COURSES=atlas),
                       cwd=atlas, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=60)
    check("`board recap` stays for manual use, and prints it whole",
          p.returncode == 0 and "their turns so far" in p.stdout, p.stdout[-400:])
finally:
    shutil.rmtree(box, ignore_errors=True)

print("\n%d failed" % len(fails) if fails else "\nall passed")
sys.exit(1 if fails else 0)
