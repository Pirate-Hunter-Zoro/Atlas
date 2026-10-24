"""How the harness reaches a model, and what each kind of work is allowed to spend.

Text comes from whichever of Atlas's AI providers can write it (`chain.py`): the
board's provider table, walked in order until one writes the artifact. Claude runs
through `text_cli`, which knows its model tiers and flags; any other recipe runs
through Atlas's one-shot runner. No vendor is load-bearing, so one going away or
running out costs nothing but a fallback. `PAPER_PROVIDERS` pins the order for this
project alone.

## The role table

Each kind of work (gathering, drafting, review, ...) has one row in
`config.TEXT_ROLES`: the model tier Claude runs it at, its turn budget, its timeout and
its tool grant, side by side where the numbers can be compared. `role(name)` reads it.
"""

from .. import config
from . import chain

# The text provider: every provider Atlas has, in order.
TEXT = chain


class Role:
    """What one kind of work is allowed to spend, and how it is expected to work."""

    def __init__(self, name, spec):
        self.name = name
        self.model = spec.get("model") or config.MODEL
        self.max_turns = spec.get("max_turns", 30)
        self.timeout = spec.get("timeout", 1200)
        self.tools = tuple(spec.get("tools", ("Read", "Write")))
        # Whether this role's whole input is inlined in the prompt, so the model reads
        # nothing and writes once. On an agentic CLI that is roughly ten times fewer
        # input tokens for the same artifact at the same model; see
        # `base.file_contract`.
        self.oneshot = bool(spec.get("oneshot"))

    def __repr__(self):                                          # pragma: no cover
        return f"<Role {self.name} model={self.model}>"


def role(name):
    """Resolve one role from the config table. An unknown name is a programming error,
    not a runtime condition, so this raises rather than defaulting."""
    try:
        spec = config.TEXT_ROLES[name]
    except KeyError:
        raise KeyError(
            f"unknown text role {name!r}; known roles: "
            f"{', '.join(sorted(config.TEXT_ROLES))}") from None
    return Role(name, spec)


def text():
    """The text provider: Atlas's providers, in order."""
    return TEXT


def describe():
    """One line for the startup log, so a broken setup is visible in the first three
    lines of a daemon log rather than inferred from a failure much later."""
    sources = ", ".join(str(p) for p in config.SOURCE_DIRS) or "(none configured)"
    try:
        order = ", ".join(chain.names()) or "(none configured)"
    except Exception as exc:                                     # noqa: BLE001
        order = f"(unreadable: {exc})"
    return (f"text: {order}, in that order; claude at {config.MODEL} | evidence "
            f"sources: {sources} | output: {config.OUT_DIR}")
