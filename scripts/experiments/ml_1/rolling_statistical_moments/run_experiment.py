# Folder: scripts/experiments/ml_1/rolling_statistical_moments/
# File: run_experiment.py
# Purpose: Run the Rolling Statistical Moments feature-research experiment.
#
# Inputs:
#   data/processed/top50/top50_panel.parquet
#   data/processed/moex_daily_adjusted.sqlite (read-only)
#
# Outputs:
#   data/interim/ml_1/rolling_statistical_moments/
#
# Run from repository root:
#   python scripts/experiments/ml_1/rolling_statistical_moments/run_experiment.py

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from config import (
    ADJUSTED_DB_PATH,
    APPROVED_BOARDS,
    CHUNK_SIZE,
    EXCLUDED_TICKERS,
    HORIZON,
    OUTPUT_DIR,
    PANEL_PATH,
    PRICE_BOARD_PRIORITY,
    SUSPENSION_END,
    SUSPENSION_START,
    TABLE_NAME,
    WINDOWS,
)
from evaluation import (
    calculate_daily_feature_correlations,
    calculate_daily_ic,
    calculate_feature_coverage,
    summarize_ic,
    build_hac_inference,
    summarize_missingness,
)
from features import (
    calculate_binary_target,
    calculate_log_returns,
    calculate_rolling_moments,
)
from reporting import write_json, write_report


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def readonly_connection(path):
    uri = path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def validate_inputs() -> None:
    if not PANEL_PATH.is_file():
        raise FileNotFoundError(f"TOP50 panel not found: {PANEL_PATH}")
    if not ADJUSTED_DB_PATH.is_file():
        raise FileNotFoundError(
            f"Adjusted database not found: {ADJUSTED_DB_PATH}"
        )


def load_panel() -> pd.DataFrame:
    log(f"Loading PIT TOP50 panel: {PANEL_PATH}")
    panel = pd.read_parquet(PANEL_PATH)

    required = {"tradedate", "secid", "bar_available"}
    missing = required - set(panel.columns)
    if missing:
        raise RuntimeError(f"Panel is missing columns: {sorted(missing)}")

    panel["tradedate"] = pd.to_datetime(panel["tradedate"], errors="coerce")
    panel["secid"] = panel["secid"].astype(str).str.strip().str.upper()
    panel["bar_available"] = pd.to_numeric(
        panel["bar_available"], errors="coerce"
    ).fillna(0).astype(int)

    panel = panel.dropna(subset=["tradedate", "secid"]).copy()
    panel = panel[~panel["secid"].isin(EXCLUDED_TICKERS)].copy()
    panel = panel[panel["bar_available"].eq(1)].copy()

    if panel.duplicated(["tradedate", "secid"]).any():
        raise RuntimeError("Duplicate tradedate/SECID rows in PIT TOP50 panel.")
    if panel.empty:
        raise RuntimeError("No PIT TOP50 signal rows with bar_available=1.")

    log(
        f"Signal rows: {len(panel):,}; dates: {panel['tradedate'].nunique():,}; "
        f"SECIDs: {panel['secid'].nunique():,}"
    )
    return panel


