#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# test/all.sh -- run every suite.
#
#   bash test/all.sh
#
# Several suites drive the pages in a real DOM, which needs jsdom. That is a
# development-only dependency and the board never touches it, so rather than
# asking anyone to remember an install step, this fetches it on first run and
# carries on without it if there is no network.
#
# A forgotten setup step is a step that does not happen. The tests that use a
# real DOM are the ones that caught the defects a stub DOM waved through, so
# they are exactly the ones that must not be the easy ones to skip.
# ---------------------------------------------------------------------------
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE" || exit 1

if ! command -v node >/dev/null 2>&1; then
  echo "node is not installed; the test suite needs it (the board itself does not)"
  exit 1
fi

if ! node -e "require('jsdom')" >/dev/null 2>&1; then
  if command -v npm >/dev/null 2>&1; then
    echo "installing jsdom (development only, not needed to run the board)…"
    npm install --no-save --silent jsdom >/dev/null 2>&1 \
      && echo "  installed" \
      || echo "  could not install — the real-DOM suites will skip"
  else
    echo "no npm; the real-DOM suites will skip"
  fi
  echo
fi

SUITES="markdown macros hidden chrome theme pages modes typeface export shot interactive plane adopt chain sheets filed answer mine half feedback typed seam hanging panic steering sizing staying link hub review walk who clip map address marks notify library deck handover door shelf"
fails=0
skipped=0

for t in $SUITES; do
  printf '%-12s ' "$t"
  out="$(node "test/$t.js" 2>&1)"
  code=$?
  last="$(printf '%s' "$out" | tail -1)"
  if printf '%s' "$out" | grep -q '^skip'; then
    skipped=$((skipped + 1))
    echo "skipped ($(printf '%s' "$out" | head -1 | sed 's/^skip *//'))"
  elif [ $code -ne 0 ]; then
    fails=$((fails + 1))
    echo "FAILED"
    printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
  else
    echo "$last"
  fi
done

printf '%-12s ' "offline"
if out="$(node test/offline.js 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

# The tracked-file audit runs EARLY, because what it guards -- no PHI, no
# 50-megabyte artifact, no other author's book inside a public repository -- is
# the only failure in this suite that cannot be undone by fixing it afterwards.
printf '%-12s ' "tracked"
if out="$(python3 test/tracked.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

# And beside it, the other thing a document can be wrong about: not what git
# carries, but whether a sentence about the code is still true. It runs here
# because both audit the repository rather than the board, and a stale address
# in a briefing is read by an assistant before anybody notices.
printf '%-12s ' "truthful"
if out="$(python3 test/truthful.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep -A6 '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "choice"
if out="$(python3 test/choice.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "keeping"
if out="$(python3 test/keeping.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "untouched"
if out="$(python3 test/beside.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "catchup"
if out="$(python3 test/catchup.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "tailnet"
if out="$(python3 test/address.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "transcript"
if out="$(python3 test/transcript.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "begin"
if out="$(python3 test/begin.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "anchor"
if out="$(python3 test/anchor.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "annotate"
if out="$(python3 test/annotate.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "teaching"
if out="$(python3 test/teaching.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "whole"
if out="$(python3 test/whole.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "plainly"
if out="$(python3 test/plainly.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "colibri"
if out="$(python3 test/colibri.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "carry"
if out="$(python3 test/carry.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "hopping"
if out="$(python3 test/hopping.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "elsewhere"
if out="$(python3 test/elsewhere.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "direction"
if out="$(python3 test/direction.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "aiming"
if out="$(python3 test/aiming.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "library"
if out="$(python3 test/library.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "shelf"
if out="$(python3 test/shelf.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "revising"
if out="$(python3 test/revising.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "plan"
if out="$(python3 test/plan.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "walk"
if out="$(python3 test/walk.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "beside"
if out="$(python3 test/beside_lesson.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "writing-up"
if out="$(python3 test/writing_up.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "meeting"
if out="$(python3 test/meeting.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "map"
if out="$(python3 test/map.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "review"
if out="$(python3 test/review.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "shot"
if out="$(python3 test/shot.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "document"
if out="$(python3 test/document.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "showing"
if out="$(python3 test/showing.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "paper"
if out="$(python3 test/paper.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "homework"
if out="$(python3 test/homework.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "burn"
if out="$(python3 test/burn.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "tokens"
if out="$(python3 test/tokens.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "chapter"
if out="$(python3 test/chapter.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "resume"
if out="$(python3 test/resume.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "egress"
if out="$(python3 test/egress.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "limit"
if out="$(python3 test/limit.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "serving"
if out="$(python3 test/serving.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "node"
if out="$(python3 test/node.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "reasoning"
if out="$(python3 test/reasoning.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "waking"
if out="$(python3 test/waking.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "vocabulary"
if out="$(python3 test/vocabulary.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "wedged"
if out="$(python3 test/wedged.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "keys"
if out="$(python3 test/keys.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "seeing"
if out="$(python3 test/seeing.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "provider"
if out="$(python3 test/provider.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "agents"
if out="$(python3 test/agents.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

printf '%-12s ' "perpetual"
if out="$(python3 test/perpetual.py 2>&1)"; then
  printf '%s\n' "$out" | tail -1
else
  fails=$((fails + 1))
  echo "FAILED"
  printf '%s\n' "$out" | grep '^FAIL' | sed 's/^/             /'
fi

# THE OTHER HALF OF THE DOCUMENT SEAM. `manuscript.job` writes `## Revision` and
# `## Delivery`; `jobspec.revision` and `jobspec.landing` read them. `revising.py`
# checks that direction. Nothing checked the reverse: a change to a field name in
# the factory passes the board's suite and breaks the board silently, and only the
# board's suite is a habit. So the habit runs both.
#
# Skipped, loudly, where the factory is not checked out -- the board is a program
# in its own right and must not need a sibling repository to be testable.
printf '%-12s ' "factory"
FACTORY="$HERE/../projects/Paper-Writer"
if [ -d "$FACTORY/paperwriter" ]; then
  if out="$(cd "$FACTORY" && python3 -m unittest discover -s tests 2>&1)"; then
    printf '%s\n' "$out" | grep -E '^Ran [0-9]+ tests' | sed 's/$/, and they pass/'
  else
    fails=$((fails + 1))
    echo "FAILED"
    printf '%s\n' "$out" | grep -E '^(FAIL|ERROR):' | sed 's/^/             /'
  fi
else
  skipped=$((skipped + 1))
  echo "skipped (Paper-Writer is not checked out here)"
fi

printf '%-12s ' "macros/tex"
if python3 tools/sync-macros.py --check >/dev/null 2>&1; then
  echo "TeX and KaTeX know the same commands"
else
  fails=$((fails + 1))
  echo "FAILED — run: python3 tools/sync-macros.py"
fi

echo
if [ "$fails" -eq 0 ]; then
  echo "all suites passed${skipped:+ ($skipped skipped)}"
else
  echo "$fails suite(s) failed"
fi
exit "$fails"
