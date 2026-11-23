# Folder: scripts/one_use/
# File: build_candidate_comparison.py
# Purpose: Export a transparent cross-sectional comparison packet for
#          the latest PIT TOP50 plus current holdings T and GCHE.
#
# Research question:
#   Which current PIT TOP50 names deserve deeper fundamental/valuation
#   research relative to the existing holdings, without inventing a
#   composite score or treating screener ranks as buy signals?
#
# Inputs:
#   data/processed/top50/top50_panel.parquet
#   data/interim/primitive_research/primitive_features.parquet
#   data/processed/moex_daily_adjusted.sqlite (read-only, only for holdings
#   outside the latest PIT TOP50, currently GCHE)
#
# Output:
#   data/interim/screener/candidate_comparison_YYYY-MM-DD.csv
#
# Run:
#   python scripts/one_use/build_candidate_comparison.py
#
# Method:
#   - Uses the latest date in the PIT panel, not the computer's current date.
#   - Preserves PIT TOP50 membership and its panel rank.
#   - Adds T and GCHE if absent from the latest PIT TOP50.
#   - Reconstructs approved price primitives for outside-universe holdings.
#   - Adds separate high-value ranks/percentiles for selected features.
#   - Does NOT calculate a composite score, expected return, or target weight.
#
# Safety:
#   SQLite is opened read-only. No source data, panel, feature frame,
#   portfolio ledger, or model output is modified.

from __future__ import annotations

import argparse
import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PANEL_PATH = PROJECT_ROOT / "data" / "processed" / "top50" / "top50_panel.parquet"
FEATURE_PATH = PROJECT_ROOT / "data" / "interim" / "primitive_research" / "primitive_features.parquet"
DB_PATH = PROJECT_ROOT / "data" / "processed" / "moex_daily_adjusted.sqlite"
OUTPUT_DIR = PROJECT_ROOT / "data" / "interim" / "screener"
TABLE_NAME = "adjusted_daily_bars"

HOLDINGS = ("T", "GCHE")
BOARDS = ("TQBR", "EQBR")
BOARD_PRIORITY = {"TQBR": 0, "EQBR": 1}
EXCLUDED_TICKERS = {"GAZC", "GAZS", "GAZT"}
SUSPENSION_START = pd.Timestamp("2022-02-28")
SUSPENSION_END = pd.Timestamp("2022-03-23")

FEATURES = [
    "price_sma20",
    "sma20_sma50",
    "sma50_sma200",
    "return_5",
    "return_20",
    "return_60",
    "realized_vol_20",
    "realized_vol_60",
    "drawdown_20",
    "drawdown_60",
    "turnover_ratio_20",
    "rs_rank_20",
    "rs_rank_60",
    "rebound_20",
    "rebound_60",
    "zscore_sma20_20",
    "momentum_acceleration_20",
    "efficiency_ratio_20",
]


def resolve_column(frame: pd.DataFrame, expected: str) -> str:
    lookup = {str(c).strip().lower(): c for c in frame.columns}
    if expected.lower() not in lookup:
        raise RuntimeError(
            f"Missing column '{expected}'. Available: {list(frame.columns)}"
        )
    return lookup[expected.lower()]


def readonly_connection() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Adjusted DB not found: {DB_PATH}")
    con = sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only = ON")
    return con


