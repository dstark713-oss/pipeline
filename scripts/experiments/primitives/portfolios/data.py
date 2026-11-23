# Folder: scripts/experiments/primitives/portfolios/
# File: data.py
# Purpose: Load PIT primitive features and adjusted opens; build breadth and
#          next-open-to-next-open asset returns without look-ahead.

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    ADJUSTED_DB_PATH, APPROVED_BOARDS, BREADTH_LOOKBACK,
    FEATURE_PATH, MIN_BREADTH_NAMES, PRICE_BOARD_PRIORITY, TABLE_NAME,
)

REQUIRED_FEATURES = [
    "tradedate", "secid", "rank",
    "drawdown_60", "zscore_sma20_20", "realized_vol_60", "price_sma20",
]


def log(message: str) -> None:
    print(message, flush=True)


def readonly_connection(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def load_features() -> pd.DataFrame:
    if not FEATURE_PATH.is_file():
        raise FileNotFoundError(f"Primitive feature file not found: {FEATURE_PATH}")

    frame = pd.read_parquet(FEATURE_PATH)
    missing = sorted(set(REQUIRED_FEATURES) - set(frame.columns))
    if missing:
        raise RuntimeError(f"Feature frame is missing required columns: {missing}")

    # The feature builder outputs only rows with an actual observed bar.
    # Older/current parquet files may omit bar_available; derive it as 1.
    if "bar_available" in frame.columns:
        frame = frame[REQUIRED_FEATURES + ["bar_available"]].copy()
        frame["bar_available"] = pd.to_numeric(
            frame["bar_available"], errors="coerce"
        ).fillna(0).astype(int)
    else:
        frame = frame[REQUIRED_FEATURES].copy()
        frame["bar_available"] = 1
        log("bar_available absent: deriving availability=1 from observed-bar-only feature rows.")

    frame["tradedate"] = pd.to_datetime(frame["tradedate"], errors="coerce")
    frame["secid"] = frame["secid"].astype(str).str.strip().str.upper()

    for column in (
        "rank", "drawdown_60", "zscore_sma20_20",
        "realized_vol_60", "price_sma20",
    ):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.dropna(subset=["tradedate", "secid"])
    frame = frame[frame["bar_available"].eq(1)].copy()

    if frame.duplicated(["tradedate", "secid"]).any():
        raise RuntimeError("Duplicate SECID/TRADEDATE rows in primitive feature frame.")
    if frame.empty:
        raise RuntimeError("Primitive feature frame is empty.")

    frame = frame.sort_values(["tradedate", "rank", "secid"]).reset_index(drop=True)
    log(
        f"Feature rows: {len(frame):,}; dates: {frame['tradedate'].nunique():,}; "
        f"tickers: {frame['secid'].nunique():,}"
    )
    return frame


def load_open_matrix(secids: list[str], dates: pd.DatetimeIndex) -> pd.DataFrame:
    if not ADJUSTED_DB_PATH.is_file():
        raise FileNotFoundError(f"Adjusted SQLite database not found: {ADJUSTED_DB_PATH}")

    chunks = []
    board_placeholders = ",".join("?" for _ in APPROVED_BOARDS)
    batch_size = 400
    log("Loading adjusted OPEN prices from SQLite (read-only)...")

    with readonly_connection(ADJUSTED_DB_PATH) as connection:
        for start in range(0, len(secids), batch_size):
            batch = secids[start:start + batch_size]
            ticker_placeholders = ",".join("?" for _ in batch)
            query = f"""
                SELECT UPPER(TRIM(secid)) AS secid, tradedate, boardid, adjusted_open
                FROM "{TABLE_NAME}"
                WHERE boardid IN ({board_placeholders})
                  AND UPPER(TRIM(secid)) IN ({ticker_placeholders})
                  AND tradedate IS NOT NULL
            """
            part = pd.read_sql_query(
                query, connection, params=[*APPROVED_BOARDS, *batch]
            )
            if not part.empty:
                chunks.append(part)
            log(
                f"Loaded OPEN history: "
                f"{min(start + batch_size, len(secids)):,}/{len(secids):,} tickers"
            )

    if not chunks:
        raise RuntimeError("No adjusted OPEN observations found.")

    source = pd.concat(chunks, ignore_index=True)
    source["tradedate"] = pd.to_datetime(source["tradedate"], errors="coerce")
    source["secid"] = source["secid"].astype(str).str.strip().str.upper()
    source["boardid"] = source["boardid"].astype(str).str.strip().str.upper()
    source["adjusted_open"] = pd.to_numeric(source["adjusted_open"], errors="coerce")
    source = source.dropna(subset=["tradedate", "secid", "boardid"]).copy()

    if source.duplicated(["secid", "tradedate", "boardid"]).any():
        raise RuntimeError("Duplicate SECID/TRADEDATE/BOARDID rows in adjusted OPEN history.")

    source["_priority"] = source["boardid"].map(PRICE_BOARD_PRIORITY).fillna(999)
    source["_valid_open"] = (
        source["adjusted_open"].notna()
        & np.isfinite(source["adjusted_open"])
        & source["adjusted_open"].gt(0)
    ).astype("int8")

    # Prefer valid TQBR OPEN; use valid EQBR as fallback.
    source = source.sort_values(
        ["secid", "tradedate", "_valid_open", "_priority", "boardid"],
        ascending=[True, True, False, True, True],
        kind="mergesort",
    ).drop_duplicates(["secid", "tradedate"], keep="first")

    source.loc[~source["_valid_open"].eq(1), "adjusted_open"] = np.nan
    matrix = source.pivot(
        index="tradedate", columns="secid", values="adjusted_open"
    )
    matrix = matrix.reindex(index=dates, columns=secids).sort_index()

    log(f"OPEN matrix: {matrix.shape[0]:,} sessions x {matrix.shape[1]:,} tickers")
    return matrix


def build_breadth(frame: pd.DataFrame) -> pd.DataFrame:
    daily = (
        frame.assign(
            above_sma20=frame["price_sma20"].gt(0).where(
                frame["price_sma20"].notna()
            )
        )
        .groupby("tradedate")
        .agg(
            breadth_names=("above_sma20", "count"),
            breadth_level=("above_sma20", "mean"),
        )
        .sort_index()
    )

    daily["breadth_level"] *= 100.0
    daily.loc[daily["breadth_names"] < MIN_BREADTH_NAMES, "breadth_level"] = np.nan
    daily["breadth_change_5"] = (
        daily["breadth_level"] - daily["breadth_level"].shift(BREADTH_LOOKBACK)
    )

    def classify(row: pd.Series) -> str | None:
        level, change = row["breadth_level"], row["breadth_change_5"]
        if not np.isfinite(level) or not np.isfinite(change):
            return None
        level_state = "above50" if level > 50.0 else "below50"
        change_state = "rising" if change > 0.0 else "flat_or_falling"
        return f"{level_state}_{change_state}"

    daily["breadth_regime"] = daily.apply(classify, axis=1)
    return daily.reset_index()


def build_asset_returns(
    open_matrix: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Signal after close T; enter OPEN T+1; exit/rebalance OPEN T+2.
    entry_open = open_matrix.shift(-1)
    exit_open = open_matrix.shift(-2)
    returns = exit_open.div(entry_open).sub(1.0).replace([np.inf, -np.inf], np.nan)

    date_map = pd.DataFrame(index=open_matrix.index)
    date_map["signal_date"] = open_matrix.index
    date_map["execution_date"] = pd.Series(
        open_matrix.index, index=open_matrix.index
    ).shift(-1)
    date_map["exit_date"] = pd.Series(
        open_matrix.index, index=open_matrix.index
    ).shift(-2)
    return returns, date_map


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    features = load_features()
    dates = pd.DatetimeIndex(sorted(features["tradedate"].dropna().unique()))
    secids = sorted(features["secid"].unique())
    opens = load_open_matrix(secids, dates)
    breadth = build_breadth(features)
    asset_returns, date_map = build_asset_returns(opens)

    if not asset_returns.index.equals(dates):
        raise RuntimeError("Asset return dates do not match feature dates.")
    return features, breadth, asset_returns, date_map
