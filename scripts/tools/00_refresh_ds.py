
# Folder: scripts/tools/
# File: 00_refresh_ds.py

from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFRESH_SCRIPT = (
    PROJECT_ROOT
    / "scripts"
    / "dataset"
    / "fresh"
    / "refresh_pipeline.py"
)


def main() -> int:
    if not REFRESH_SCRIPT.is_file():
        print(
            f"ERROR: Refresh script not found: {REFRESH_SCRIPT}",
            file=sys.stderr,
        )
        return 1

    print("=" * 60)
    print("DATASET REFRESH")
    print("=" * 60)
    print(f"Project: {PROJECT_ROOT}")
    print(f"Runner:  {REFRESH_SCRIPT}")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, str(REFRESH_SCRIPT), *sys.argv[1:]],
        cwd=PROJECT_ROOT,
        check=False,
    )

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
