"""What a turn said and what it cost.

OpenCode's `--format json` output is the only record of a turn: whether it
failed and in what words (`failure_reason`), what it used
(`read_turn_usage`), what that cost (`priced`, off the recipe's table), and
the line in the session's `cost.jsonl` that `board cost` adds up.
"""

import json
import os
import time

from tutorboard import paths
from tutorboard.agents import recipes
from tutorboard.course import repo as course_repo

# Failure markers, most useful first; `!!` is this file's own.
FAILURE_MARKERS = ("!! ", "error: ", "Error: ")


def failure_reason(text, code_note):
    """Why the turn failed, in words, rather than its exit code.

    OpenCode's own `error` event first (marker prefixes miss a JSON line),
    then the last line that looks like a reason, capped, with the exit code
    kept on the end. `code_note` when it said nothing, never an empty banner.
    """
    said = opencode_error(text)
    if said:
        return "%s (%s)" % (said[:160], code_note)
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    for line in reversed(lines[-40:]):
        for mark in FAILURE_MARKERS:
            if line.startswith(mark):
                said = line[len(mark):].strip()
                # Our own `!! exit` line, not a reason.
                if said and not said.startswith(("exit ", "timed out")):
                    return "%s (%s)" % (said[:160], code_note)
    return code_note


def turn_output(path, offset, cap=20000, line_cap=400000):
    """What this turn wrote to the log, from `offset`: the last `cap` bytes,
    except that the final line is never cut (bounded by `line_cap`), because
    a JSON event cut in half is no longer read.
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
# `--format json` reports what a turn cost; one line per turn goes to
# `cost.jsonl` and `board cost` adds it up. The counts there are summed over
# the turn's round trips, which is the number worth watching.
COST_LOG = "cost.jsonl"


def turn_words(path, offset):
    """What this turn actually printed, from `offset` on. "" if unreadable."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            fh.seek(max(0, offset))
            return fh.read(4000000)
    except OSError:
        return ""


def read_turn_usage(path, offset, spec=None):
    """What OpenCode said this turn cost, or {} if it did not say. Never
    raises. Dollars are recomputed from `spec`'s price table (`priced`)."""
    got = read_opencode_usage(turn_words(path, offset))
    return priced(got, spec) if got else got


def opencode_events(blob):
    """`opencode run --format json`, one event a line, as dicts. Never raises."""
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
    """What the model said in words this turn: the raw output, or OpenCode's
    `text` events alone, since its JSON also carries tool output verbatim."""
    events = opencode_events(said)
    if not events:
        return said or ""
    return "\n".join(str((d.get("part") or {}).get("text") or "")
                     for d in events if d.get("type") == "text")


def read_opencode_usage(blob):
    """OpenCode's `--format json` event stream: one `step_finish` per round
    trip, summed. Reasoning is billed as output. OpenCode's own `cost` is kept
    as `usd` unless the recipe has a price table.
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
    """The last OpenCode `error` event's message, or None: `opencode run`
    prints DeepSeek's error only as JSON."""
    for d in reversed(opencode_events(text)):
        if d.get("type") != "error":
            continue
        err = d.get("error") or {}
        data = err.get("data") if isinstance(err.get("data"), dict) else {}
        said = data.get("message") or err.get("message") or err.get("name")
        return str(said).strip() if said else "OpenCode reported an error"
    return None


def at_peak_rate(prices, now=None):
    """Is DeepSeek's peak window open now? Windows are UTC
    `[["01:00", "04:00"], ...]`; `peak_weekdays_only` excludes weekends. Peak
    by default, since the dear rate cannot understate a bill."""
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
    """The dollars this turn cost, from the recipe's price table, recording
    the rate that applied. Without a table, whatever the agent said; with
    neither, tokens and no dollar figure.
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


def record_cost(live, log, turn, fresh, usage):
    """One line per turn in `live/cost.jsonl`, and one in the log: a
    per-machine record, as the allowance belongs to this machine's account."""
    if not usage:
        return
    rec = dict(usage)
    rec.update({"t": time.time(), "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
                "turn": turn, "agent": recipes.NAME, "fresh": bool(fresh),
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
                     else "no price table"))
    except (OSError, ValueError):
        pass


def thousands(n):
    return "%.1fk" % (n / 1000.0) if n >= 1000 else str(n)


def read_costs(where):
    """The cost rows of `where`: a session directory holding `cost.jsonl`, or
    a workspace root whose bound session holds one."""
    path = os.path.join(where, COST_LOG)
    if not os.path.isfile(path):
        path = course_repo.session_path(where, COST_LOG) or path
    return read_jsonl(path)


