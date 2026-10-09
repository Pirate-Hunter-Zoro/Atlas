"""What a turn said and what it cost.

The agent's own output is the only record of a turn: whether it failed and in
what words (`failure_reason`), what it used (`read_turn_usage`, one parser per
provider), what that cost (`priced`, off the recipe's table), and the line in
`live/cost.jsonl` that `tutor cost` adds up.
"""

import json
import os
import re
import time

from tutorboard.agents import recipes
from tutorboard.course import repo as course_repo

# What a turn said on its way down, in the order a person would find useful.
# `!!` is this file's own marker for something that went wrong; a tutor writes
# its own reason in the other two forms.
FAILURE_MARKERS = ("!! ", "error: ", "Error: ")


def result_object_error(text):
    """What an agent's own result object says went wrong, or None.

    Claude Code's `--output-format json` closes a turn with one line carrying
    `type: result`; on a failure `is_error` is true and `result` holds the
    sentence. The recipes that drive a third-party provider through that same
    binary report the same way, so this is the one place a provider-side fault
    -- a refused model, a reset connection, a rejected key -- says so in words.

    The LAST such line, because a turn retried as a fresh one writes two.

    AND A RESULT OBJECT TOO LONG TO HAVE SURVIVED WHOLE still says what
    happened, which is the second line of defence rather than the first.
    `turn_output` now pulls its seek back to the start of the final line, so an
    ordinary long turn arrives here parseable -- but a log rotated under the
    daemon, or an offset past the line, still hands over a fragment that no
    longer opens with a brace, which is why neither test is what admits a line
    here. What is read off a fragment is read directly, and the ORDER matters:
    measured on a real result line, `"is_error"` sits at byte 932 and `"result"`
    at 1006, so a front cut loses the verdict before it loses the sentence. A
    fragment with no verdict in it therefore ends the scan rather than being
    guessed at in either direction -- guessing failure marks a good turn as
    broken, and guessing success is the silence this whole path exists to end.
    """
    for line in reversed((text or "").splitlines()):
        line = line.strip()
        if '"result"' not in line:
            continue
        if line.startswith("{"):
            try:
                d = json.loads(line)
            except ValueError:
                d = None
            if d is not None:
                if d.get("type") != "result" or not d.get("is_error"):
                    return None
                got = d.get("result")
                return got.strip() if isinstance(got, str) and got.strip() else None
        # The tail of a result object, or an ordinary log line that happens to
        # hold the word: only the first is answered for, and `type` says which
        # it is. A fragment that reports no failure is still the newest verdict,
        # so it ends the scan rather than letting an older turn's failure through.
        if not re.search(r'"type"\s*:\s*"result"', line):
            continue
        if not re.search(r'"is_error"\s*:\s*true', line):
            return None
        got = re.search(r'"result"\s*:\s*"((?:[^"\\]|\\.)*)"', line)
        try:
            return json.loads('"%s"' % got.group(1)).strip() if got else None
        except ValueError:
            return None
    return None


def failure_reason(text, code_note):
    """Why the turn failed, in words, rather than the number it exited with.

    `exit 1` is what the student's iPad used to say, and it is a dead end: it is
    true, it is the same for every cause, and there is nothing a person holding
    the board can do with it except go and find somebody who can read a log. The
    turn almost always said something better than that on its way down -- "every
    model on the chain deliberated instead of writing a card", "no provider key
    on this machine" -- and that sentence is already in the log, one line above
    the number nobody can use.

    So: the last thing it said that looks like a reason, capped to something that
    fits in the chrome, with the exit code kept on the end for whoever does open
    the log. `code_note` when it said nothing at all, which is a real outcome and
    must not become an empty banner.

    THE AGENT'S OWN VERDICT IS ASKED FOR FIRST, because the marker prefixes miss
    it entirely: an agent reporting `--output-format json` puts its reason in a
    `result` field inside one long JSON line that starts with a brace, so the
    line reads as ordinary output and a turn killed by `API Error: Connection
    dropped (ECONNRESET)` reaches the board as `exit 1`. That is the same banner
    every other cause wears, which is the dead end this function exists to end.
    """
    said = result_object_error(text) or opencode_error(text)
    if said:
        return "%s (%s)" % (said[:160], code_note)
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    for line in reversed(lines[-40:]):
        for mark in FAILURE_MARKERS:
            if line.startswith(mark):
                said = line[len(mark):].strip()
                # `!! exit 1` is this function's own output from a previous turn,
                # or the line written just above the call. Not a reason.
                if said and not said.startswith(("exit ", "timed out")):
                    return "%s (%s)" % (said[:160], code_note)
    return code_note


