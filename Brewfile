# The Mac's system tools. `bash scripts/setup.sh` runs `brew bundle` on this file
# joined with every subject's own Brewfile (~/.local/state/atlas-setup/Brewfile.all).
# A line's comment says what it is for, where the name does not. A
# tool only one subject uses goes in that subject's Brewfile.

# the board and the paper builders
brew "python"
brew "texlive"       # latex, pdflatex, xelatex, latexmk
brew "dvisvgm"
brew "poppler"       # pdftotext, pdftoppm
brew "ghostscript"   # gs, which textbook ingest renders pages with
brew "tesseract"     # OCR of scanned textbook pages
brew "pandoc"
brew "node"          # the test suite's headless browser
brew "gh"
brew "tailscale"
cask "font-dejavu"   # `board build`'s PDF face: it has the ₀ ρ ≈ − a paper uses

# speech: the board's local listener and voices (board/tutorboard/agents/speech.py)
brew "whisper-cpp"   # whisper-cli; scripts/speech-model.sh fetches its model
brew "ffmpeg"        # a WebM take, which afconvert cannot read
brew "espeak-ng"     # Irish (ga), which macOS has no voice for

# the workspaces' code. Not elan: scripts/setup.sh installs it into ~/.elan for
# a Lean subject, on every machine, and a second one here would shadow it.
brew "uv"            # every pyproject.toml and uv.lock
brew "mise"          # every subject's mise.toml and mise.lock: its pinned toolchains
brew "libomp"        # OpenMP, which xgboost's and lightgbm's Mac wheels load
brew "go"            # board Go-check integration tests
