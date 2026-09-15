#!/usr/bin/env python3
"""A figure the pipeline made, on the glass -- and nothing else out of the tree.

    `results/counterfactual_pipeline/<contrast>/propensity_by_arm.png` exists
    and cannot be put on the board. `reading.py` offers PDFs only and refuses
    `results` by name; nothing serves an image out of a workspace. The only
    route a figure had to a lesson was somebody copying it into
    `live/inbox/uploads/` -- a second copy of a file the next job overwrites.

Opening a route into a workspace's own directories is the largest of these
changes and the one with the most ways to go wrong, so this suite is about what
must NOT happen rather than about the figure arriving.

Four things, and each of them is a way the feature turns into a defect:

  * A PATH FROM A BROWSER NEVER REACHES A FILESYSTEM. What arrives is an id,
    compared against the ids of the figures discovery actually found. Same rule
    as `reading.find` and `walk.resolve`, and the same reason: the alternative
    is a query parameter carrying a repo-relative path, which is a traversal
    waiting to be written.

  * THE FENCE HOLDS HERE TOO. `research/PSYCH-ASR/phi/` is session content, and
    a route that serves images out of a workspace is the second place that has
    to be refused by name. `tutorboard/fenced.py` is the one list.

  * IT IS BOUNDED. TRD-EHR's results tree holds 676 PNGs. A drawer is not a file
    manager and a payload polled four times a second is not a directory walk.

  * AND IT IS NOT CACHED. A figure is rebuilt at the same name by the next job,
    so a cached one is last week's result wearing this week's label -- which is
    the one failure a figure on a board must not have, because it is being
    looked at in order to decide something.
"""

import json
import os
import re
import shutil
import socket
import struct
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zlib
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import fenced, sense                              # noqa: E402
from tutorboard.course import results, repo as course_repo        # noqa: E402
from tutorboard.server.handler import Handler                     # noqa: E402
from tutorboard.server.hub import Hub                             # noqa: E402
from tutorboard.server.tikz import TikzWorker                     # noqa: E402

fails = []


def check(label, cond):
    print(("ok   " if cond else "FAIL ") + label)
    if not cond:
        fails.append(label)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def get(port, path):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path))
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def png_bytes(width=64, height=64):
    """A real PNG, big enough to clear the size floor.

    Written out here rather than drawn: this suite is about the route and the
    refusals, and needing matplotlib to test them would mean they never run.
    Noise rather than a flat colour, because a flat one compresses to a couple
    of hundred bytes and the size floor would refuse it -- which would be the
    suite testing its own fixture.
    """
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload
                + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))
    head = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + os.urandom(width * 3) for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head)
            + chunk(b"IDAT", zlib.compress(raw, 1)) + chunk(b"IEND", b""))


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


BIG = png_bytes()


# ---------------------------------------------------------------------------
# a workspace shaped like the one this is for
# ---------------------------------------------------------------------------
TMP = tempfile.mkdtemp(prefix="showing-")
WS = os.path.join(TMP, "TRD-EHR")
os.makedirs(WS)
with open(os.path.join(WS, "tutorboard.json"), "w", encoding="utf-8") as fh:
    json.dump({"name": "TRD-EHR"}, fh)

# The figure this change exists for, written once per contrast under the SAME
# filename -- which is the reason an id cannot come from a basename.
for contrast in ("bupropion_vs_ssri", "bupropion_vs_snri", "snri_vs_ssri"):
    write(os.path.join(WS, "results", "counterfactual_pipeline", contrast,
                       "propensity_by_arm.png"), BIG)
write(os.path.join(WS, "figures", "roc_curve.png"), BIG)
write(os.path.join(WS, "tables", "table_one.png"), BIG)

# And everything that must not be offered.
write(os.path.join(WS, "results", "phi", "turn_table.png"), BIG)
write(os.path.join(WS, "results", "cohort", "raw", "waveform.png"), BIG)
write(os.path.join(WS, "notebooks", "scratch.png"), BIG)          # not a result dir
write(os.path.join(WS, "results", "spacer.png"), b"\x89PNG\r\n\x1a\ntiny")
write(os.path.join(WS, "results", "summary.csv"), b"a,b\n1,2\n")
write(os.path.join(WS, "results", "deep", "a", "b", "c", "buried.png"), BIG)