def turn_output(path, offset, cap=20000, line_cap=400000):
    """What this turn wrote to the log, which is everything it managed to say.

    An agent's stdout and stderr both go straight into the log file, so the only
    record of WHY a turn failed is the stretch of that file it has just written.
    The tail of it is enough, and the cap is there because a turn that dumped a
    repository into its output must not be read back into memory whole.

    AND THE LAST LINE IS NEVER CUT, WHATEVER THE CAP SAYS, because it is the one
    line whose every field is load-bearing: the client's result object, which is
    where `result_object_error` reads whether the turn actually failed. That
    object is long exactly when the turn had a lot to say, and a blind seek to
    `size - cap` lands in the middle of it -- measured on a real turn, the tail
    kept `"result"` and lost the `"is_error"` that comes before it, so a failure
    read back as a clean turn. So the seek is pulled back to the start of the
    final line when the cap would have cut it, bounded by `line_cap` for the
    same reason the cap exists at all.
    """
    try:
        size = os.path.getsize(path)
        floor = max(0, offset)
        with open(path, "rb") as fh:
            back = max(floor, size - line_cap)
            fh.seek(back)
            tail = fh.read()
            cut = tail.rstrip(b"\n").rfind(b"\n")
            last = back + cut + 1 if cut >= 0 else back
            fh.seek(min(max(floor, size - cap), last))
            return fh.read().decode("utf-8", "replace")
    except OSError:
        return ""

# ---------------------------------------------------------------------------
# What a turn cost, measured rather than argued about
# ---------------------------------------------------------------------------
# Every decision in this file about reading, resuming and re-reading is a
# decision about money, and until now not one of them could be checked. The
# numbers that justified them were read out of `~/.claude.json` and a session
# transcript by hand, after the fact, by somebody who knew where to look -- so
# the next change to any of it would have been guesswork wearing a comment.
#
# `--output-format json` makes the agent say what its turn cost. This writes it
# down, one line per turn, and `tutor cost` adds it up. The cost of the
# accounting is zero: it is a field in output the daemon was already logging.
#
# `usage` in that JSON is cumulative for the whole invocation -- every round trip
# the turn took, not the last one. Measured: a five-round-trip turn reports
# cache_read 152,020, which is the sum of its five requests and not any one of
# them. That is exactly the number worth watching, because ROUND TRIPS x CONTEXT
# is what a turn is billed for.
COST_LOG = "cost.jsonl"


def with_usage(spec, cmd):
    """The turn's command, plus whatever makes this agent report what it cost.

    Appended here rather than written into the recipe, because a machine's
    config file overrides `agents` one level deep and a config holding a
    verbatim copy of an older recipe would otherwise stop reporting without
    saying so. Idempotent: a recipe that already carries the flag is left alone.
    """
    extra = [a for a in (spec.get("usage_args") or []) if a not in cmd]
    extra += [a for a in (spec.get("extra_args") or []) if a not in cmd]
    return list(cmd) + extra

