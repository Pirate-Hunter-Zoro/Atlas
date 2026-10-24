#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup.sh -- build every workspace's environment, on whichever machine this is.
#
#     bash scripts/setup.sh
#
# 1. The system tools. On a Mac, `brew bundle` on the union of the root
#    Brewfile and every subject's own, sorted and deduplicated into
#    ~/.local/state/atlas-setup/Brewfile.all (rewritten only when it changes,
#    board/tutorboard/toolplan.py), installing what is missing and moving
#    nothing that is there (--no-upgrade). Never --cleanup: the machine holds
#    formulae no Brewfile names, and one a deleted subject declared stays
#    installed, named by `board doctor`. Elsewhere,
#    uv is installed into ~/.local/bin when it is not on the PATH, and so is Go:
#    from conda-forge into ~/.local/goenv where Slurm is (the cluster has no Go
#    module and blocks dl.google.com), from go.dev into ~/.local/go elsewhere.
#    Nothing needs root.
# 2. Every workspace, found the way the board finds them (`subjects.all`),
#    never from a list. ai-config, the one private repository nested in Atlas,
#    is reported when this machine has not cloned it. A workspace is built by
#    what it holds:
#      pyproject.toml   uv sync, with the `test` extra, and the `cluster` extra
#                       only where Slurm exists
#      lean-toolchain   its own scripts/setup.sh when it has one. Otherwise
#                       elan, installed into ~/.elan when it is missing; the
#                       prebuilt cache, when lake-manifest.json asks for the
#                       library that ships one; then lake build
#      go.mod           go mod download
#    and by what it pins, each counted at its root and one directory down
#    (never in target/, build/, .dart_tool/, .venv/, node_modules/, zig-out/,
#    .zig-cache/ or zig-pkg/):
#      mise.toml        mise trust, then mise install --locked <its tools>,
#                       which installs only what mise.lock records (with a
#                       URL for this platform; `mise lock` writes it)
#      Cargo.toml       mise exec -- cargo fetch --locked
#      pubspec.yaml     mise exec -- flutter pub get --enforce-lockfile
#      build.zig.zon    mise exec -- zig build --fetch, only when the nearest
#                       mise.toml pins zig (else "zig skipped"); it is its
#                       own lockfile, holding each dependency's hash
#    A pin moves only by a commit of mise.toml and mise.lock.
#    On a Mac only: elsewhere a marker's subject says it was skipped.
# 3. The subjects' tool descriptors, <subject>/tools/<name>.sh: each one this
#    role uses and lacks is installed (scripts/tools.sh install). Mac only.
#
# Idempotent: a second run changes nothing and says so. One line per workspace;
# what each step printed is in ~/.local/state/atlas-setup/<workspace>.log.
# ---------------------------------------------------------------------------
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="${XDG_STATE_HOME:-$HOME/.local/state}/atlas-setup"
mkdir -p "$LOGS"

# launchd and a bare ssh hand over a short PATH; the tools live in these.
for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin" "$HOME/.local/go/bin" "$HOME/.elan/bin"; do
  [ -d "$d" ] && case ":$PATH:" in *":$d:"*) ;; *) PATH="$d:$PATH" ;; esac
done
# mise's shims last, so a subject's pinned python never stands in for the
# python3 this script and the board run.
case ":$PATH:" in *":$HOME/.local/share/mise/shims:"*) ;; *) PATH="$PATH:$HOME/.local/share/mise/shims" ;; esac
export PATH

# board/tutorboard/toolplan.py, which reads the Brewfiles, markers and descriptors.
plan() { (cd "$ROOT/board" && TUTORBOARD_COURSES="$ROOT" python3 -B -m tutorboard.toolplan "$@" --atlas "$ROOT"); }

SLURM=0
command -v sbatch >/dev/null 2>&1 && SLURM=1
# mise and the tool descriptors are a Mac's: brew is where mise comes from,
# and a descriptor's installer is for a host or a coding laptop.
MAC=0
[ "$(uname -s)" = Darwin ] && MAC=1
failed=0

line() { printf '%-32s %s\n' "$1" "$2"; }

# ---- 1. system tools --------------------------------------------------------
if [ "$(uname -s)" = Darwin ] && command -v brew >/dev/null 2>&1; then
  if ! union="$(plan union --write 2>"$LOGS/brew.log")"; then
    line "Brewfile" "FAILED -- the union was not written; $LOGS/brew.log"; failed=1
  elif brew bundle install --no-upgrade --file="$LOGS/Brewfile.all" >"$LOGS/brew.log" 2>&1; then
    line "Brewfile" "ok (Brewfile.all $union)"
  else
    line "Brewfile" "FAILED -- $LOGS/brew.log"; failed=1
  fi
