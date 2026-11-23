# Folder: scripts/one_use/
# File: inspect_gche_primitives.py
# Purpose: Inspect GCHE price primitives outside the PIT TOP50 screener.
#
# Research question:
#   What are GCHE's drawdown_60, zscore_sma20_20, realized_vol_60,
#   and price_sma20 values on the requested snapshot date?
#
# Decision relevance:
#   GCHE is a known portfolio holding but is absent from the current
#   PIT TOP50 screener output. This script reproduces the approved
#   adjusted-close feature definitions for GCHE only.
#
# Inputs:
#   data/processed/moex_daily_adjusted.sqlite
#
# Output:
#   data/interim/screener/gche_primitive_inspection.csv
#
# Safety:
#   Read-only SQLite connection. Does not modify databases, panels,
#   feature frames, model outputs, or portfolio files.
#
# Execution:
#   python scripts/one_use/inspect_gche_primitives.py --date 2026-11-23

from __future__ import annotations

import argparse
import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "moex_daily_adjusted.sqlite"
OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "screener"
    / "gche_primitive_inspection.csv"
)

TABLE_NAME = "adjusted_daily_bars"
SECID = "GCHE"
BOARDS = ("TQBR", "EQBR")
BOARD_PRIORITY = {"TQBR": 0, "EQBR": 1}
SUSPENSION_START = pd.Timestamp("2022-02-28")
SUSPENSION_END = pd.Timestamp("2022-03-23")


def readonly_connection(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"Adjusted database not found: {path}")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only GCHE primitive inspection."
    )
    parser.add_argument(
        "--date",
        default="2026-11-23",
        help="Snapshot date YYYY-MM-DD (default: 2026-11-23).",
    )
    return parser.parse_args()


def load_history(snapshot_date: pd.Timestamp) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    placeholders = ",".join("?" for _ in BOARDS)
    query = f"""
        SELECT
            UPPER(TRIM(secid)) AS secid,
            tradedate,
            UPPER(TRIM(boardid)) AS boardid,
            adjusted_open,
            adjusted_high,
            adjusted_low,
            adjusted_close
        FROM "{TABLE_NAME}"
        WHERE UPPER(TRIM(secid)) = ?
          AND UPPER(TRIM(boardid)) IN ({placeholders})
          AND tradedate IS NOT NULL
          AND tradedate <= ?
        ORDER BY tradedate, boardid
    """

    calendar_query = f"""
        SELECT DISTINCT tradedate
        FROM "{TABLE_NAME}"
        WHERE boardid IN ({placeholders})
          AND tradedate IS NOT NULL
          AND tradedate <= ?
        ORDER BY tradedate
    """

    with readonly_connection(DB_PATH) as connection:
        history = pd.read_sql_query(
            query,
            connection,
            params=[SECID, *BOARDS, snapshot_date.strftime("%Y-%m-%d")],
        )
        calendar_frame = pd.read_sql_query(
            calendar_query,
            connection,
            params=[*BOARDS, snapshot_date.strftime("%Y-%m-%d")],
        )

    if history.empty:
        raise RuntimeError(
            f"No adjusted {SECID} bars found on or before {snapshot_date.date()} "
            f"for boards {BOARDS}."
        )

    history["tradedate"] = pd.to_datetime(history["tradedate"], errors="coerce")
    calendar = pd.DatetimeIndex(
        pd.to_datetime(calendar_frame["tradedate"], errors="coerce").dropna().unique()
    ).sort_values()

    calendar = calendar[
        (calendar < SUSPENSION_START) | (calendar > SUSPENSION_END)
    ]

    history = history.dropna(subset=["tradedate"]).copy()
    history = history[
        (history["tradedate"] < SUSPENSION_START)
        | (history["tradedate"] > SUSPENSION_END)
    ].copy()

    price_fields = [
        "adjusted_open",
        "adjusted_high",
        "adjusted_low",
        "adjusted_close",
    ]
    for column in price_fields:
        history[column] = pd.to_numeric(history[column], errors="coerce")

    history["_valid_ohlc"] = history[price_fields].notna().all(axis=1).astype(int)
    history["_board_priority"] = history["boardid"].map(BOARD_PRIORITY).fillna(999)

    history = (
        history.sort_values(
            ["tradedate", "_valid_ohlc", "_board_priority", "boardid"],
            ascending=[True, False, True, True],
            kind="mergesort",
        )
        .drop_duplicates(["tradedate"], keep="first")
        .sort_values("tradedate")
        .reset_index(drop=True)
    )

    return history, calendar


def calculate(snapshot_date: pd.Timestamp) -> pd.DataFrame:
    history, calendar = load_history(snapshot_date)
    indexed = history.set_index("tradedate").reindex(calendar)

    close = pd.to_numeric(indexed["adjusted_close"], errors="coerce")
    daily_return = close.pct_change(fill_method=None)

    sma20 = close.rolling(20, min_periods=20).mean()
    residual20 = close - sma20
    residual_std20 = residual20.rolling(20, min_periods=20).std(ddof=1)

    features = pd.DataFrame(index=calendar)
    features["adjusted_close"] = close
    features["price_sma20"] = close / sma20 - 1.0
    features["drawdown_60"] = close / close.rolling(60, min_periods=60).max() - 1.0
    features["zscore_sma20_20"] = residual20 / residual_std20
    features["realized_vol_60"] = (
        daily_return.rolling(60, min_periods=60).std(ddof=1) * math.sqrt(252)
    )
    features.index.name = "snapshot_date"

    if snapshot_date not in features.index:
        raise RuntimeError(
            f"Requested date {snapshot_date.date()} is absent from market calendar."
        )

    result = features.loc[[snapshot_date]].reset_index()
    result.insert(1, "secid", SECID)
    result["last_actual_bar_date"] = (
        history["tradedate"].max().strftime("%Y-%m-%d")
    )
    result["history_rows"] = int(len(history))
    result["calendar_sessions"] = int(len(calendar))
    result["data_status"] = (
        "OK"
        if pd.notna(result.loc[0, "adjusted_close"])
        and result.loc[0, [
            "price_sma20",
            "drawdown_60",
            "zscore_sma20_20",
            "realized_vol_60",
        ]].notna().all()
        else "INCOMPLETE_OR_NO_BAR_ON_REQUESTED_DATE"
    )
    result["snapshot_date"] = result["snapshot_date"].dt.strftime("%Y-%m-%d")
    return result


def main() -> int:
    args = parse_args()
    snapshot_date = pd.Timestamp(args.date).normalize()

    if snapshot_date > pd.Timestamp.today().normalize():
        raise ValueError("Requested snapshot date is in the future.")

    result = calculate(snapshot_date)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print(result.to_string(index=False))
    print(f"CSV saved: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    print("SQLite opened read-only; no source data was modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