def turn_words(path, offset):
    """What this turn actually printed, from `offset` on. "" if unreadable."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            fh.seek(max(0, offset))
            return fh.read(4000000)
    except OSError:
        return ""


def read_turn_usage(path, offset, kind, spec=None):
    """What the agent said this turn cost, or {} if it did not say.

    `kind` is the recipe's `usage` field and it is a DISPATCH rather than an
    equality test, which is the difference between a table of three providers
    and a table of one. An agent whose `usage` names no parser -- `usage: none`,
    or nothing at all -- costs nothing here and is simply not accounted for.
    Never raises: this is bookkeeping beside a lesson, and a lesson does not
    stop because a number could not be parsed.

    `spec` is the recipe, and it is here for the dollars rather than the tokens.
    A provider driven through somebody else's binary reports the token counts
    correctly -- they are the model's own -- and the price WRONG, because the
    prices compiled into that binary are its vendor's. So the counts come from
    the parser and `priced` recomputes the money off the recipe's own table
    wherever it has one.
    """
    parser = USAGE_PARSERS.get(kind)
    if not parser:
        return {}
    got = parser(turn_words(path, offset))
    return priced(got, spec) if got else got


def read_claude_usage(blob):
    """Claude Code's `--output-format json` result object."""
    # The last line of the turn that is a result object. Not the only line:
    # warnings, and anything the agent printed on its way, share this stream.
    for line in reversed(blob.splitlines()):
        line = line.strip()
        if not line.startswith("{") or '"result"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "result":
            continue
        u = d.get("usage") or {}
        models = d.get("modelUsage") or {}
        billed = (int(u.get("input_tokens") or 0)
                  + int(u.get("output_tokens") or 0)
                  + int(u.get("cache_creation_input_tokens") or 0)
                  + int(u.get("cache_read_input_tokens") or 0))
        return {
            # Everything that went through the model this turn. On a
            # subscription this is the number that matters: what runs out is a
            # five-hour allowance, and a percentage of it is computed from
            # tokens rather than from dollars.
            "tokens": billed,
            "in": int(u.get("input_tokens") or 0),
            "out": int(u.get("output_tokens") or 0),
            "cache_write": int(u.get("cache_creation_input_tokens") or 0),
            "cache_read": int(u.get("cache_read_input_tokens") or 0),
            # Round trips. This is the lever a prompt can actually pull, and the
            # one that turned a turn into $4.49 when it also ran `board wait`.
            "requests": int(d.get("num_turns") or 0),
            "usd": float(d.get("total_cost_usd") or 0.0),
            "models": sorted(models),
            "session": d.get("session_id") or "",
        }
    return {}


def read_codex_usage(blob):
    """Codex's `--json` event stream, in either of the two shapes it has had.

    TWO SHAPES, because the stream belongs to the client and the client moved.
    Both are read: which one arrives depends on the binary installed on this
    machine, and nothing here gets to insist on a version.

    * `turn.completed`, carrying a `usage` object. One per `codex exec`
      invocation -- measured on 0.156.1 against a run that made two shell
      calls, which produced three `item.completed` events and exactly one
      `turn.completed`. SUMMED, because each is its own turn's bill.
    * `token_count`, carrying `total_token_usage`, which is the RUNNING TOTAL
      for the session. The LAST of those is the answer, and summing them would
      count every earlier round trip again -- the one way to get this wrong
      that produces a plausible number.

    A stream in the first shape read by the second rule reports NOTHING: there
    is no `token_count` line to match, so every Codex turn was free in
    `cost.jsonl` and absent from every total.

    Round trips are counted rather than reported, because Codex reports no such
    number: one event per turn in the new shape, one per trip in the old.
    """
    fresh, last, trips = [], None, 0
    for line in blob.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        if '"turn.completed"' in line:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            got = d.get("usage")
            if isinstance(got, dict):
                fresh.append(got)
            continue
        if "token_count" not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        info = d.get("info") or d.get("msg") or d
        total = (info.get("total_token_usage")
                 or (info.get("info") or {}).get("total_token_usage"))
        if isinstance(total, dict):
            last = total
            trips += 1
    # The new shape wins where a stream somehow carries both: a client that
    # reports `usage` on the turn is reporting THIS turn, and a running total
    # beside it would be the whole session's.
    if fresh:
        def summed(field):
            return sum(int(u.get(field) or 0) for u in fresh)
        got_in, cached = summed("input_tokens"), summed("cached_input_tokens")
        out = summed("output_tokens")
        written = summed("cache_write_input_tokens")
        trips = len(fresh)
    elif last:
        got_in = int(last.get("input_tokens") or 0)
        cached = int(last.get("cached_input_tokens") or 0)
        out = int(last.get("output_tokens") or 0)
        written = 0
    else:
        return {}
    return {
        # `input_tokens` INCLUDES the cached part in this report, so the two are
        # separated here to mean what they mean everywhere else in this file --
        # and the billed total must not add them twice.
        "tokens": got_in + out,
        "in": max(0, got_in - cached),
        "out": out,
        "cache_write": written,
        "cache_read": cached,
        "requests": trips,
        "usd": 0.0,
        "models": [],
        "session": "",
    }


def opencode_events(blob):
    """`opencode run --format json`, one event a line, as dicts. Never raises.

    Every event is `{type, timestamp, sessionID, part}` -- or `error` in place
    of `part` -- and the types are `step_start`, `step_finish`, `tool_use`,
    `text`, `reasoning` and `error`. Anything else in the log is skipped.
    """
    out = []
    for line in (blob or "").splitlines():
        line = line.strip()
        if not line.startswith("{") or '"type"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("type") and "sessionID" in d:
            out.append(d)
    return out


