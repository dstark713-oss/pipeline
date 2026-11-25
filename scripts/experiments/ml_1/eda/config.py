"""Configuration for descriptive EDA of the PIT TOP50 panel."""
from pathlib import Path

def find_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists() or (parent / "data").exists():
            return parent
    raise RuntimeError("Could not locate project root.")

PROJECT_ROOT = find_project_root()
PANEL_PATH = PROJECT_ROOT / "data" / "processed" / "top50" / "top50_panel.parquet"
ADJUSTED_DB_PATH = PROJECT_ROOT / "data" / "processed" / "moex_daily_adjusted.sqlite"
DB_TABLE = "adjusted_daily_bars"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "research" / "eda"

APPROVED_BOARDS = ("TQBR", "EQBR")
PRICE_BOARD_PRIORITY = {"TQBR": 0, "EQBR": 1}
SUSPENSION_START = "2022-02-28"
SUSPENSION_END = "2022-03-23"
EXCLUDED_TICKERS = {"GAZC", "GAZS", "GAZT"}
HORIZONS = (1, 5, 20)
CHUNK_SIZE = 200

# numtrades is intentionally not analyzed: it is not part of the EDA input contract.
MARKET_VARIABLES = (
    "adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close",
    "volume", "value",
)
MEMBERSHIP_VARIABLES = ("value_60d", "rank", "universe_size")