repo = course_repo.Repo(WS)
with open(repo.state_path, "w", encoding="utf-8") as fh:
    json.dump({"course": "TRD-EHR"}, fh)

results._cache.clear()
found = results.figures(WS)
ids = [f["id"] for f in found]
rels = [f["rel"] for f in found]


# ---------------------------------------------------------------------------
# 1. what is offered, and what is not
# ---------------------------------------------------------------------------
print("\n-- an allowlist of trees, and a fence behind it --")

check("the figure this exists for is offered",
      [r for r in rels if r.endswith("counterfactual_pipeline/"
                                     "bupropion_vs_ssri/propensity_by_arm.png")])
check("and so is one in each of the other result directories",
      "figures/roc_curve.png" in rels and "tables/table_one.png" in rels)
check("a picture outside the result directories is not a result",
      not [r for r in rels if "notebooks" in r])

check("A FENCED DIRECTORY IS REFUSED INSIDE AN ALLOWED TREE",
      not [r for r in rels if "/phi/" in r])
check("and at any depth under one, not only at the top",
      not [r for r in rels if "/raw/" in r])
check("which is the same list the manuscript factory refuses",
      fenced.refused("results/phi/turn_table.png")
      and fenced.refused("results/cohort/raw/waveform.png")
      and not fenced.refused("results/counterfactual_pipeline/x.png"))

check("a file too small to be a plot is not offered",
      not [r for r in rels if "spacer" in r])
check("and neither is something that is not a picture at all",
      not [r for r in rels if r.endswith(".csv")])
check("a figure buried deeper than a result is not offered",
      not [r for r in rels if "buried" in r])


# ---------------------------------------------------------------------------
# 2. the id: unique, and the same one tomorrow
# ---------------------------------------------------------------------------
print("\n-- an id is what a card keeps, so it is stable and it is unique --")

three = [f for f in found if f["rel"].endswith("propensity_by_arm.png")]
check("three figures written under one filename get three ids",
      len(three) == 3 and len(set(f["id"] for f in three)) == 3)
check("and each says which one it is, because the drawer shows three rows",
      sorted(f["where"] for f in three) == [
          "counterfactual_pipeline/bupropion_vs_snri",
          "counterfactual_pipeline/bupropion_vs_ssri",
          "counterfactual_pipeline/snri_vs_ssri"])
check("an id is a function of the path and nothing else, so a card written "
      "today still resolves next month",
      results.ident("results/a/b.png") == results.ident("results/a/b.png")
      and results.ident("results/a/b.png") != results.ident("results/c/b.png"))
check("and a path too long to fit in one is still uniquely named",
      len(results.ident("results/" + "x" * 300 + "/plot.png")) <= results.MAX_ID
      and results.ident("results/" + "x" * 300 + "/plot.png")
      != results.ident("results/" + "y" * 300 + "/plot.png"))
check("every id is one the route will accept",
      all(re.match(r"^[a-z0-9-]{1,%d}$" % results.MAX_ID, i) for i in ids))


# ---------------------------------------------------------------------------
# 3. bounded, in both directions
# ---------------------------------------------------------------------------
print("\n-- bounded, because a results tree has hundreds in it --")

for i in range(60):
    write(os.path.join(WS, "results", "many", "plot_%02d.png" % i), png_bytes())
results._cache.clear()
lots = results.figures(WS)
check("a drawer is offered %d figures and no more" % results.MAX_FIGURES,
      len(lots) == results.MAX_FIGURES)
check("newest first, because the one being asked about is the one that changed",
      all(lots[i]["at"] >= lots[i + 1]["at"] for i in range(len(lots) - 1)))
check("so what the cap drops is the oldest, not an arbitrary two dozen",
      not [f for f in lots if f["rel"].endswith("table_one.png")])
