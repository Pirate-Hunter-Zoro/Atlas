"""What a turn said and what it cost.

The agent's own output is the only record of a turn: whether it failed and in
what words (`failure_reason`), what it used (`read_turn_usage`, one parser per
provider), what that cost (`priced`, off the recipe's table), and the line in
the session's `cost.jsonl` that `board cost` adds up.
"""

import json
import os
import re
import time

from tutorboard.agents import recipes
from tutorboard.course import repo as course_repo

# Failure markers, most useful first; `!!` is this file's own.
FAILURE_MARKERS = ("!! ", "error: ", "Error: ")


def result_object_error(text):
    """What an agent's own result object (`type: result`, `is_error`) says
    went wrong, or None. The last such line, since a retried turn writes two.

    A fragment of a result object is still read, but the verdict precedes the
    sentence, so a fragment without a verdict ends the scan rather than being
    guessed either way.
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
        # A fragment reporting no failure is still the newest verdict, so it
        # ends the scan before an older turn's failure.
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
    """Why the turn failed, in words, rather than its exit code.

    The agent's own result object first (marker prefixes miss a JSON line),
    then the last line that looks like a reason, capped, with the exit code
    kept on the end. `code_note` when it said nothing, never an empty banner.
    """
    said = result_object_error(text) or opencode_error(text)
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
    it is the result object `result_object_error` reads.
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
# `--output-format json` reports what a turn cost; one line per turn goes to
# `cost.jsonl` and `board cost` adds it up. `usage` there is cumulative over
# the turn's round trips, which is the number worth watching.
COST_LOG = "cost.jsonl"


def with_usage(spec, cmd):
    """The turn's command plus whatever makes this agent report its cost.
    Appended here, not in the recipe, so an old copied recipe still reports.
    Idempotent."""
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
    """What the agent said this turn cost, or {} if it did not say. Never
    raises.

    `kind` is the recipe's `usage` field, dispatching to a parser; none means
    unaccounted. Token counts come from the parser, and `priced` recomputes
    dollars from `spec`'s table, because a binary driving another vendor
    prices with its own vendor's rates.
    """
    parser = USAGE_PARSERS.get(kind)
    if not parser:
        return {}
    got = parser(turn_words(path, offset))
    return priced(got, spec) if got else got


def read_claude_usage(blob):
    """Claude Code's `--output-format json` result object."""
    # The last result object; other output shares the stream.
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
            # Everything through the model this turn: what a subscription's
            # allowance is measured in.
            "tokens": billed,
            "in": int(u.get("input_tokens") or 0),
            "out": int(u.get("output_tokens") or 0),
            "cache_write": int(u.get("cache_creation_input_tokens") or 0),
            "cache_read": int(u.get("cache_read_input_tokens") or 0),
            # Round trips: the lever a prompt can pull.
            "requests": int(d.get("num_turns") or 0),
            "usd": float(d.get("total_cost_usd") or 0.0),
            "models": sorted(models),
            "session": d.get("session_id") or "",
        }
    return {}


def read_codex_usage(blob):
    """Codex's `--json` event stream, in either of its two shapes.

    `turn.completed` carries one turn's `usage` and is summed. `token_count`
    carries a running `total_token_usage`, and only the last counts. Round
    trips are counted from events, since Codex reports none.
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
    # Where both appear, the per-turn shape wins.
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
        # `input_tokens` includes the cached part; separate them so nothing is
        # counted twice.
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
    prints a provider error only as JSON."""
    for d in reversed(opencode_events(text)):
        if d.get("type") != "error":
            continue
        err = d.get("error") or {}
        data = err.get("data") if isinstance(err.get("data"), dict) else {}
        said = data.get("message") or err.get("message") or err.get("name")
        return str(said).strip() if said else "OpenCode reported an error"
    return None


# Parser per `usage` kind; a new provider is a parser added here.
USAGE_PARSERS = {
    "claude-json": read_claude_usage,
    "codex-jsonl": read_codex_usage,
    "opencode-json": read_opencode_usage,
}


def at_peak_rate(prices, now=None):
    """Is the provider's peak window open now? Windows are UTC
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


def record_cost(live, log, turn, agent_name, fresh, usage):
    """One line per turn in `live/cost.jsonl`, and one in the log: a
    per-machine record, as the allowance belongs to this machine's account."""
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
    a workspace root whose bound session holds one."""
    path = os.path.join(where, COST_LOG)
    if not os.path.isfile(path):
        path = course_repo.session_path(where, COST_LOG) or path
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
    """`board cost`: every place in `found` that billed, one line each.
    Each is `{dir, root}`, `root` a session directory or a workspace root."""
    share = _share(_window(cfg))
    rows = [(c, read_costs(c["root"])) for c in found]
    rows = [(c, r) for c, r in rows if r]
    if not rows:
        print("no turn has reported a cost on this machine yet.")
        print("Turns record one only on a recipe whose `usage` names a "
              "parser -- `claude-json`, `codex-jsonl` or `opencode-json`; see "
              "agents/recipes.py.")
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

    Tokens lead, because a subscription's allowance is tokens; `quota_tokens`
    gives a window share. The last line compares halves: a rising cost per
    turn means context that should be read back off disk.
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
    # Per provider, only where there is more than one.
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