def load_latest_panel_and_features() -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    for path in (PANEL_PATH, FEATURE_PATH):
        if not path.is_file():
            raise FileNotFoundError(f"Required input not found: {path}")

    panel = pd.read_parquet(PANEL_PATH)
    panel = panel[
        [
            resolve_column(panel, "tradedate"),
            resolve_column(panel, "secid"),
            resolve_column(panel, "rank"),
            resolve_column(panel, "bar_available"),
        ]
    ].copy()
    panel.columns = ["tradedate", "secid", "panel_rank", "bar_available"]
    panel["tradedate"] = pd.to_datetime(panel["tradedate"], errors="coerce").dt.normalize()
    panel["secid"] = panel["secid"].astype(str).str.strip().str.upper()
    panel["panel_rank"] = pd.to_numeric(panel["panel_rank"], errors="coerce")
    panel["bar_available"] = pd.to_numeric(
        panel["bar_available"], errors="coerce"
    ).fillna(0).astype(int)
    panel = panel.dropna(subset=["tradedate", "secid"])
    panel = panel[~panel["secid"].isin(EXCLUDED_TICKERS)].copy()

    if panel.duplicated(["tradedate", "secid"]).any():
        raise RuntimeError("Duplicate PIT panel rows for TRADEDATE/SECID.")

    snapshot_date = panel["tradedate"].max()
    current_panel = panel[panel["tradedate"].eq(snapshot_date)].copy()

    features = pd.read_parquet(FEATURE_PATH)
    required = ["tradedate", "secid", *FEATURES]
    actual = {name: resolve_column(features, name) for name in required}
    features = features[[actual[name] for name in required]].copy()
    features.columns = required
    features["tradedate"] = pd.to_datetime(
        features["tradedate"], errors="coerce"
    ).dt.normalize()
    features["secid"] = features["secid"].astype(str).str.strip().str.upper()
    for col in FEATURES:
        features[col] = pd.to_numeric(features[col], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
    features = features.dropna(subset=["tradedate", "secid"])

    if features.duplicated(["tradedate", "secid"]).any():
        raise RuntimeError("Duplicate primitive feature rows for TRADEDATE/SECID.")

    current_features = features[features["tradedate"].eq(snapshot_date)].copy()
    if current_features.empty:
        raise RuntimeError(
            f"No feature rows found for latest panel date {snapshot_date.date()}."
        )

    return current_panel, current_features, snapshot_date


def calculate_outside_holding(
    secid: str,
    snapshot_date: pd.Timestamp,
) -> dict:
    board_marks = ",".join("?" for _ in BOARDS)
    with readonly_connection() as con:
        history = pd.read_sql_query(
            f"""
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
              AND boardid IN ({board_marks})
              AND tradedate IS NOT NULL
              AND tradedate <= ?
            ORDER BY tradedate, boardid
            """,
            con,
            params=[secid, *BOARDS, snapshot_date.strftime("%Y-%m-%d")],
        )
        calendar_frame = pd.read_sql_query(
            f"""
            SELECT DISTINCT tradedate
            FROM "{TABLE_NAME}"
            WHERE boardid IN ({board_marks})
              AND tradedate IS NOT NULL
              AND tradedate <= ?
            ORDER BY tradedate
            """,
            con,
            params=[*BOARDS, snapshot_date.strftime("%Y-%m-%d")],
        )

    if history.empty:
        raise RuntimeError(f"No adjusted history found for outside holding {secid}.")

    history["tradedate"] = pd.to_datetime(history["tradedate"], errors="coerce").dt.normalize()
    for col in ("adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close"):
        history[col] = pd.to_numeric(history[col], errors="coerce")
    history = history.dropna(subset=["tradedate", "boardid"])
    history = history[
        (history["tradedate"] < SUSPENSION_START)
        | (history["tradedate"] > SUSPENSION_END)
    ].copy()

    history["_valid_ohlc"] = history[
        ["adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close"]
    ].notna().all(axis=1).astype(int)
    history["_board_priority"] = history["boardid"].map(BOARD_PRIORITY).fillna(999)
    history = (
        history.sort_values(
            ["tradedate", "_valid_ohlc", "_board_priority", "boardid"],
            ascending=[True, False, True, True],
            kind="mergesort",
        )
        .drop_duplicates(["tradedate"], keep="first")
        .sort_values("tradedate")
    )

    calendar = pd.DatetimeIndex(
        pd.to_datetime(calendar_frame["tradedate"], errors="coerce").dropna().unique()
    ).sort_values()
    calendar = calendar[
        (calendar < SUSPENSION_START) | (calendar > SUSPENSION_END)
    ]
    if snapshot_date not in calendar:
        raise RuntimeError(
            f"Snapshot date {snapshot_date.date()} absent from adjusted market calendar."
        )

    indexed = history.set_index("tradedate").reindex(calendar)
    close = pd.to_numeric(indexed["adjusted_close"], errors="coerce")
    daily_return = close.pct_change(fill_method=None)

    sma20 = close.rolling(20, min_periods=20).mean()
    sma50 = close.rolling(50, min_periods=50).mean()
    sma200 = close.rolling(200, min_periods=200).mean()
    residual20 = close - sma20
    residual_std20 = residual20.rolling(20, min_periods=20).std(ddof=1)

    def drawdown(window: int) -> float:
        return float(
            close.loc[snapshot_date]
            / close.rolling(window, min_periods=window).max().loc[snapshot_date]
            - 1.0
        )

    def value(series: pd.Series) -> float:
        result = series.loc[snapshot_date]
        return float(result) if pd.notna(result) else np.nan

    return {
        "secid": secid,
        "universe_member": False,
        "panel_rank": np.nan,
        "bar_available": int(pd.notna(close.loc[snapshot_date])),
        "data_source": "adjusted_db_direct_reconstruction",
        "price_sma20": value(close / sma20 - 1.0),
        "sma20_sma50": value(sma20 / sma50 - 1.0),
        "sma50_sma200": value(sma50 / sma200 - 1.0),
        "return_5": value(close / close.shift(5) - 1.0),
        "return_20": value(close / close.shift(20) - 1.0),
        "return_60": value(close / close.shift(60) - 1.0),
        "realized_vol_20": value(
            daily_return.rolling(20, min_periods=20).std(ddof=1) * math.sqrt(252)
        ),
        "realized_vol_60": value(
            daily_return.rolling(60, min_periods=60).std(ddof=1) * math.sqrt(252)
        ),
        "drawdown_20": drawdown(20),
        "drawdown_60": drawdown(60),
        "turnover_ratio_20": np.nan,
        "rs_rank_20": np.nan,
        "rs_rank_60": np.nan,
        "rebound_20": value(
            close / close.rolling(20, min_periods=20).min() - 1.0
        ),
        "rebound_60": value(
            close / close.rolling(60, min_periods=60).min() - 1.0
        ),
        "zscore_sma20_20": value(residual20 / residual_std20),
        "momentum_acceleration_20": value(
            (close / close.shift(20) - 1.0)
            - (close / close.shift(20) - 1.0).shift(5)
        ),
        "efficiency_ratio_20": value(
            (close - close.shift(20)).abs()
            / close.diff().abs().rolling(20, min_periods=20).sum()
        ),
    }


def add_cross_sectional_ranks(frame: pd.DataFrame) -> pd.DataFrame:
    # Ranks/percentiles are computed only against the current PIT TOP50.
    # Outside-universe holdings are displayed but do not alter the reference set.
    reference = frame[frame["universe_member"].eq(True)]
    for feature in FEATURES:
        rank_col = f"{feature}_rank_high_value"
        pct_col = f"{feature}_percentile_high_value"
        frame[rank_col] = np.nan
        frame[pct_col] = np.nan
        valid = reference[feature].dropna()
        if valid.empty:
            continue
        ranks = valid.rank(ascending=False, method="min")
        percentiles = valid.rank(ascending=True, method="average", pct=True) * 100.0
        frame.loc[ranks.index, rank_col] = ranks
        frame.loc[percentiles.index, pct_col] = percentiles
    return frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a non-composite current candidate comparison packet."
    )
    parser.add_argument(
        "--holdings", default="T,GCHE",
        help="Comma-separated holdings to append if absent from PIT TOP50.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    holdings = tuple(
        token.strip().upper()
        for token in args.holdings.split(",")
        if token.strip()
    )

    panel, features, snapshot_date = load_latest_panel_and_features()
    snapshot = panel.merge(
        features.drop(columns=["tradedate"]),
        on="secid",
        how="left",
        validate="one_to_one",
    )
    snapshot.insert(0, "snapshot_date", snapshot_date.strftime("%Y-%m-%d"))
    snapshot["universe_member"] = True
    snapshot["data_source"] = "pit_top50_feature_frame"
    snapshot["is_current_holding"] = snapshot["secid"].isin(holdings)

    existing = set(snapshot["secid"])
    extra_rows = []
    for secid in holdings:
        if secid in existing:
            continue
        row = calculate_outside_holding(secid, snapshot_date)
        row["snapshot_date"] = snapshot_date.strftime("%Y-%m-%d")
        row["is_current_holding"] = True
        for col in FEATURES:
            row.setdefault(col, np.nan)
        extra_rows.append(row)

    if extra_rows:
        snapshot = pd.concat(
            [snapshot, pd.DataFrame(extra_rows)],
            ignore_index=True,
            sort=False,
        )

    for col in FEATURES:
        if col not in snapshot.columns:
            snapshot[col] = np.nan

    snapshot = add_cross_sectional_ranks(snapshot)
    snapshot = snapshot.sort_values(
        ["is_current_holding", "panel_rank", "secid"],
        ascending=[False, True, True],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)

    ordered = [
        "snapshot_date", "secid", "is_current_holding",
        "universe_member", "panel_rank", "bar_available", "data_source",
        *FEATURES,
    ]
    rank_cols = []
    for feature in FEATURES:
        rank_cols.extend([
            f"{feature}_rank_high_value",
            f"{feature}_percentile_high_value",
        ])
    output = snapshot[ordered + rank_cols].copy()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"candidate_comparison_{snapshot_date:%Y-%m-%d}.csv"
    output.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
        float_format="%.10g",
    )

    print("CANDIDATE COMPARISON PACKET")
    print(f"Snapshot date: {snapshot_date.date()}")
    print(f"PIT TOP50 rows: {int(snapshot['universe_member'].eq(True).sum())}")
    print(f"Holdings included: {', '.join(holdings)}")
    print("No composite score, expected return, BUY/SELL signal, or target weight was generated.")
    print()
    display = output[
        [
            "secid", "is_current_holding", "universe_member", "panel_rank",
            "return_20", "return_60", "price_sma20", "sma20_sma50",
            "drawdown_60", "zscore_sma20_20", "realized_vol_60",
            "turnover_ratio_20",
        ]
    ]
    print(display.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print()
    print(f"CSV saved: {output_path.relative_to(PROJECT_ROOT)}")
    print("SQLite opened read-only; source files were not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