else
  if ! command -v uv >/dev/null 2>&1; then
    if curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh >"$LOGS/uv.log" 2>&1 \
        && command -v uv >/dev/null 2>&1; then
      line "uv" "installed in ~/.local/bin"
    else
      line "uv" "FAILED -- $LOGS/uv.log"; failed=1
    fi
  fi
  # The cluster blocks dl.google.com, so there Go comes from conda-forge, and
  # modules come straight from their repositories (GOPROXY=direct), because
  # proxy.golang.org is Google's too.
  if ! command -v go >/dev/null 2>&1 && [ "$SLURM" = 1 ]; then
    conda="$(command -v conda || ls -d /opt/apps/easybuild/software/Anaconda3/*/bin/conda 2>/dev/null | tail -1)"
    if [ -n "$conda" ] \
        && "$conda" create -y -q -p "$HOME/.local/goenv" -c conda-forge go >"$LOGS/go.log" 2>&1 \
        && mkdir -p "$HOME/.local/bin" \
        && ln -sf "$HOME/.local/goenv/bin/go" "$HOME/.local/goenv/bin/gofmt" "$HOME/.local/bin/" \
        && PATH="$HOME/.local/bin:$PATH" && export PATH \
        && command -v go >/dev/null 2>&1; then
      line "go" "installed $(go env GOVERSION) from conda-forge in ~/.local/goenv"
    else
      line "go" "FAILED -- $LOGS/go.log"; failed=1
    fi
  elif ! command -v go >/dev/null 2>&1; then
    case "$(uname -m)" in x86_64) goarch=amd64 ;; aarch64|arm64) goarch=arm64 ;; *) goarch="" ;; esac
    gover="$(curl -fsS 'https://go.dev/dl/?mode=json' 2>>"$LOGS/go.log" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["version"])' 2>>"$LOGS/go.log")"
    if [ -n "$goarch" ] && [ -n "$gover" ] \
        && curl -fsSL "https://go.dev/dl/$gover.linux-$goarch.tar.gz" -o "$LOGS/go.tar.gz" 2>>"$LOGS/go.log" \
        && rm -rf "$HOME/.local/go" && mkdir -p "$HOME/.local/bin" \
        && tar -C "$HOME/.local" -xzf "$LOGS/go.tar.gz" 2>>"$LOGS/go.log" \
        && ln -sf "$HOME/.local/go/bin/go" "$HOME/.local/go/bin/gofmt" "$HOME/.local/bin/" \
        && PATH="$HOME/.local/go/bin:$PATH" && export PATH \
        && command -v go >/dev/null 2>&1; then
      rm -f "$LOGS/go.tar.gz"
      line "go" "installed $gover in ~/.local/go"
    else
      line "go" "FAILED -- $LOGS/go.log"; failed=1
    fi
  fi
  if [ "$SLURM" = 1 ] && command -v go >/dev/null 2>&1 \
      && [ "$(go env GOPROXY)" != direct ]; then
    go env -w GOPROXY=direct
  fi
fi

# ---- 2. the workspaces -----------------------------------------------------
# ai-config is the one private repository nested inside Atlas; a machine that
# never cloned it is told the command that brings it in.
if [ ! -e "$ROOT/ai-config/.git" ]; then
  line "ai-config" "not cloned -- bash board/bootstrap.sh"; failed=1
fi

workspaces="$(cd "$ROOT/board" && TUTORBOARD_COURSES="$ROOT" python3 -c '
from tutorboard import subjects
for w in subjects.all():
    print(w["id"])
')" || { line "workspaces" "FAILED -- board/tutorboard/subjects.py did not answer"; exit 1; }

# Does this pyproject.toml declare the optional extra named $2?
has_extra() {
  awk -v want="$2" '
    /^\[/ { inside = ($0 == "[project.optional-dependencies]") ; next }
    inside && $1 == want && $2 == "=" { found = 1 }
    END { exit !found }' "$1"
}

# elan, Lean's toolchain manager, from its official installer into ~/.elan,
# when it is missing. --no-modify-path: no shell profile is edited, and this
# run puts ~/.elan/bin on its own PATH. --default-toolchain none: each
# workspace's lean-toolchain names its own, and elan fetches it on first use.
need_elan() {
  command -v elan >/dev/null 2>&1 && return 0
  local tmp ok=1
  tmp="$(mktemp -d)" || return 1
  curl -sSfL https://elan.lean-lang.org/elan-init.sh -o "$tmp/elan-init.sh" \
    && sh "$tmp/elan-init.sh" -y --no-modify-path --default-toolchain none && ok=0
  rm -rf "$tmp"
  case ":$PATH:" in *":$HOME/.elan/bin:"*) ;; *) PATH="$HOME/.elan/bin:$PATH"; export PATH ;; esac
  [ "$ok" = 0 ] && command -v elan >/dev/null 2>&1
}

# A Lean workspace, in a subshell so its cd stays there: the prebuilt cache
# only when the manifest pins the library that ships one (`lake exe cache get`
# is that library's executable), then the build.
lean_build() (
  cd "$1" || exit 1
  if grep -q -E '"name": *"mathlib"' lake-manifest.json 2>/dev/null; then
    lake exe cache get || exit 1
  fi
  lake build
)

# Every marker, one line each: subject, marker, lockfile, directory.
markers="$(plan markers)" || { line "markers" "FAILED -- board/tutorboard/toolplan.py did not answer"; failed=1; }
TAB="$(printf '\t')"