def turn_text(said):
    """What the model said in words this turn: the raw output, or for OpenCode
    the `text` events alone.

    OpenCode's JSON carries every tool's output too -- a file the turn read,
    verbatim -- so a scan of the whole stream for a provider's placeholder
    would fire on any turn that opened a document quoting it.
    """
    events = opencode_events(said)
    if not events:
        return said or ""
    return "\n".join(str((d.get("part") or {}).get("text") or "")
                     for d in events if d.get("type") == "text")


def read_opencode_usage(blob):
    """OpenCode's `--format json` event stream.

    ONE `step_finish` PER ROUND TRIP, AND THEY ARE SUMMED: each carries its own
    trip's `tokens` and `cost`, not a running total. Measured against a real
    DeepSeek session: `total = input + output + reasoning + cache.read +
    cache.write`, `input` excludes the cache reads, and reasoning is billed at
    the output rate -- so it is counted as output here. The `cost` OpenCode
    adds up is kept as `usd` and is replaced wherever the recipe has a price
    table, because it is one flat rate with no peak window.
    """
    trips, session = [], ""
    for d in opencode_events(blob):
        session = d.get("sessionID") or session
        part = d.get("part") or {}
        if d.get("type") == "step_finish" and isinstance(part.get("tokens"), dict):
            trips.append(part)
    if not trips:
        return {}

    def summed(*path):
        n = 0
        for part in trips:
            got = part.get("tokens")
            for key in path:
                got = got.get(key) if isinstance(got, dict) else None
            n += int(got or 0)
        return n
    got_in, out = summed("input"), summed("output") + summed("reasoning")
    read, written = summed("cache", "read"), summed("cache", "write")
    return {
        "tokens": got_in + out + read + written,
        "in": got_in,
        "out": out,
        "cache_write": written,
        "cache_read": read,
        "requests": len(trips),
        "usd": round(sum(float(p.get("cost") or 0.0) for p in trips), 6),
        "models": [],
        "session": session,
    }


def opencode_error(text):
    """What an OpenCode `error` event says went wrong, or None. The last one.

    `opencode run` exits 1 on a provider error and prints the reason only as a
    JSON event -- `{"type": "error", "error": {"name", "data": {"message"}}}` --
    which no marker prefix in `failure_reason` matches. The provider's own
    sentence is the useful one: an invalid key, an empty balance, a model
    that does not exist.
    """
    for d in reversed(opencode_events(text)):
        if d.get("type") != "error":
            continue
        err = d.get("error") or {}
        data = err.get("data") if isinstance(err.get("data"), dict) else {}
        said = data.get("message") or err.get("message") or err.get("name")
        return str(said).strip() if said else "OpenCode reported an error"
    return None


# Which parser reads which agent's report. A provider is a parser added beside
# the others; nothing else in this file learns a new name.
USAGE_PARSERS = {
    "claude-json": read_claude_usage,
    "codex-jsonl": read_codex_usage,
    "opencode-json": read_opencode_usage,
}


def at_peak_rate(prices, now=None):
    """Is the provider's peak window open right now? Peak unless told otherwise.

    The windows are the provider's own, in UTC, as `[["01:00", "04:00"], ...]`,
    and `peak_weekdays_only` says whether Saturday and Sunday count. Peak is the
    default answer for a table with no windows on it, because guessing the dear
    rate cannot understate a bill.
    """
    spans = (prices or {}).get("peak_utc")
    if not spans:
        return True
    t = time.gmtime(now if now is not None else time.time())
    if (prices or {}).get("peak_weekdays_only") and t.tm_wday >= 5:
        return False
    mins = t.tm_hour * 60 + t.tm_min
    for span in spans:
        try:
            a, b = [int(x[:2]) * 60 + int(x[3:5]) for x in span]
        except (ValueError, IndexError, TypeError):
            continue
        if a <= mins < b or (b < a and (mins >= a or mins < b)):
            return True
    return False


