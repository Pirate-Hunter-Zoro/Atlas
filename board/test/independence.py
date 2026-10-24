#!/usr/bin/env python3
"""Subject discovery and board regressions work without real projects."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("suite_runner", HERE / "run.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

with tempfile.TemporaryDirectory(prefix="subject-discovery-") as tmp:
    root = Path(tmp)
    assert runner.subject_suites(tmp) == []
    for name in ("projects/Zeta", "courses/Delta"):
        target = root / name / "tests/board/check.py"
        target.parent.mkdir(parents=True)
        target.write_text("raise SystemExit(0)\n")
        (target.parent / "_helper.py").write_text("raise RuntimeError('helper executed')\n")
    suites = runner.subject_suites(tmp)
    assert len(suites) == 2
    for suite in suites:
        assert Path(suite.cwd) == root / Path(suite.name).parts[0] / Path(suite.name).parts[1]
        subprocess.run(suite.argv, cwd=suite.cwd, check=True)
    shutil.move(root / "projects/Zeta", root / "projects/Renamed")
    assert any("Renamed" in s.name for s in runner.subject_suites(tmp))
    shutil.rmtree(root / "courses")
    shutil.rmtree(root / "projects")
    assert runner.subject_suites(tmp) == []

    # Real board code and tests, but no courses or projects to borrow fixtures from.
    shutil.copytree(HERE.parent, root / "board", ignore=shutil.ignore_patterns(
        "node_modules", "__pycache__", "*.pyc", ".venv", "data"))
    (root / "courses").mkdir()
    (root / "projects").mkdir()
    (root / ".gitignore").write_text("/sessions/\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-qm", "empty subject inventory"], check=True)
    env = dict(os.environ)
    env.pop("TUTORBOARD_COURSES", None)
    env.pop("TUTORBOARD_SESSION", None)
    env.pop("TUTORBOARD_TURN", None)
    for name in ("rules_fence", "writing_up", "subjects"):
        result = subprocess.run([sys.executable, str(root / "board/test" / (name + ".py"))],
                                cwd=root / "board", env=env, capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, name + "\n" + result.stdout + result.stderr
        print("ok subject-free " + name)
print("subjects can be added, renamed, or removed without changing the test runner")
