# Folder: scripts/experiments/ml_1/rolling_statistical_moments/
# File: config.py
# Purpose: Configuration for the Rolling Statistical Moments experiment.

from pathlib import Path

def _find_project_root() -> Path:
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        if (parent / ".git").exists() or (parent / "data").exists():
            return parent
    parents = script_path.parents
    return parents[min(4, len(parents) - 1)]


PROJECT_ROOT = _find_project_root()

PANEL_PATH = (
    PROJECT_ROOT / "data" / "processed" / "top50" / "top50_panel.parquet"
)
ADJUSTED_DB_PATH = (
    PROJECT_ROOT / "data" / "processed" / "moex_daily_adjusted.sqlite"
)
OUTPUT_DIR = (
    PROJECT_ROOT / "data" / "interim" / "ml_1" / "rolling_statistical_moments"
)

TABLE_NAME = "adjusted_daily_bars"
APPROVED_BOARDS = ("TQBR", "EQBR")
PRICE_BOARD_PRIORITY = {"TQBR": 0, "EQBR": 1}
EXCLUDED_TICKERS = {"GAZC", "GAZS", "GAZT"}

# Existing dataset/panel policy.
SUSPENSION_START = "2022-02-28"
SUSPENSION_END = "2022-03-23"

WINDOWS = (20, 60, 120, 240)
FEATURE_FAMILIES = ("mean", "variance", "skewness", "excess_kurtosis")
HORIZON = 5
MIN_CROSS_SECTION = 20
HAC_BANDWIDTHS = (4, 10, 20, 60)
HAC_MIN_OBSERVATIONS = 30
CHUNK_SIZE = 400

SUBPERIODS = (
    ("2005_2012", "2005-01-01", "2012-12-31"),
    ("2013_2019", "2013-01-01", "2019-12-31"),
    ("2020_plus", "2020-01-01", "2099-12-31"),
)
