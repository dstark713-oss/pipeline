# Path: scripts/experiments/ml_1/eda/data_loader.py
# Purpose: EDA implementation module.
"""Read-only loading and market-session alignment for EDA."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from config import (
    ADJUSTED_DB_PATH, APPROVED_BOARDS, CHUNK_SIZE, DB_TABLE,
    EXCLUDED_TICKERS, PANEL_PATH, PRICE_BOARD_PRIORITY,
    SUSPENSION_END, SUSPENSION_START,
)


def readonly_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def load_panel() -> pd.DataFrame:
    if not PANEL_PATH.is_file():
        raise FileNotFoundError(f"PIT TOP50 panel not found: {PANEL_PATH}")
    panel = pd.read_parquet(PANEL_PATH)
    required = {
        "tradedate", "secid", "bar_available", "adjusted_open",
        "adjusted_high", "adjusted_low", "adjusted_close",
        "volume", "value", "value_60d", "rank", "universe_size",
    }
    missing = required - set(panel.columns)
    if missing:
        raise RuntimeError(f"Panel is missing required EDA columns: {sorted(missing)}")

    panel["tradedate"] = pd.to_datetime(panel["tradedate"], errors="coerce")
    panel["secid"] = panel["secid"].astype(str).str.strip().str.upper()
    panel["bar_available"] = pd.to_numeric(
        panel["bar_available"], errors="coerce"
    ).fillna(0).astype("int8")
    numeric = required - {"tradedate", "secid", "bar_available"}
    for column in numeric:
        panel[column] = pd.to_numeric(panel[column], errors="coerce")

    panel = panel.dropna(subset=["tradedate", "secid"]).copy()
    panel = panel[~panel["secid"].isin(EXCLUDED_TICKERS)].copy()
    if panel.empty:
        raise RuntimeError("PIT TOP50 panel is empty after basic normalization.")
    if panel.duplicated(["tradedate", "secid"]).any():
        raise RuntimeError("Duplicate SECID/tradedate rows found; panel uniqueness audit is not repeated here.")
    return panel.sort_values(["tradedate", "secid"]).reset_index(drop=True)


def load_market_history(secids: list[str]) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    if not ADJUSTED_DB_PATH.is_file():
        raise FileNotFoundError(f"Adjusted database not found: {ADJUSTED_DB_PATH}")

    board_marks = ",".join("?" for _ in APPROVED_BOARDS)
    chunks: list[pd.DataFrame] = []
    with readonly_connection(ADJUSTED_DB_PATH) as connection:
        columns = {
            row[1].lower()
            for row in connection.execute(f'PRAGMA table_info("{DB_TABLE}")').fetchall()
        }
        required = {
            "secid", "tradedate", "boardid", "adjusted_open",
            "adjusted_high", "adjusted_low", "adjusted_close",
        }
        missing = required - columns
        if missing:
            raise RuntimeError(f"{DB_TABLE} is missing columns: {sorted(missing)}")

        calendar_frame = pd.read_sql_query(
            f"""SELECT DISTINCT tradedate FROM "{DB_TABLE}"
                WHERE boardid IN ({board_marks}) AND tradedate IS NOT NULL
                ORDER BY tradedate""",
            connection,
            params=list(APPROVED_BOARDS),
        )
        calendar = pd.DatetimeIndex(
            pd.to_datetime(calendar_frame["tradedate"], errors="coerce").dropna().unique()
        ).sort_values()
        calendar = calendar[
            (calendar < pd.Timestamp(SUSPENSION_START))
            | (calendar > pd.Timestamp(SUSPENSION_END))
        ]

        selected = [
            "secid", "tradedate", "boardid", "adjusted_open",
            "adjusted_high", "adjusted_low", "adjusted_close",
        ]
        if "adjustment_status" in columns:
            selected.append("adjustment_status")
        select_sql = ", ".join(f'"{name}"' for name in selected)

        for start in range(0, len(secids), CHUNK_SIZE):
            batch = secids[start:start + CHUNK_SIZE]
            secid_marks = ",".join("?" for _ in batch)
            query = f"""SELECT {select_sql} FROM "{DB_TABLE}"
                WHERE boardid IN ({board_marks})
                  AND UPPER(TRIM(secid)) IN ({secid_marks})
                  AND tradedate IS NOT NULL
                ORDER BY tradedate, secid, boardid"""
            frame = pd.read_sql_query(
                query, connection, params=[*APPROVED_BOARDS, *batch]
            )
            if not frame.empty:
                chunks.append(frame)

    if not chunks:
        raise RuntimeError("No adjusted price history found for panel SECIDs.")

    history = pd.concat(chunks, ignore_index=True)
    history["secid"] = history["secid"].astype(str).str.strip().str.upper()
    history["boardid"] = history["boardid"].astype(str).str.strip().str.upper()
    history["tradedate"] = pd.to_datetime(history["tradedate"], errors="coerce")
    for column in ("adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close"):
        history[column] = pd.to_numeric(history[column], errors="coerce")
    history = history.dropna(subset=["secid", "tradedate"]).copy()
    history = history[
        (history["tradedate"] < pd.Timestamp(SUSPENSION_START))
        | (history["tradedate"] > pd.Timestamp(SUSPENSION_END))
    ].copy()

    duplicate_keys = ["secid", "tradedate", "boardid"]
    if history.duplicated(duplicate_keys).any():
        raise RuntimeError("Duplicate SECID/date/board rows in adjusted history.")

    price_fields = ["adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close"]
    history["_valid_ohlc"] = history[price_fields].notna().all(axis=1).astype("int8")
    history["_board_priority"] = history["boardid"].map(PRICE_BOARD_PRIORITY).fillna(999)
    prices = (
        history.sort_values(
            ["secid", "tradedate", "_valid_ohlc", "_board_priority", "boardid"],
            ascending=[True, True, False, True, True],
            kind="mergesort",
        )
        .drop_duplicates(["secid", "tradedate"], keep="first")
        [["secid", "tradedate", "adjusted_close"]]
        .copy()
    )
    return prices, calendar
