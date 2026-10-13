"""Run this project's unittest suite from any checkout or directory."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
sys.exit(subprocess.call([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=root))
