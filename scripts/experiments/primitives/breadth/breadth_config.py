# Folder: scripts/experiments/primitives/breadth/
# File: breadth_config.py
# Purpose: Shared configuration for the independent market-breadth research block.

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
PRIMITIVE_ROOT = PROJECT_ROOT / "scripts" / "experiments" / "primitives"
SOURCE_REPORT_SCRIPT = PRIMITIVE_ROOT / "01_research_report.py"

PANEL_PATH = PROJECT_ROOT / "data" / "processed" / "top50" / "top50_panel.parquet"
ADJUSTED_DB_PATH = PROJECT_ROOT / "data" / "processed" / "moex_daily_adjusted.sqlite"
OUTPUT_DIR = PROJECT_ROOT / "data" / "interim" / "primitive_research" / "breadth"

HORIZONS = (5, 10, 20)
BREADTH_FEATURES = (
    "breadth_sma20",
    "breadth_sma50",
    "breadth_sma200",
    "breadth_change_5",
    "breadth_change_20",
)
OUTCOME_TYPES = ("mean_return", "median_return", "positive_share")

SUBPERIODS = (
    ("2005-2012", "2005-01-01", "2012-12-31"),
    ("2013-2019", "2013-01-01", "2019-12-31"),
    ("2020-2026", "2020-01-01", "2026-12-31"),
)

MIN_FORWARD_COVERAGE = 20
HAC_MAX_LAGS_CAP = 19
ROLLING_WINDOW = 252
ROLLING_MIN_PERIODS = 126
QUANTILE_COUNT = 5
DOUBLE_SORT_MARKET_BUCKETS = 5
DOUBLE_SORT_BREADTH_BUCKETS = 3