# Taken away again, so the sections below are about a workspace with figures in
# it rather than about the flood.
shutil.rmtree(os.path.join(WS, "results", "many"))
results._cache.clear()

started = time.time()
results._cache.clear()
results.figures(WS)
first = time.time() - started
started = time.time()
results.figures(WS)
check("and the answer is remembered rather than re-walked on every payload",
      time.time() - started < max(first, 0.001))
check("for the same window as every other discovery on this board",
      results.CACHE_SECONDS == 30)


# ---------------------------------------------------------------------------
# 4. a real board, and a name from a browser
# ---------------------------------------------------------------------------
print("\n-- the client names an id; it never names a path --")

worker = TikzWorker(repo)
hub = Hub(repo, worker)
hub.payload = json.dumps({})
PORT = free_port()
httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
httpd.daemon_threads = True
httpd.repo = repo
httpd.hub = hub
threading.Thread(target=httpd.serve_forever, daemon=True).start()

real = [f for f in results.figures(WS)
        if f["rel"].endswith("bupropion_vs_ssri/propensity_by_arm.png")]
check("the figure this change exists for has an id to ask for", bool(real))
if real:
    status, heads, body = get(PORT, "/result/" + real[0]["id"])
    check("an id the workspace offers is served, as a picture",
          status == 200 and body.startswith(b"\x89PNG")
          and heads.get("Content-Type") == "image/png")
    check("and not with a cache header, because the next job overwrites it",
          "max-age" not in (heads.get("Cache-Control") or ""))

for evil in ("/result/../../../../etc/passwd",
             "/result/..%2f..%2fetc%2fpasswd",
             "/result/results/summary.csv",
             "/result/" + "a" * 200,
             "/result/PROPENSITY_BY_ARM",
             "/result/propensity_by_arm.png",
             "/result/",
             "/result/nothing-by-that-name"):
    status, _h, _b = get(PORT, evil)
    check("refused: %s" % evil, status == 404)

# A figure that IS on disk, inside a fenced directory, asked for by the id it
# would have had. The refusal is the fence and not the lookup failing by luck.
status, _h, _b = get(PORT, "/result/" + results.ident("results/phi/turn_table.png"))
check("and an id naming a figure inside the fence is refused too", status == 404)


# ---------------------------------------------------------------------------
# 5. the payload, the briefing, and the cache rule
# ---------------------------------------------------------------------------
print("\n-- what the board is told, and what the tutor is told --")

built = hub.build()
check("the board's payload carries the figures", bool(built.get("results"))
      and len(built["results"]["figures"]) == len(results.figures(WS)))
check("each with a name, a place and a date the drawer can show",
      all(f.get("name") and f.get("iso") is not None
          for f in built["results"]["figures"]))
check("and never with the path, because the board addresses one by id",
      all("rel" not in f for f in built["results"]["figures"]))

line = sense.results_sense(repo)
check("a tutor is told the figures exist and how to put one in a card",
      "/result/" in line and real and real[0]["id"] in line)
check("and told a figure is something to ask about rather than an explanation",
      "under it" in line.lower())
check("and never handed the address of one inside the fence",
      results.ident("results/phi/turn_table.png") not in line)

empty = os.path.join(TMP, "Galois-Theory")
os.makedirs(os.path.join(empty, "chapters"))
check("a workspace with no results sends nothing rather than an empty group",
      results.status(type("R", (), {"root": empty})()) is None
      and sense.results_sense(type("R", (), {"root": empty})()) == "")

sw = open(os.path.join(ROOT, "web", "sw.js"), encoding="utf-8").read()
live = re.search(r"var LIVE = /(.+)/;", sw)
check("the service worker sends the figure route to the network, always",
      bool(live) and re.match(live.group(1), "/result/anything"))
check("which is the rule it already has for a document rebuilt at one name",
      bool(live) and re.match(live.group(1), "/download/homework"))
check("and the shell version was bumped, or the app serves its cached copy",
      'VERSION = "board-shell-v' in sw)

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a figure goes on the glass, and the tree stays where it is")
