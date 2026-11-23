# Folder: scripts/experiments/primitives/breadth/
# File: run_breadth_research.py
# Purpose: Single entry point for the complete market-breadth research run.
#
# Execution from repository root:
#   python scripts/experiments/primitives/breadth/run_breadth_research.py

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SOURCE_SCRIPT = (
    PROJECT_ROOT
    / "scripts"
    / "experiments"
    / "primitives"
    / "01_research_report.py"
)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from breadth_analysis import run_breadth_analysis  # noqa: E402


def load_source_module():
    if not SOURCE_SCRIPT.is_file():
        raise FileNotFoundError(
            f"Existing primitive research module not found: {SOURCE_SCRIPT}"
        )

    spec = importlib.util.spec_from_file_location(
        "primitive_research_source",
        SOURCE_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load 01_research_report.py.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    started = datetime.now()
    print("=" * 68, flush=True)
    print("[BREADTH] MARKET BREADTH RESEARCH START", flush=True)
    print(f"[BREADTH] Project root: {PROJECT_ROOT}", flush=True)
    print("[BREADTH] Reusing the established PIT TOP50 data loader and feature logic.", flush=True)
    print("=" * 68, flush=True)

    source = load_source_module()
    source.validate_inputs()

    panel = source.load_panel()
    secids = sorted(panel["secid"].unique())

    history, calendar = source.load_adjusted_history(secids)
    frame = source.build_feature_frame(panel, history, calendar)
    frame = frame[frame["bar_available"].eq(1)].copy()

    metadata = {
        "source_script": str(SOURCE_SCRIPT),
        "panel_rows": int(len(panel)),
        "signal_rows_with_bar": int(len(frame)),
        "calendar_sessions": int(len(calendar)),
    }

    run_breadth_analysis(
        frame=frame,
        calendar=pd.DatetimeIndex(calendar),
        metadata=metadata,
    )

    elapsed = datetime.now() - started
    print(f"[BREADTH] Elapsed: {elapsed}", flush=True)


if __name__ == "__main__":
    main()
