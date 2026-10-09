# Paper-Writer rules

- Run the suite (`board check`) before claiming anything works.
- A model call goes through its stage's one named seam function; a stage that reaches a provider any other way hits the live API. A gate never calls a model and never does I/O.
- gates/ladder.py is the only gate that can refuse correct work, on purpose. Read the failure in its docstring before relaxing a threshold.
- Points are decided at planning time and nowhere else.
- An edit anchor matches character for character: hand the editor gates/prose.py's raw form, never its tidy one.
- The ledger gatekeeper is all-or-nothing.
- Nothing has a terminal failure state; a stall is retried forever.
- Changing a threshold in config.py changes its comment too.
- Test a proposed rule against REFERENCE_MANUSCRIPT in tests/test_gates.py. A rule that refuses it is wrong.
- A gate that reports green after checking nothing is worse than one that fires wrongly.
- A share needs a denominator: ask what a rule reports on a three-paragraph section, and whether its scope is the section, the document or the packet.
- Comments and docstrings say why, not what.
- Commits carry no assistant attribution.
