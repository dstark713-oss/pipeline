from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SOURCE = (
    PROJECT_ROOT
    / "scripts"
    / "experiments"
    / "model1_replication"
    / "scripts_for_tool"
)
if str(TOOL_SOURCE) not in sys.path:
    sys.path.insert(0, str(TOOL_SOURCE))

from daily_inference import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
