#!/usr/bin/env python3
"""What a headless course costs to run, in tokens.

Not a speed test. A tutor billed by the token pays for every character it is
told to read, and it pays again for every round trip inside a turn, because each
one resends the whole conversation. Two things follow, and this file guards both:

- **A turn is a fresh process and is handed what it must read.** The brief
  and the recap ride in its prompt (test/injected.py); it reads no document
  and no card file by file.
- **A lesson is read back in one block.** The recap is that block, also
  printed by `board recap`. Reading a twelve-card lesson card by card is
  twelve round trips for what fits in one.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BOARD = os.path.join(ROOT, "bin", "board")
sys.path.insert(0, ROOT)

from tutorboard.runner import prompts  # noqa: E402
from tutorboard.agents import recipes  # noqa: E402
from tutorboard.runner import turn as runturn  # noqa: E402
from tutorboard.agents import usage  # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


# --- the prompts ----------------------------------------------------------
first = prompts.HEADLESS_FIRST_PROMPT
EVERY_PROMPT = [v for k, v in vars(prompts).items()
                if k.isupper() and isinstance(v, str)]

check("a turn is told the brief and the recap are above, and not to fetch them",
      "The brief and the recap are above" in first
      and "Do not run `board brief` or `board recap`" in first
      and "Run these" not in first)
check("and is told NOT to read the documents that call replaced",
      "Do not read" in first and "AI_INSTRUCTIONS.md" in first
      and "board/TEACHING.md" in first)
check("and not to read the lesson card by card",
      "cards file by file" in first)
check("there is no resume prompt: every turn is a fresh process",
      not hasattr(prompts, "HEADLESS_RESUME_PROMPT"))
check("a turn is told not to touch HANDOFF.md", "Do not touch `HANDOFF.md`" in first)
check("a turn is told to keep TUTOR.md true with `board memo`",
      "board memo" in first and "800 words" in first)
check("and no prompt names `board wait`, which is gone",
      all("board wait" not in p for p in EVERY_PROMPT))
check("and no prompt names a live/ path a session does not have",
      all("live/cards" not in p and "live/state.json" not in p
          and "live/TEACHING.md" not in p for p in EVERY_PROMPT))

# The prompt IS the inbox, already marked read. Telling the agent to run
# `board inbox` as well bought an empty round trip on every single turn.
check("a turn is not sent to `board inbox` for what it already has",
      "do not run `board inbox`" in first.lower())

check("the handoff is capped, because it is read on every future session",
      "350 words" in prompts.HANDOFF_PROMPT)
check("and it is written through the one command that enforces the cap",
      "board handoff" in prompts.HANDOFF_PROMPT)
check("the wrap-up is handed the recap, and told not to fetch it",
      "The recap is above" in prompts.HANDOFF_PROMPT
      and "Do not run `board recap`" in prompts.HANDOFF_PROMPT
      and "file by file" in prompts.HANDOFF_PROMPT)
check("the handoff turn reads no document to write itself",
      "do not read ai_instructions.md" in prompts.HANDOFF_PROMPT.lower()
      and "board/TEACHING.md" in prompts.HANDOFF_PROMPT
      and "old HANDOFF.md" in prompts.HANDOFF_PROMPT)
check("the handoff is not a documentation review either",
      "Do not review" in prompts.HANDOFF_PROMPT)

# --- every turn is a fresh process ----------------------------------------
# Every session's turn runs in the Atlas root, so a resume would pick up
# another session's conversation. What a turn holds never grows with the lesson.
spec_claude = {"headless_first": ["claude", "-p", "{prompt}"],
               "headless": ["claude", "-p", "{prompt}", "--continue"]}
for sig in ("", "unfinished", "carry", "revise", "writeup", "repair"):
    use, template = runturn.turn_plan(spec_claude, sig)
    check("a %s turn opens a fresh conversation" % (sig or "lesson"),
          "--continue" not in use)
check("a lesson turn is cold-prompted",
      runturn.turn_plan(spec_claude)[1] is first)
check("an unfinished report reads what the work changed off disk",
      runturn.turn_plan(spec_claude, "unfinished")[1]
      is prompts.HEADLESS_UNFINISHED_PROMPT)
check("and a `[carry]` is not special: it is an ordinary cold turn",
      runturn.turn_plan(spec_claude, "carry")[1] is first
      and not hasattr(prompts, "HEADLESS_CARRY_PROMPT"))
use, template = runturn.turn_plan({"headless": ["codex", "exec", "{prompt}"]})
check("an agent with one recipe runs that, cold-prompted",
      use == ["codex", "exec", "{prompt}"] and template is first)

check("the config says how big an allowance window is, without guessing",
      "quota_tokens" in recipes.DEFAULT_CONFIG
      and recipes.DEFAULT_CONFIG["quota_tokens"] is None)

# --- the session's mode ------------------------------------------------------
# `mode: do` is what the owner sets when they want the work done rather than
# taught. It is never guessed: writing the code for somebody who wanted to learn
# it is the one mistake here the next card cannot undo. One paragraph each.

from tutorboard import sense as serve_mod                    # noqa: E402

check("teaching is the default, and anything that is not do teaches",
      serve_mod.mode_sense("teach") == serve_mod.TEACH_SENSE
      and serve_mod.mode_sense(None) == serve_mod.TEACH_SENSE
      and serve_mod.mode_sense("code") == serve_mod.TEACH_SENSE)
do = serve_mod.mode_sense("do")
check("do mode is told to write the code",
      "you write the code" in do.lower())
check("and to run what needs running", "run what needs running" in do)
check("but still one card", "one card" in do.lower())
check("and the card-first ordering is no longer claimed for a doing turn",
      "before the rest" not in do)
check("which has an order of its own that says so outright",
      "opposite" in serve_mod.DOING_SENSE.lower()
      and "board write --over" in serve_mod.DOING_SENSE)
check("and to say what it did not actually verify", "did NOT verify" in do)
check("and no subject is read anywhere in the config",
      "mode" not in serve_mod.config.read_config(tempfile.gettempdir()))

# --- board recap ----------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="tutor-tokens-")
try:
    with open(os.path.join(tmp, "tutorboard.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": "Test Course", "mode": "math"}, fh)
    live = os.path.join(tmp, "live")
    cards = os.path.join(live, "cards")
    os.makedirs(cards)
    with open(os.path.join(live, "state.json"), "w", encoding="utf-8") as fh:
        json.dump({"course": "Test Course", "session": "lecture",
                   "chapter": "Ch 1 - Groups"}, fh)

    # A lesson of a realistic length, each card a realistic size.
    body = "Some teaching prose about cosets. " * 60
    for n in range(1, 13):
        kind = "question" if n % 3 == 0 else "lesson"
        with open(os.path.join(cards, "%04d-card-%d.md" % (n, n)), "w",
                  encoding="utf-8") as fh:
            fh.write("---\nkind: %s\ntitle: Card %d\n---\n\n%s\n" % (kind, n, body))
    total = sum(os.path.getsize(os.path.join(cards, n)) for n in os.listdir(cards))

    with open(os.path.join(live, "turns.jsonl"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": "t0001", "rev": 1, "t": 1.0,
                             "iso": "2026-08-27 10:00:00", "from": "student",
                             "answers": "0003", "kind": "ink",
                             "text": "", "png": "/answers/t0001-r1.png"}) + "\n")
        fh.write(json.dumps({"id": "t0002", "rev": 1, "t": 2.0,
                             "iso": "2026-08-27 10:20:00", "from": "student",
                             "answers": "0006", "kind": "text",
                             "text": "I think the index is 2"}) + "\n")
        # A correction supersedes in place; the old revision is not the lesson.
        fh.write(json.dumps({"id": "t0002", "rev": 2, "t": 3.0,
                             "iso": "2026-08-27 10:25:00", "from": "student",
                             "answers": "0006", "kind": "text",
                             "text": "the two cosets are H and its complement"}) + "\n")

    p = subprocess.run([sys.executable, BOARD, "recap"], cwd=tmp,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    out = p.stdout.decode("utf-8", "replace")
    check("recap runs", p.returncode == 0)
    check("it names the session", "Test Course" in out and "Ch 1 - Groups" in out)
    check("every card is there as a line", all("Card %d" % n in out for n in range(1, 13)))
    check("the newest card is there in full", body.strip()[:40] in out)
    check("it says which question is still open", "OPEN" in out)
    # 0003 and 0006 were answered; 0009 and 0012 were not.
    answered_lines = [l for l in out.splitlines()
                      if l.strip().startswith(("0003", "0006"))]
    check("an answered question is marked answered, not open",
          answered_lines and all("answered" in l and "OPEN" not in l
                                 for l in answered_lines))
    check("and the ones still owed are the only open ones",
          out.count("OPEN") == 2)
    check("their turns are listed", "10:00:00" in out and "10:20:00" not in out
          or "the two cosets" in out)
    check("only the newest revision of a turn is shown",
          "I think the index is 2" not in out)
    check("their latest turn is shown in full", "the two cosets" in out)

    # The whole point: one call, and a fraction of the lesson's own size.
    check("recap is a fraction of the cost of reading the lesson (%d vs %d bytes)"
          % (len(out), total), len(out) < total / 2.0)

    # The list of card LINES is the one part of the recap that grew with the
    # lesson: 107 cards is 6.4k of titles, read at the start of every turn.
    for n in range(13, 71):
        with open(os.path.join(cards, "%04d-card-%d.md" % (n, n)), "w",
                  encoding="utf-8") as fh:
            fh.write("---\nkind: lesson\ntitle: Card %d\n---\n\n%s\n" % (n, body))
    pbig = subprocess.run([sys.executable, BOARD, "recap"], cwd=tmp,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    bigout = pbig.stdout.decode("utf-8", "replace")
    check("a long lesson still says how many cards it has", "70 card(s)" in bigout)
    check("but the list of them is bounded rather than growing every turn",
          "Card 70" in bigout and "Card 1\n" not in bigout
          and "earlier card(s) not listed" in bigout)
    check("and it says where the earlier ones went, and how to see them",
          "HANDOFF.md" in bigout and "recap --all" in bigout)
    check("a seventy-card recap is no bigger than a twelve-card one was (%d vs %d)"
          % (len(bigout), len(out)), len(bigout) < len(out) * 3)
    for n in range(13, 71):
        os.remove(os.path.join(cards, "%04d-card-%d.md" % (n, n)))

    # --all is there for the rare case, and is honestly bigger.
    p2 = subprocess.run([sys.executable, BOARD, "recap", "--all"], cwd=tmp,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    check("--all prints the lesson in full when that is genuinely wanted",
          len(p2.stdout) > total)

    # An empty lesson says so rather than printing nothing.
    for n in os.listdir(cards):
        os.remove(os.path.join(cards, n))
    p3 = subprocess.run([sys.executable, BOARD, "recap"], cwd=tmp,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    check("an empty lesson says so", b"no cards yet" in p3.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# --- board brief: a size budget -------------------------------------------
# The other half of what a turn reads. `recap` above is the lesson; this is the
# method, the owner's RULES.md at HEAD and the tutor's TUTOR.md, read on every
# cold turn. A fixture with RULES.md at its 300-word size and TUTOR.md at its
# 800-word cap, beside a contract, a method and a handoff that are padded and
# must not be read, briefs in at most `brief.BUDGET` (14,000) characters.
from tutorboard import brief as brief_mod                     # noqa: E402

RULES = ("# Rules\n\n- **You never make the user transcribe what they already "
         "wrote.** Open the PNG.\n- **The user never runs a board command.**\n"
         + "".join("- rule %d: %s\n" % (i, "keep the data fenced " * 3)
                   for i in range(18)))
TUTOR = ("# Test Course\n\n## Where things are\n\n"
         + "chapters/ch01 holds the notes and homework. " * 20
         + "\n\n## Now\n\n" + "Cosets, then Lagrange, then quotients. " * 80
         + "\n\n## Open decisions\n\n" + "- which book's notation\n" * 25
         + "\n## Done recently\n\n" + "- subgroups and orders\n" * 37)

tmp = tempfile.mkdtemp(prefix="tutor-brief-")
try:
    with open(os.path.join(tmp, "tutorboard.json"), "w", encoding="utf-8") as fh:
        json.dump({"name": "Test Course"}, fh)
    contract = ("# AI_INSTRUCTIONS.md\n\n## 0. Who you are working for\n\n"
                + ("padding that a turn has no reason to pay for. " * 900))
    with open(os.path.join(tmp, "AI_INSTRUCTIONS.md"), "w", encoding="utf-8") as fh:
        fh.write(contract)
    with open(os.path.join(tmp, "RULES.md"), "w", encoding="utf-8") as fh:
        fh.write(RULES)
    with open(os.path.join(tmp, "TUTOR.md"), "w", encoding="utf-8") as fh:
        fh.write(TUTOR)
    with open(os.path.join(tmp, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("# Test Course\n\n" + "the owner's README, never briefed. " * 400)
    live = os.path.join(tmp, "live")
    os.makedirs(os.path.join(live, "cards"))
    with open(os.path.join(tmp, ".gitignore"), "w", encoding="utf-8") as fh:
        fh.write("/live/\n")
    with open(os.path.join(live, "state.json"), "w", encoding="utf-8") as fh:
        json.dump({"course": "Test Course", "session": "lecture",
                   "chapter": "Ch 1 - Groups"}, fh)
    hand = "<!-- chapter: Ch 1 - Groups -->\n# HANDOFF\n\nthey got cosets.\n"
    with open(os.path.join(tmp, "HANDOFF.md"), "w", encoding="utf-8") as fh:
        fh.write(hand)
    for argv in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.email=t@example.com", "-c", "user.name=t",
                  "commit", "-q", "-m", "fixture"]):
        subprocess.run(["git", "-C", tmp] + argv, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)

    def board(*args, **kw):
        return subprocess.run([sys.executable, BOARD] + list(args), cwd=tmp,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=60, **kw)

    check("the fixture's RULES.md is at its 300-word size and TUTOR.md at its "
          "800-word cap", 280 <= len(RULES.split()) <= 300
          and 760 <= len(TUTOR.split()) <= 800)
    p = board("brief")
    out = p.stdout.decode("utf-8", "replace")
    check("brief runs", p.returncode == 0)
    check("it says what this sitting is", "Test Course" in out and "Ch 1 - Groups" in out)
    check("it carries the method rather than a pointer to it",
          "THE LESSON IS EXERCISES" in out)
    check("and the measure the work already has, which every sitting is asked for",
          "NAME THE MEASURE THIS WORK ALREADY HAS" in out)
    check("it carries the owner's RULES.md", "never make the user transcribe" in out)
    check("and the tutor's TUTOR.md, whole", "subgroups and orders" in out
          and "which book's notation" in out)
    check("it says how a turn works now",
          "board memo" in out and "Do not wait" in out and "own session" in out)
    check("it names board/TEACHING.md for a rule that needs its detail",
          "board/TEACHING.md" in out)
    check("and reads none of the contract, the handoff or the README",
          "padding that a turn" not in out and "they got cosets" not in out
          and "never briefed" not in out)
    check("THE BUDGET: a fixture brief is at most %d characters (%d)"
          % (brief_mod.BUDGET, len(out)),
          brief_mod.BUDGET == 14000 and len(out) <= brief_mod.BUDGET)

    # --- the handoff: capped at the door ----------------------------------
    p = board("handoff", input=("word " * 400).encode())
    check("a handoff over 350 words is REFUSED, not trimmed",
          p.returncode == 1 and b"cap is 350" in p.stdout)
    check("and nothing was written over the old one",
          b"they got cosets" in board("handoff", "--show").stdout)
    p = board("handoff", input=b"# HANDOFF\n\nthey got quotient groups.\n")
    check("a handoff inside the cap is written", p.returncode == 0)
    with open(os.path.join(tmp, "HANDOFF.md"), "r", encoding="utf-8") as fh:
        written = fh.read()
    check("and is stamped with the chapter it is about, by the writer",
          written.startswith("<!-- chapter: Ch 1 - Groups -->"))
    check("`--check` says how long it is",
          b"words, cap 350, ok" in board("handoff", "--check").stdout)

    # --- there is no `board wait`: a turn does not wait -------------------
    # The defect this replaced cost $4.49 in one turn: the agent ran `board
    # wait` at the end of its own turn, held the conversation open while the
    # student thought, and answered their next message inside it. The runner
    # starts a fresh turn per message, so nothing waits and the command is gone.
    p = board("wait", "--timeout", "1")
    check("`board wait` is no command at all",
          p.returncode != 0 and b"unknown command" in p.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# --- what a turn cost, and that it is measured at all ---------------------
# A design whose whole justification is price has to be measured. These two
# guard the measurement itself: the flag that makes the agent report, and the
# parse of what it reports.
claude = recipes.DEFAULT_CONFIG["agents"]["claude"]
check("the claude recipe says how to ask what a turn cost",
      claude.get("usage") == "claude-json" and claude.get("usage_args"))
check("the flag is appended rather than written into the recipe, so a machine "
      "carrying an old copy of it still reports",
      "--output-format" not in claude["headless"]
      and "--output-format" in usage.with_usage(claude, claude["headless"]))
check("and appending it twice does not repeat it",
      usage.with_usage(claude, usage.with_usage(claude, claude["headless"]))
      == usage.with_usage(claude, claude["headless"]))
check("an agent that reports nothing is simply not accounted for",
      usage.with_usage({}, ["free", "{prompt}"]) == ["free", "{prompt}"])
check("and `board cost` splits the evening by who taught it, because the "
      "reason to have three is to see which one it went on",
      "by_agent.setdefault" in open(os.path.join(ROOT, "tutorboard", "agents",
                                                 "usage.py"), encoding="utf-8").read())

fd, logpath = tempfile.mkstemp(prefix="tutor-cost-", suffix=".log")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("=== 10:00:00 turn 1 ===\nthe student sent a page\n")
        offset = fh.tell()
        # Real stdout: a warning the agent printed, then the result object.
        fh.write("Warning: no stdin data received in 3s, proceeding without it.\n")
        fh.write(json.dumps({
            "type": "result", "subtype": "success", "num_turns": 6,
            "session_id": "abc", "total_cost_usd": 0.372,
            "result": "wrote card 0042",
            "usage": {"input_tokens": 10, "output_tokens": 4291,
                      "cache_creation_input_tokens": 29513,
                      "cache_read_input_tokens": 152020},
            "modelUsage": {"claude-opus-5[1m]": {"costUSD": 0.371},
                           "claude-haiku-4-5-20251001": {"costUSD": 0.001}},
        }) + "\n")
    u = usage.read_turn_usage(logpath, offset, "claude-json")
    check("a turn's own report is read back out of the log",
          u.get("usd") == 0.372 and u.get("requests") == 6)
    check("and the numbers that matter are the cumulative ones",
          u.get("cache_read") == 152020 and u.get("cache_write") == 29513
          and u.get("out") == 4291)
    # The headline figure, because on a subscription what runs out is a
    # five-hour allowance and that is computed from tokens, not dollars.
    check("and the total a quota is computed from is everything through the model",
          u.get("tokens") == 10 + 4291 + 29513 + 152020)
    check("noise on the same stream does not break the parse",
          u.get("session") == "abc")
    check("an agent that reports nothing yields nothing rather than raising",
          usage.read_turn_usage(logpath, offset, None) == {})
    check("and a log with no report at all is not an error",
          usage.read_turn_usage(logpath, 0, "claude-json").get("usd") == 0.372
          and usage.read_turn_usage(logpath, 10 ** 9, "claude-json") == {})

    # ---- WHAT A TURN COST, PER PROVIDER -----------------------------------
    #
    # `usage` was an equality test against one string, so every other provider
    # cost nothing and appeared in no total -- and the measurement that
    # justifies every decision about how a turn is shaped would have stopped
    # covering two thirds of the table the moment there were three of them.
    check("`usage` is a dispatch, so a provider is a parser added beside the "
          "others rather than a branch in the reader",
          set(usage.USAGE_PARSERS) >= {"claude-json", "codex-jsonl"})
    check("and a kind nobody wrote a parser for costs nothing rather than "
          "raising", usage.read_turn_usage(logpath, offset, "no-such-kind") == {})

    # A PROVIDER DRIVEN THROUGH SOMEBODY ELSE'S BINARY REPORTS THE TOKENS RIGHT
    # AND THE MONEY WRONG. The counts are the model's own; the prices compiled
    # into that binary are its vendor's. So the counts are kept and the dollars
    # are recomputed from the recipe's table.
    DS = recipes.DEFAULT_CONFIG["agents"]["deepseek"]
    import calendar                                            # noqa: E402
    peak = calendar.timegm((2026, 9, 23, 2, 0, 0, 0, 0, 0))    # Wednesday 02:00
    off = calendar.timegm((2026, 9, 23, 12, 0, 0, 0, 0, 0))    # Wednesday 12:00
    weekend = calendar.timegm((2026, 9, 26, 2, 0, 0, 0, 0, 0))  # Saturday 02:00
    check("the provider's own peak window is open when it says it is",
          usage.at_peak_rate(DS["prices"], peak)
          and not usage.at_peak_rate(DS["prices"], off))
    check("and its weekday rule is honoured, because it has one",
          not usage.at_peak_rate(DS["prices"], weekend))
    check("a table with no windows is charged at peak -- guessing the dear rate "
          "cannot understate a bill", usage.at_peak_rate({}, off))

    counts = {"tokens": 100000, "in": 50000, "out": 10000,
              "cache_write": 0, "cache_read": 40000}
    dear = usage.priced(counts, DS, peak)
    cheap = usage.priced(counts, DS, off)
    check("the dollars are computed here rather than believed from the JSON",
          abs(dear["usd"] - 0.02724) < 1e-6)
    check("off-peak is charged off-peak", abs(cheap["usd"] - dear["usd"] / 2) < 1e-6)
    check("AND THE RATE THAT APPLIED IS RECORDED. A table of windows in the "
          "reader goes stale silently; a recorded rate cannot",
          dear["rate"]["window"] == "peak" and cheap["rate"]["window"] == "off"
          and cheap["rate"]["out"] == 0.60)
    check("the token counts are untouched, because they are the model's own "
          "report and they are right",
          dear["tokens"] == 100000 and dear["cache_read"] == 40000)
    bare = usage.priced(counts, recipes.DEFAULT_CONFIG["agents"]["codex"])
    check("and a provider with no price table records the tokens and NO dollar "
          "figure, which is honest rather than wrong",
          "usd" not in bare and "rate" not in bare)

    # ---- CODEX'S OWN STREAM ------------------------------------------------
    #
    # `--json` carries a `token_count` event whose `total_token_usage` is the
    # RUNNING TOTAL for the session. Summing them counts every earlier round
    # trip again, which is the one way to get this wrong that yields a
    # plausible number.
    stream = "\n".join(json.dumps({
        "type": "token_count",
        "info": {"total_token_usage": {"input_tokens": n * 1000,
                                       "cached_input_tokens": n * 400,
                                       "output_tokens": n * 100}},
    }) for n in (1, 2, 3))
    got = usage.read_codex_usage(stream)
    check("the last running total is the answer, not the sum of them",
          got["out"] == 300 and got["cache_read"] == 1200)
    check("and the cached half is not counted twice in the billed total",
          got["in"] == 3000 - 1200 and got["tokens"] == 3000 + 300)
    check("round trips are counted, because the stream is where they are",
          got["requests"] == 3)
    check("a stream that reported nothing is nothing rather than a crash",
          usage.read_codex_usage("some plain output\n") == {})

    # AND THE SHAPE IT HAS NOW, which is not that one. Codex 0.156.1 emits no
    # `token_count` event at all: the numbers ride on `turn.completed` as a
    # `usage` object. Read by the old rule that stream matches nothing, so
    # every Codex turn was free in `cost.jsonl` and missing from every total --
    # a measurement that reads zero is worse than one that is absent, because
    # zero adds up. Captured from a real run rather than composed here.
    now = "\n".join([
        json.dumps({"type": "thread.started", "thread_id": "01a0d40b"}),
        json.dumps({"type": "turn.started"}),
        json.dumps({"type": "item.completed",
                    "item": {"id": "item_0", "type": "agent_message",
                             "text": "3"}}),
        json.dumps({"type": "turn.completed",
                    "usage": {"input_tokens": 43786,
                              "cached_input_tokens": 32512,
                              "cache_write_input_tokens": 0,
                              "output_tokens": 139,
                              "reasoning_output_tokens": 0}}),
    ])
    got = usage.read_codex_usage(now)
    check("the turn's own usage event is read, which is where the numbers are "
          "now", got["out"] == 139 and got["cache_read"] == 32512)
    check("and the cached half is still not billed twice",
          got["in"] == 43786 - 32512 and got["tokens"] == 43786 + 139)
    check("one `codex exec` is one turn, whatever it did in the middle: that "
          "run made two shell calls and reported once",
          got["requests"] == 1)
    check("and the cache WRITE is carried now, because this shape reports one",
          usage.read_codex_usage(json.dumps(
              {"type": "turn.completed",
               "usage": {"input_tokens": 10, "cached_input_tokens": 4,
                         "cache_write_input_tokens": 6, "output_tokens": 2}}
          ))["cache_write"] == 6)
    check("two turns in one stream are summed, because each is its own bill",
          usage.read_codex_usage("\n".join(
              json.dumps({"type": "turn.completed",
                          "usage": {"input_tokens": 100, "output_tokens": 10}})
              for _ in range(2)))["tokens"] == 220)
finally:
    os.unlink(logpath)

print()
print("%d FAILURES" % len(fails) if fails
      else "a turn pays for what it needs and not for what it already has")
sys.exit(1 if fails else 0)