def priced(usage, spec, now=None):
    """The dollars this turn cost, from the RECIPE's price table.

    Three outcomes and they are all deliberate:

      - a recipe with a price table gets a figure computed here, and the RATE
        THAT APPLIED is recorded beside it. A provider whose price has a peak
        and an off-peak window can only be said honestly one of two ways, and
        recording what applied beats encoding the windows in the reader: a
        table of windows goes stale silently, a recorded rate cannot;
      - a recipe with none keeps whatever the agent itself said, which for
        Claude Code against Anthropic is right;
      - and one with neither records the tokens and NO dollar figure, which is
        the honest answer rather than a wrong number.
    """
    prices = (spec or {}).get("prices")
    if not prices:
        return usage
    peak = at_peak_rate(prices, now)
    rate = prices.get("peak" if peak else "off") or {}
    per = lambda n, k: (usage.get(n, 0) / 1000000.0) * float(rate.get(k, 0) or 0)
    out = dict(usage)
    out["usd"] = round(per("in", "in") + per("cache_write", "cache_write")
                       + per("cache_read", "cache_read") + per("out", "out"), 6)
    out["rate"] = {"window": "peak" if peak else "off",
                   "in": rate.get("in"), "cache_write": rate.get("cache_write"),
                   "cache_read": rate.get("cache_read"), "out": rate.get("out")}
    return out


