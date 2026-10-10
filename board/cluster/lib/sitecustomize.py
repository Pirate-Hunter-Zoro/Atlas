"""sitecustomize.py -- every Python a relay recipe starts reports its failure.

The relay's wrapper (`jobs.wrapper`) and `relay_trap.sh` put this directory
on PYTHONPATH, and Python imports `sitecustomize` at startup, so
`relay_hook.install` runs before any entrypoint without one of them
importing it. A conda env's own sitecustomize, which this
file shadows, is run after it. Nothing here may stop a job: every failure is
swallowed.
"""

import os
import sys

try:
    import relay_hook
    relay_hook.install()
except Exception:                                             # noqa: BLE001
    pass


def _chain():
    here = os.path.dirname(os.path.abspath(__file__))
    import importlib.machinery
    import importlib.util
    rest = [p for p in sys.path if os.path.abspath(p or os.curdir) != here]
    spec = importlib.machinery.PathFinder.find_spec("sitecustomize", rest)
    if spec is None or not spec.origin or spec.loader is None:
        return
    if os.path.abspath(spec.origin) == os.path.abspath(__file__):
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)


try:
    _chain()
except Exception:                                             # noqa: BLE001
    pass
