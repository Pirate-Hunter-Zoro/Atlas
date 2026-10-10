"""Text provider: every AI provider Atlas has, tried in order until one writes the file.

The providers are Atlas's own table (`board/tutorboard/agents/recipes.py`, laid over by
`~/.config/tutor-board/config.json`), so adding or removing one there adds or removes
it here, and no vendor is load-bearing. The order is `PAPER_PROVIDERS` (a comma list of
recipe names) when set, else the board's (`recipes.chain`): its provider, then every
fallback.

`claude` goes through `text_cli`, which knows its flags: the role's model tier, turn
budget, tool grant and usage meter. Every other recipe goes through Atlas's one-shot
runner (`tutorboard.agents.oneshot`) with its own headless command. Either way the
contract is the same: the artifact is a file at `out_path`, and a provider that exits
without writing it has failed, so the next one is tried.

A `QuotaExceeded` is raised only when every provider was tried and at least one was out
of allowance: one vendor's ceiling is no longer a reason to wait.
"""

import os
import sys
from pathlib import Path

from .. import config
from ..errors import QuotaExceeded
from . import text_cli
from .base import Capability, file_contract

NAME = "chain"
CAPABILITY = Capability(writes_own_file=True, supports_tools=True, supports_web=True)
contract = file_contract

# Atlas's board, which holds the provider table: projects/Paper-Writer/../../board.
BOARD = Path(__file__).resolve().parents[4] / "board"


def _board():
    """Atlas's provider modules, imported from the board beside this project."""
    if str(BOARD) not in sys.path:
        sys.path.insert(0, str(BOARD))
    from tutorboard.agents import oneshot, recipes
    return oneshot, recipes


def names():
    """The recipe names to try, in order."""
    said = [n.strip() for n in os.environ.get("PAPER_PROVIDERS", "").split(",")
            if n.strip()]
    if said:
        return said
    _, recipes = _board()
    return recipes.chain(recipes.load_config())


def produce(prompt, out_path, role, log_fn=None):
    """Have the first provider that can write the artifact at `out_path` do it.
    Returns a short rationale. Raises `QuotaExceeded` when nobody could and a
    ceiling was among the reasons, else `RuntimeError`."""
    def note(msg):
        if log_fn:
            log_fn(msg)

    oneshot, recipes = _board()
    cfg = recipes.load_config()
    tried, ceiling = [], False
    for name in names():
        if name == "claude":
            try:
                return text_cli.produce(prompt, out_path, role, log_fn=log_fn)
            except QuotaExceeded as exc:
                ceiling = True
                tried.append(f"claude: {exc}")
            except RuntimeError as exc:
                tried.append(f"claude: {exc}")
            note(f"claude could not write {out_path.name}; trying the next provider")
            continue
        if out_path.exists():
            out_path.unlink()                     # so "file present" means "this run"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        got = oneshot.run(prompt, str(config.PROJECT_ROOT), timeout=role.timeout,
                          cfg=cfg, names=[name], done=lambda _n: out_path.exists())
        if got["ok"]:
            if tried:
                note(f"{name} wrote {out_path.name} after: {'; '.join(tried)[:300]}")
            return (got["text"] or "")[:2000]
        for who, why in got["tried"]:
            ceiling = ceiling or "allowance" in why
            tried.append(f"{who}: {why}")
    said = "; ".join(tried)[:600] or "no provider is configured"
    if ceiling:
        raise QuotaExceeded(f"every provider is out or failing: {said}", source="model")
    raise RuntimeError(f"no provider wrote {out_path.name}: {said}")
