"""Run maintained offline unit tests used to gate pre-release builds.

The two legacy suites excluded here still target retired APIs. Their status is
documented in docs/releases/v2.0.0-rc.1.md; this is not a full-suite pass.
"""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    raise SystemExit(subprocess.call([
        sys.executable, "-m", "pytest", "-q", "tests/unit",
        "--ignore=tests/unit/test_cover_templates.py",
        "--ignore=tests/unit/test_database.py",
        *sys.argv[1:],
    ], cwd=ROOT))
