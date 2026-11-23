# Folder: scripts/experiments/primitives/portfolios/
# File: config.py
# Purpose: Shared configuration for the primitive portfolio application experiment.

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FEATURE_PATH = ROOT / "data/interim/primitive_research/primitive_features.parquet"
ADJUSTED_DB_PATH = ROOT / "data/processed/moex_daily_adjusted.sqlite"
OUTPUT_DIR = ROOT / "data/interim/primitive_research/portfolios"

TABLE_NAME = "adjusted_daily_bars"
APPROVED_BOARDS = ("TQBR", "EQBR")
PRICE_BOARD_PRIORITY = {"TQBR": 0, "EQBR": 1}

TOP_N = 10
BASELINE_WEIGHT = 0.02
SELECTED_WEIGHT = 0.10
BREADTH_LOOKBACK = 5
MIN_BREADTH_NAMES = 20
TRANSACTION_COST_BPS = (0.0, 10.0, 25.0)

CORE_STRATEGIES = {
    "baseline_top50": {
        "kind": "baseline", "feature": None, "ascending": True,
        "description": "PIT TOP50, 2% per available constituent.",
    },
    "drawdown60_top10": {
        "kind": "rank", "feature": "drawdown_60", "ascending": False,
        "description": "TOP10 by drawdown_60; higher is closer to 60-session high.",
    },
    "drawdown60_bottom10": {
        "kind": "rank", "feature": "drawdown_60", "ascending": True,
        "description": "BOTTOM10 by drawdown_60; deepest drawdowns.",
    },
    "zscore_top10": {
        "kind": "rank", "feature": "zscore_sma20_20", "ascending": False,
        "description": "TOP10 by zscore_sma20_20; strongest positive deviations.",
    },
    "zscore_bottom10": {
        "kind": "rank", "feature": "zscore_sma20_20", "ascending": True,
        "description": "BOTTOM10 by zscore_sma20_20; strongest negative deviations.",
    },
    "realized_vol60_bottom10": {
        "kind": "rank", "feature": "realized_vol_60", "ascending": True,
        "description": "BOTTOM10 by realized_vol_60; lowest realized volatility.",
    },
    "realized_vol60_top10": {
        "kind": "rank", "feature": "realized_vol_60", "ascending": False,
        "description": "TOP10 by realized_vol_60; highest realized volatility.",
    },
}

BREADTH_MULTIPLIERS = {
    "above50_rising": 1.00,
    "above50_flat_or_falling": 0.75,
    "below50_rising": 0.50,
    "below50_flat_or_falling": 0.25,
}
