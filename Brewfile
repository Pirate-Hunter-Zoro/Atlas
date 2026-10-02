# The Mac's system tools. `bash scripts/setup.sh` runs `brew bundle` on this file;
# on the cluster the same tools come from modules or a user-level install of uv
# and elan. board/README.md section 6 of the setup says what each is for.

# the board and the paper builders
brew "python"
brew "texlive"       # latex, pdflatex, xelatex, latexmk
brew "dvisvgm"
brew "poppler"       # pdftotext, pdftoppm
brew "pandoc"
brew "node"          # the test suite's headless browser
brew "gh"
brew "tailscale"

# the workspaces' code. Not elan: practice/Lean-Theorem-Proving/scripts/setup.sh
# installs it into ~/.elan on both machines, and a second one here would shadow it.
brew "uv"            # every pyproject.toml and uv.lock
brew "libomp"        # OpenMP, which xgboost's and lightgbm's Mac wheels load
brew "go"            # practice/Algo-Solutions