def read_jsonl(path):
    """Every line of `path` that is JSON; a torn line is skipped."""
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


# A speech job with no session (a phrase made for a card) costs here.
SPEECH_LOG = "speech-cost.jsonl"


def speech_log():
    return os.path.join(paths.STATE_DIR, SPEECH_LOG)


def split_speech(rows):
    """`(turn rows, speech rows)`: a speech job (`agents/speech.record_cost`)
    is a line of its own in the same file, and is not a turn."""
    return ([t for t in rows if t.get("kind") != "speech"],
            [t for t in rows if t.get("kind") == "speech"])


def speech_line(rows):
    """One line for a place's speech jobs, or None."""
    if not rows:
        return None
    by = sorted({t.get("agent") or "?" for t in rows})
    return ("  speech: %d job(s), $%.3f (%s)"
            % (len(rows), sum(t.get("usd", 0) for t in rows), ", ".join(by)))


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


def cost_all(cfg, found, sessionless=True):
    """`board cost`: every place in `found` that billed, one line each.
    Each is `{dir, root}`, `root` a session directory or a workspace root.
    Speech jobs are shown apart from the turns, each place's on a line of its
    own, and with `sessionless` the state directory's `speech-cost.jsonl`
    too, which holds the jobs no session paid for."""
    share = _share(_window(cfg))
    split = [(c, split_speech(read_costs(c["root"]))) for c in found]
    rows = [(c, turns) for c, (turns, _spoken) in split if turns]
    spoken = [(c["dir"], said) for c, (_turns, said) in split if said]
    if sessionless:
        said = split_speech(read_jsonl(speech_log()))[1]
        if said:
            spoken.append(("no session", said))
    if not rows:
        print("no turn has reported a cost on this machine yet.")
        print("A turn records one from OpenCode's `--format json` output; "
              "see agents/usage.py.")
    else:
        print("%-22s %6s %8s %11s %10s" %
              ("where", "turns", "trips/t", "tokens/t", "total"))
        for c, r in sorted(rows, key=lambda x: -sum(t.get("tokens", 0) for t in x[1])):
            n = len(r)
            print("%-22s %6d %8.1f %11s %9.2f" %
                  (c["dir"][:22], n,
                   sum(t.get("requests", 0) for t in r) / float(n),
                   thousands(sum(t.get("tokens", 0) for t in r) / float(n)),
                   sum(t.get("usd", 0) for t in r)))
        total = sum(t.get("tokens", 0) for _, r in rows for t in r)
        print("\n%s tokens across %d turn(s) on %s%s"
              % (thousands(total), sum(len(r) for _, r in rows), recipes.this_host(),
                 share(total)))
    if spoken:
        print("\nspeech, apart from the turns:")
        for where, said in spoken:
            print("%-22s%s" % (where[:22], speech_line(said)[1:]))
        print("speech in total: %d job(s), $%.3f"
              % (sum(len(r) for _, r in spoken),
                 sum(t.get("usd", 0) for _, r in spoken for t in r)))
    return 0


def cost_report(cfg, course, per_turn=False):
    """What the turns in one workspace cost, per turn and in total.

    Tokens lead, because a subscription's allowance is tokens; `quota_tokens`
    gives a window share. The last line compares halves: a rising cost per
    turn means context that should be read back off disk.
    """
    window = _window(cfg)
    share = _share(window)
    rows, spoken = split_speech(read_costs(course["root"]))
    if not rows:
        print("%s: no turn has reported a cost here yet." % course["dir"])
        if spoken:
            print(speech_line(spoken))
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
    print("  %s tokens a turn%s, %.1f round trips a turn"
          % (thousands(tokens / float(n)), share(tokens / float(n)),
             sum(t.get("requests", 0) for t in rows) / float(n)))
    # Unpriced is said as such, never $0.00.
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
    if spoken:
        print(speech_line(spoken))
    if not window:
        print("  set `quota_tokens` in the config to see these as a share of "
              "one allowance window")
    # A rising trend means a turn carries what it should read off disk.
    if n >= 6:
        half = n // 2
        early = sum(t.get("tokens", 0) for t in rows[:half]) / float(half)
        late = sum(t.get("tokens", 0) for t in rows[half:]) / float(n - half)
        print("  first half %s a turn, second half %s -- %s"
              % (thousands(early), thousands(late),
                 "flat, which is the point" if late <= early * 1.25
                 else "RISING: a turn is carrying context it could read back"))
    return 0