def load_adjusted_history(
    secids: list[str],
) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    chunks = []
    board_placeholders = ",".join("?" for _ in APPROVED_BOARDS)

    with readonly_connection(ADJUSTED_DB_PATH) as connection:
        columns = {
            row[1].lower()
            for row in connection.execute(
                f'PRAGMA table_info("{TABLE_NAME}")'
            ).fetchall()
        }
        required = {
            "secid", "tradedate", "boardid",
            "adjusted_open", "adjusted_high",
            "adjusted_low", "adjusted_close",
        }
        missing = required - columns
        if missing:
            raise RuntimeError(
                f"{TABLE_NAME} is missing required columns: {sorted(missing)}"
            )

        calendar_query = f"""
            SELECT DISTINCT tradedate
            FROM "{TABLE_NAME}"
            WHERE boardid IN ({board_placeholders})
              AND tradedate IS NOT NULL
            ORDER BY tradedate
        """
        calendar_frame = pd.read_sql_query(
            calendar_query, connection, params=list(APPROVED_BOARDS)
        )
        calendar = pd.DatetimeIndex(
            pd.to_datetime(calendar_frame["tradedate"], errors="coerce")
        ).dropna().unique().sort_values()

        calendar = calendar[
            (calendar < pd.Timestamp(SUSPENSION_START))
            | (calendar > pd.Timestamp(SUSPENSION_END))
        ]

        for start in range(0, len(secids), CHUNK_SIZE):
            batch = secids[start:start + CHUNK_SIZE]
            ticker_placeholders = ",".join("?" for _ in batch)

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
                WHERE boardid IN ({board_placeholders})
                  AND UPPER(TRIM(secid)) IN ({ticker_placeholders})
                  AND tradedate IS NOT NULL
                ORDER BY tradedate, secid, boardid
            """
            chunk = pd.read_sql_query(
                query,
                connection,
                params=[*APPROVED_BOARDS, *batch],
            )
            if not chunk.empty:
                chunks.append(chunk)

            log(
                f"Loaded adjusted history for SECIDs: "
                f"{min(start + CHUNK_SIZE, len(secids)):,}/{len(secids):,}"
            )

    if not chunks:
        raise RuntimeError("No adjusted daily history found for PIT TOP50 SECIDs.")

    source = pd.concat(chunks, ignore_index=True)
    source["tradedate"] = pd.to_datetime(source["tradedate"], errors="coerce")

    for column in (
        "adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close"
    ):
        source[column] = pd.to_numeric(source[column], errors="coerce")

    source = source.dropna(subset=["secid", "tradedate"]).copy()
    source = source[~source["secid"].isin(EXCLUDED_TICKERS)].copy()
    source = source[
        (source["tradedate"] < pd.Timestamp(SUSPENSION_START))
        | (source["tradedate"] > pd.Timestamp(SUSPENSION_END))
    ].copy()

    if source.duplicated(["secid", "tradedate", "boardid"]).any():
        raise RuntimeError(
            "Duplicate SECID/TRADEDATE/BOARDID rows in adjusted history."
        )

    price_fields = [
        "adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close"
    ]
    source["_valid_ohlc"] = source[price_fields].notna().all(axis=1).astype("int8")
    source["_board_priority"] = (
        source["boardid"].map(PRICE_BOARD_PRIORITY).fillna(999)
    )

    # Match established pipeline policy: prefer a complete OHLC row,
    # then TQBR, then EQBR. No price averaging across boards.
    prices = (
        source.sort_values(
            ["secid", "tradedate", "_valid_ohlc", "_board_priority", "boardid"],
            ascending=[True, True, False, True, True],
            kind="mergesort",
        )
        .drop_duplicates(["secid", "tradedate"], keep="first")
        [["secid", "tradedate", "adjusted_close"]]
        .copy()
    )

    log(
        f"Adjusted price rows: {len(prices):,}; "
        f"market sessions: {len(calendar):,}"
    )
    return prices, calendar


def build_ticker_observations(
    ticker_history: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    secid = ticker_history["secid"].iloc[0]
    close = (
        ticker_history.set_index("tradedate")["adjusted_close"]
        .reindex(calendar)
        .astype("float64")
    )

    log_returns = calculate_log_returns(close)
    moments = calculate_rolling_moments(log_returns, WINDOWS)
    target = calculate_binary_target(close, HORIZON)

    result = moments.copy()
    result["secid"] = secid
    result["adjusted_close"] = close
    result["target"] = target

    return result.rename_axis("tradedate").reset_index()


def build_observations(
    panel: pd.DataFrame,
    prices: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    history_groups = {
        secid: group
        for secid, group in prices.groupby("secid", sort=False)
    }
    selected_tickers = sorted(panel["secid"].unique())
    chunks = []

    for number, secid in enumerate(selected_tickers, start=1):
        history = history_groups.get(secid)
        if history is None:
            log(f"WARNING: no adjusted history for {secid}; skipping")
            continue

        ticker_frame = build_ticker_observations(history, calendar)
        signal_dates = panel.loc[
            panel["secid"].eq(secid), "tradedate"
        ].to_numpy()

        selected = ticker_frame[
            ticker_frame["tradedate"].isin(signal_dates)
        ].copy()
        if not selected.empty:
            chunks.append(selected)

        if number % 25 == 0 or number == len(selected_tickers):
            log(f"Feature calculation: {number:,}/{len(selected_tickers):,} SECIDs")

    if not chunks:
        raise RuntimeError("No feature observations were generated.")

    features = pd.concat(chunks, ignore_index=True)
    frame = panel[["tradedate", "secid"]].merge(
        features,
        on=["tradedate", "secid"],
        how="left",
        validate="one_to_one",
    )

    # Do not keep rows whose five-session target is unavailable or tied.
    before = len(frame)
    frame = frame[frame["target"].notna()].copy()
    log(
        f"Rows with valid binary target: {len(frame):,}/{before:,}; "
        f"excluded: {before - len(frame):,}"
    )

    if frame.empty:
        raise RuntimeError("No observations remain after target validation.")

    return frame.sort_values(["tradedate", "secid"]).reset_index(drop=True)


def main() -> None:
    validate_inputs()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    panel = load_panel()
    prices, calendar = load_adjusted_history(sorted(panel["secid"].unique()))
    observations = build_observations(panel, prices, calendar)
    signal_calendar = calendar[
        (calendar >= panel["tradedate"].min())
        & (calendar <= panel["tradedate"].max())
    ]

    feature_columns = [
        f"rolling_{family}_{window}"
        for family in (
            "mean", "variance", "skewness", "excess_kurtosis"
        )
        for window in WINDOWS
    ]

    log("Calculating daily cross-sectional IC and Rank IC...")
    daily_ic = calculate_daily_ic(observations, feature_columns, signal_calendar)
    summary = summarize_ic(daily_ic)
    hac_inference = build_hac_inference(
        daily_ic, signal_calendar, bandwidths=(4, 10, 20, 60)
    )
    missingness = summarize_missingness(daily_ic)
    coverage = calculate_feature_coverage(observations, feature_columns)

    log("Calculating within-date feature redundancy...")
    redundancy = calculate_daily_feature_correlations(
        observations, feature_columns
    )

    observations_path = OUTPUT_DIR / "feature_observations.parquet"
    daily_ic_path = OUTPUT_DIR / "daily_ic.csv"
    summary_path = OUTPUT_DIR / "ic_summary.csv"
    coverage_path = OUTPUT_DIR / "feature_coverage.csv"
    redundancy_path = OUTPUT_DIR / "feature_redundancy.csv"
    hac_inference_path = OUTPUT_DIR / "hac_inference.csv"
    missingness_path = OUTPUT_DIR / "ic_missingness.csv"

    temporary_parquet = observations_path.with_name(
        observations_path.stem + ".tmp" + observations_path.suffix
    )
    observations.to_parquet(
        temporary_parquet, index=False, compression="zstd"
    )
    temporary_parquet.replace(observations_path)

    for dataframe, path in (
        (daily_ic, daily_ic_path),
        (summary, summary_path),
        (coverage, coverage_path),
        (redundancy, redundancy_path),
        (hac_inference, hac_inference_path),
        (missingness, missingness_path),
    ):
        dataframe.to_csv(path, index=False, encoding="utf-8-sig")

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "panel_path": str(PANEL_PATH),
        "adjusted_database_path": str(ADJUSTED_DB_PATH),
        "signal_universe": "historical PIT TOP50 membership on signal date; bar_available=1",
        "feature_input": "one-session log returns from adjusted_close",
        "windows": list(WINDOWS),
        "feature_families": [
            "mean", "variance", "skewness", "excess_kurtosis"
        ],
        "feature_columns": feature_columns,
        "variance_ddof": 1,
        "skewness_estimator": "pandas rolling skew; bias-corrected sample estimator",
        "kurtosis_estimator": "pandas rolling kurt; bias-corrected Fisher excess kurtosis",
        "min_periods": "full window",
        "no_forward_fill": True,
        "target": "1 if adjusted_close[t+5] > adjusted_close[t]; 0 if lower; ties/unavailable excluded",
        "horizon": HORIZON,
        "minimum_cross_section": 20,
        "hac_estimators": ["AM", "ES"],
        "hac_bandwidths_trading_sessions": [4, 10, 20, 60],
        "hac_min_observations": 30,
        "hac_missing_dates_preserved": True,
        "portfolio_metrics_calculated": False,
        "signal_rows_with_valid_target": int(len(observations)),
        "dates": int(observations["tradedate"].nunique()),
        "secids": int(observations["secid"].nunique()),
    }
    write_json(OUTPUT_DIR / "run_metadata.json", metadata)

    write_report(
        OUTPUT_DIR,
        observations,
        daily_ic,
        summary,
        coverage,
        redundancy,
        hac_inference,
        missingness,
        metadata,
    )

    log("=" * 68)
    log("ROLLING STATISTICAL MOMENTS EXPERIMENT COMPLETE")
    log(f"Output directory: {OUTPUT_DIR}")
    log(f"Report: {OUTPUT_DIR / 'research_report.md'}")
    log("=" * 68)


if __name__ == "__main__":
    main()