# The directories in subject $1 that hold marker $2.
marker_dirs() {
  printf '%s\n' "$markers" | awk -F"$TAB" -v id="$1" -v m="$2" '$1 == id && $2 == m { print $4 }'
}

for id in $workspaces; do
  ws="$ROOT/$id"
  log="$LOGS/${id//\//_}.log"
  : >"$log"
  did=""
  bad=0

  if [ -f "$ws/pyproject.toml" ]; then
    extras=()
    has_extra "$ws/pyproject.toml" test && extras+=(--extra test)
    [ "$SLURM" = 1 ] && has_extra "$ws/pyproject.toml" cluster && extras+=(--extra cluster)
    if (cd "$ws" && uv sync --locked ${extras[@]+"${extras[@]}"}) >>"$log" 2>&1; then
      did="uv sync${extras[*]:+ ${extras[*]}}"
    else
      did="uv sync"; bad=1
    fi
  fi

  if [ -f "$ws/lean-toolchain" ]; then
    if [ -f "$ws/scripts/setup.sh" ]; then
      bash "$ws/scripts/setup.sh" >>"$log" 2>&1 || bad=1
    else
      { need_elan && lean_build "$ws"; } >>"$log" 2>&1 || bad=1
    fi
    did="${did:+$did, }lean"
  fi

  if [ -f "$ws/go.mod" ]; then
    (cd "$ws" && go mod download) >>"$log" 2>&1 || bad=1
    did="${did:+$did, }go mod download"
  fi

  # The pinned toolchains first, then what builds with them. Mac only.
  if [ "$MAC" = 0 ]; then
    if [ -n "$(printf '%s\n' "$markers" | awk -F"$TAB" -v id="$id" '$1 == id')" ]; then
      did="${did:+$did, }mise toolchains skipped (Mac only)"
    fi
  else
    while IFS= read -r d; do
      [ -n "$d" ] || continue
      # Named: --locked fails on any tool mise.lock lacks, and the owner's
      # global config's tools are in no subject's lock.
      pins=()
      while IFS= read -r t; do [ -n "$t" ] && pins+=("$t"); done < <(plan pinned "$d")
      [ "${#pins[@]}" -gt 0 ] || continue
      { mise trust --quiet "$d/mise.toml" && (cd "$d" && mise install --locked "${pins[@]}"); } >>"$log" 2>&1 || bad=1
      case "$did" in *"mise install"*) ;; *) did="${did:+$did, }mise install" ;; esac
    done < <(marker_dirs "$id" mise.toml)
    while IFS= read -r d; do
      [ -n "$d" ] || continue
      (cd "$d" && mise exec -- cargo fetch --locked) >>"$log" 2>&1 || bad=1
      case "$did" in *"cargo fetch"*) ;; *) did="${did:+$did, }cargo fetch" ;; esac
    done < <(marker_dirs "$id" Cargo.toml)
    while IFS= read -r d; do
      [ -n "$d" ] || continue
      (cd "$d" && mise exec -- flutter pub get --enforce-lockfile) >>"$log" 2>&1 || bad=1
      case "$did" in *"flutter pub get"*) ;; *) did="${did:+$did, }flutter pub get" ;; esac
    done < <(marker_dirs "$id" pubspec.yaml)
    # Zig is pre-1.0, so a fetch runs only under a zig the nearest mise.toml
    # pins, never one mise exec would borrow from the PATH or a global config.
    while IFS= read -r d; do
      [ -n "$d" ] || continue
      pd="$ws"; [ -f "$d/mise.toml" ] && pd="$d"
      if plan pinned "$pd" | grep -qx zig; then
        (cd "$d" && mise exec -- zig build --fetch) >>"$log" 2>&1 || bad=1
        case "$did" in *"zig build --fetch"*) ;; *) did="${did:+$did, }zig build --fetch" ;; esac
      else
        echo "$d/build.zig.zon: no zig pin in $pd/mise.toml, not fetched" >>"$log"
        case "$did" in *"zig skipped"*) ;; *) did="${did:+$did, }zig skipped (no zig pin)" ;; esac
      fi
    done < <(marker_dirs "$id" build.zig.zon)
  fi

  if [ -z "$did" ]; then
    line "$id" "nothing to build"
  elif [ "$bad" = 0 ]; then
    line "$id" "ok ($did)"
  else
    line "$id" "FAILED ($did) -- $log"; failed=1
  fi
done

# ---- 3. the tool descriptors ------------------------------------------------
# Installs what is missing and never removes anything; tools.sh says the rest.
# Mac only: a descriptor's installer is for a host or a coding laptop.
if [ "$MAC" = 0 ]; then
  line "tools" "skipped (the descriptors are Mac only)"
elif said="$(bash "$ROOT/scripts/tools.sh" install 2>&1)"; then
  line "tools" "ok ($(printf '%s\n' "$said" | tail -1))"
else
  printf '%s\n' "$said" >"$LOGS/tools-install.log"
  line "tools" "FAILED -- $LOGS/tools-install.log"; failed=1
fi

exit "$failed"