def record_cost(live, log, turn, agent_name, fresh, usage):
    """One line per turn in `live/cost.jsonl`, and one in the log.

    `live/` is not tracked, so this is a per-machine record of a per-machine
    bill, which is the right scope: the allowance that paid for it belongs to
    this machine's account.
    """
    if not usage:
        return
    rec = dict(usage)
    rec.update({"t": time.time(), "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
                "turn": turn, "agent": agent_name, "fresh": bool(fresh),
                "host": recipes.this_host()})
    try:
        with open(os.path.join(live, COST_LOG), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError:
        pass
    try:
        log.write("-- turn %d: %s tokens over %d round trip(s) "
                  "(cache read %s, cache written %s, out %s), %s\n"
                  % (turn, thousands(rec.get("tokens", 0)), rec["requests"],
                     thousands(rec["cache_read"]), thousands(rec["cache_write"]),
                     thousands(rec["out"]),
                     ("$%.3f at the %s rate" % (rec["usd"], rec["rate"]["window"]))
                     if rec.get("rate") else
                     ("$%.3f" % rec["usd"]) if rec.get("usd")
                     else "no price table for this provider"))
    except (OSError, ValueError):
        pass


def thousands(n):
    return "%.1fk" % (n / 1000.0) if n >= 1000 else str(n)


def read_costs(where):
    """The cost rows of `where`: a session directory holding `cost.jsonl`, or
    a workspace root whose session holds one."""
    path = os.path.join(where, COST_LOG)
    if not os.path.isfile(path):
        path = course_repo.session_path(where, COST_LOG)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except (OSError, ValueError):
        out = []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for l in fh:
                    l = l.strip()
                    if not l:
                        continue
                    try:
                        out.append(json.loads(l))
                    except ValueError:
                        pass
        except OSError:
            pass
        return out

def _window(cfg):
    try:
        return int(cfg.get("quota_tokens") or 0)
    except (TypeError, ValueError):
        return 0


def _share(window):
    def share(tokens):
        """That many tokens as a share of one allowance window, if calibrated."""
        return ("  (%.2f%% of a window)" % (100.0 * tokens / window)) if window else ""
    return share


def cost_all(cfg, found):
    """`tutor cost`: every place in `found` that billed, one line each.
    Each is `{dir, root}`, `root` a session directory or a workspace root."""
    share = _share(_window(cfg))
    rows = [(c, read_costs(c["root"])) for c in found]
    rows = [(c, r) for c, r in rows if r]
    if not rows:
        print("no turn has reported a cost on this machine yet.")
        print("Turns record one only on a recipe whose `usage` names a "
              "parser -- `claude-json`, `codex-jsonl` or `opencode-json`; see "
              "`tutor --agents`.")
        return 0
    print("%-22s %6s %8s %11s %10s  %s" %
          ("where", "turns", "trips/t", "tokens/t", "total", "who"))
    for c, r in sorted(rows, key=lambda x: -sum(t.get("tokens", 0) for t in x[1])):
        n = len(r)
        print("%-22s %6d %8.1f %11s %9.2f  %s" %
              (c["dir"][:22], n,
               sum(t.get("requests", 0) for t in r) / float(n),
               thousands(sum(t.get("tokens", 0) for t in r) / float(n)),
               sum(t.get("usd", 0) for t in r),
               ", ".join(sorted({t.get("agent") or "?" for t in r}))))
    total = sum(t.get("tokens", 0) for _, r in rows for t in r)
    print("\n%s tokens across %d turn(s) on %s%s"
          % (thousands(total), sum(len(r) for _, r in rows), recipes.this_host(),
             share(total)))
    return 0


def cost_report(cfg, course, per_turn=False):
    """What the turns in one workspace cost, per turn and in total.

    TOKENS is the headline, not dollars. On a subscription what runs out is a
    five-hour allowance, and a percentage of that is computed from what went
    through the model. Set `quota_tokens` in the config and this says what share
    of a window a turn took. The LAST line is the one to read: a second half that
    costs more per turn than the first means a turn is carrying context it should
    have read back off disk.
    """
    window = _window(cfg)
    share = _share(window)
    rows = read_costs(course["root"])
    if not rows:
        print("%s: no turn has reported a cost here yet." % course["dir"])
        return 0

    if per_turn:
        print("%-19s %5s %-7s %6s %10s %10s %8s %8s %8s" %
              ("when", "turn", "session", "trips", "tokens", "cacheread",
               "cachewrit", "out", "cost"))
        for t in rows:
            print("%-19s %5s %-7s %6d %10s %10s %10s %8s %8.3f" %
                  (t.get("iso", "?"), t.get("turn", "?"),
                   "fresh" if t.get("fresh") else "resumed",
                   t.get("requests", 0), thousands(t.get("tokens", 0)),
                   thousands(t.get("cache_read", 0)),
                   thousands(t.get("cache_write", 0)), thousands(t.get("out", 0)),
                   t.get("usd", 0)))
        print()

    n = len(rows)
    tokens = sum(t.get("tokens", 0) for t in rows)
    fresh = sum(1 for t in rows if t.get("fresh"))
    print("%s — %d turn(s) on %s, %d of them their own session"
          % (course["dir"], n, recipes.this_host(), fresh))
    # SPLIT BY WHO TAUGHT IT, which is the whole reason to have three. A line
    # per provider, and it is drawn only where there is more than one -- a
    # single-provider evening already has its totals below.
    by_agent = {}
    for t in rows:
        by_agent.setdefault(t.get("agent") or "?", []).append(t)
    if len(by_agent) > 1:
        for name, r in sorted(by_agent.items(),
                              key=lambda kv: -sum(t.get("tokens", 0) for t in kv[1])):
            money = sum(t.get("usd", 0) for t in r)
            print("  %-10s %3d turn(s), %8s tokens, %s"
                  % (name, len(r), thousands(sum(t.get("tokens", 0) for t in r)),
                     ("$%.2f" % money) if money else "no price table — tokens only"))
    print("  %s tokens a turn%s, %.1f round trips a turn"
          % (thousands(tokens / float(n)), share(tokens / float(n)),
             sum(t.get("requests", 0) for t in rows) / float(n)))
    # $0.00 is a claim about money. A turn with no price table and no figure
    # of its own is unpriced, and the line says that instead.
    priced_rows = [t for t in rows if t.get("rate") or t.get("usd")]
    money = sum(t.get("usd", 0) for t in rows)
    print("  %s tokens in total%s, %s"
          % (thousands(tokens), share(tokens),
             "no price table — tokens only" if not priced_rows
             else ("$%.2f" % money) if len(priced_rows) == n
             else "$%.2f for %d priced turn(s); %d unpriced"
             % (money, len(priced_rows), n - len(priced_rows))))
    dear = max(rows, key=lambda t: t.get("tokens", 0))
    print("  dearest turn: %s tokens%s over %d round trips (%s)"
          % (thousands(dear.get("tokens", 0)), share(dear.get("tokens", 0)),
             dear.get("requests", 0), dear.get("iso", "?")))
    if not window:
        print("  set `quota_tokens` in the config to see these as a share of "
              "one allowance window")
    # The number this whole arrangement exists to hold flat. A rising trend here
    # means a turn is carrying something it should have read back off disk.
    if n >= 6:
        half = n // 2
        early = sum(t.get("tokens", 0) for t in rows[:half]) / float(half)
        late = sum(t.get("tokens", 0) for t in rows[half:]) / float(n - half)
        print("  first half %s a turn, second half %s -- %s"
              % (thousands(early), thousands(late),
                 "flat, which is the point" if late <= early * 1.25
                 else "RISING: a turn is carrying context it could read back"))
    return 0
