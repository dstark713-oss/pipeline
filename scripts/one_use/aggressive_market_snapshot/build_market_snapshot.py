from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "moex_daily_adjusted.sqlite"
MEMBERSHIP_PATH = PROJECT_ROOT / "data" / "processed" / "top50" / "top50_membership.parquet"
OUTPUT_DIR = PROJECT_ROOT / "data" / "interim" / "aggressive_market_snapshot"

APPROVED_BOARDS = ("TQBR", "EQBR")
PRICE_BOARD_PRIORITY = {"TQBR": 0, "EQBR": 1}
HORIZONS = (1, 5, 10, 20)
VOL_WINDOWS = (20, 60)
ANNUALIZATION = 252


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a historical per-ticker snapshot for the PIT TOP50 universe."
    )
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--membership", type=Path, default=MEMBERSHIP_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--min-benchmark-coverage",
        type=float,
        default=0.80,
        help="Minimum valid prior-universe share required for a daily EW benchmark return.",
    )
    return parser.parse_args()


def log(message: str) -> None:
    print(message, flush=True)


def readonly_connection(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def load_membership(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"PIT TOP50 membership not found: {path}")

    membership = pd.read_parquet(path)
    required = {"tradedate", "secid", "rank", "ranking_asof_date"}
    missing = required - set(membership.columns)
    if missing:
        raise RuntimeError(f"Membership is missing columns: {sorted(missing)}")

    membership = membership.copy()
    membership["tradedate"] = pd.to_datetime(membership["tradedate"]).dt.normalize()
    membership["ranking_asof_date"] = pd.to_datetime(
        membership["ranking_asof_date"]
    ).dt.normalize()
    membership["secid"] = membership["secid"].astype(str).str.upper()

    if membership.empty:
        raise RuntimeError("PIT TOP50 membership is empty.")
    if membership.duplicated(["tradedate", "secid"]).any():
        raise RuntimeError("Duplicate date/ticker rows in PIT TOP50 membership.")
    if not (membership["ranking_asof_date"] < membership["tradedate"]).all():
        raise RuntimeError("Look-ahead check failed: ranking date must precede membership date.")
    if (membership.groupby("tradedate")["secid"].nunique() > 50).any():
        raise RuntimeError("PIT membership contains more than 50 tickers on a date.")

    return membership.sort_values(["tradedate", "rank", "secid"]).reset_index(drop=True)


def load_adjusted_daily(db_path: Path, start_date: pd.Timestamp) -> pd.DataFrame:
    if not db_path.is_file():
        raise FileNotFoundError(f"Adjusted SQLite database not found: {db_path}")

    with readonly_connection(db_path) as connection:
        columns = {
            row[1].lower(): row[1]
            for row in connection.execute(
                'PRAGMA table_info("adjusted_daily_bars")'
            ).fetchall()
        }
        required = {
            "secid", "tradedate", "boardid", "adjusted_open",
            "adjusted_high", "adjusted_low", "adjusted_close",
            "adjusted_volume", "value",
        }
        missing = required - set(columns)
        if missing:
            raise RuntimeError(
                f"adjusted_daily_bars is missing columns: {sorted(missing)}"
            )

        selected = [
            "secid", "tradedate", "boardid", "adjusted_open",
            "adjusted_high", "adjusted_low", "adjusted_close",
            "adjusted_volume", "value",
        ]
        select_sql = ", ".join(
            f'"{columns[name]}" AS "{name}"' for name in selected
        )
        board_placeholders = ",".join("?" for _ in APPROVED_BOARDS)
        query = f"""
            SELECT {select_sql}
            FROM adjusted_daily_bars
            WHERE tradedate >= ?
              AND boardid IN ({board_placeholders})
            ORDER BY tradedate, secid, boardid
        """
        raw = pd.read_sql_query(
            query,
            connection,
            params=[start_date.strftime("%Y-%m-%d"), *APPROVED_BOARDS],
        )

    if raw.empty:
        raise RuntimeError("No adjusted daily bars returned from SQLite.")

    raw["secid"] = raw["secid"].astype(str).str.upper()
    raw["boardid"] = raw["boardid"].astype(str).str.upper()
    raw["tradedate"] = pd.to_datetime(raw["tradedate"]).dt.normalize()

    numeric = [
        "adjusted_open", "adjusted_high", "adjusted_low",
        "adjusted_close", "adjusted_volume", "value",
    ]
    for column in numeric:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")

    keys = ["secid", "tradedate"]
    if raw.duplicated(["secid", "tradedate", "boardid"]).any():
        raise RuntimeError("Duplicate SECID/date/BOARDID rows in adjusted database.")

    # Activity is additive across approved boards, matching the TOP50 panel builder.
    activity = (
        raw.groupby(keys, as_index=False)
        .agg(
            value=("value", "sum"),
            volume=("adjusted_volume", "sum"),
            n_boards=("boardid", "nunique"),
        )
    )

    # OHLC is not additive. Match panel policy: valid OHLC first, then TQBR priority.
    prices = raw.copy()
    price_fields = [
        "adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close"
    ]
    prices["_valid_price"] = prices[price_fields].notna().all(axis=1).astype("int8")
    prices["_priority"] = prices["boardid"].map(PRICE_BOARD_PRIORITY).fillna(999)
    prices = prices.sort_values(
        keys + ["_valid_price", "_priority", "boardid"],
        ascending=[True, True, False, True, True],
        kind="mergesort",
    ).drop_duplicates(keys, keep="first")

    prices = prices[
        ["secid", "tradedate", "adjusted_close", "boardid"]
    ].rename(columns={"boardid": "price_board"})

    daily = activity.merge(
        prices, on=keys, how="left", validate="one_to_one"
    )
    if daily.duplicated(keys).any():
        raise RuntimeError("Duplicate SECID/date rows after board aggregation.")

    return daily


def build_matrices(
    daily: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    close = daily.pivot(
        index="tradedate", columns="secid", values="adjusted_close"
    ).reindex(calendar).sort_index()

    value = daily.pivot(
        index="tradedate", columns="secid", values="value"
    ).reindex(calendar).sort_index()

    features: dict[str, pd.DataFrame] = {}

    one_day = close.pct_change(fill_method=None)
    features["return_1d"] = one_day

    for horizon in (5, 10, 20):
        result = close.div(close.shift(horizon)).sub(1.0)
        complete = (
            close.notna()
            .rolling(horizon + 1, min_periods=horizon + 1)
            .sum()
            .eq(horizon + 1)
        )
        features[f"return_{horizon}d"] = result.where(complete)

    log_returns = np.log(close.div(close.shift(1)))
    for window in VOL_WINDOWS:
        features[f"realized_vol_{window}d_ann"] = (
            log_returns.rolling(window, min_periods=window)
            .std(ddof=1)
            * np.sqrt(ANNUALIZATION)
        )

    for window in (20, 60):
        rolling_high = close.rolling(window, min_periods=window).max()
        features[f"drawdown_from_{window}d_high"] = close.div(rolling_high).sub(1.0)

    features["momentum_5d_acceleration"] = (
        features["return_5d"] - features["return_5d"].shift(5)
    )
    features["momentum_10d_acceleration"] = (
        features["return_10d"] - features["return_10d"].shift(10)
    )

    # Missing observations after a ticker's first recorded bar mean zero activity,
    # consistent with the PIT panel's turnover treatment. No price is forward-filled.
    exposure = pd.DataFrame(False, index=calendar, columns=value.columns)
    first_dates = daily.groupby("secid")["tradedate"].min()
    for ticker, first_date in first_dates.items():
        if ticker in exposure.columns:
            exposure[ticker] = calendar >= first_date

    value_for_rolling = value.where(exposure, np.nan).fillna(0.0)
    turnover_median = value_for_rolling.rolling(20, min_periods=20).median()
    features["turnover_vs_20d_median"] = value_for_rolling.div(
        turnover_median.where(turnover_median > 0)
    )
    features["turnover_value"] = value_for_rolling

    return features, one_day


def build_equal_weight_benchmark(
    membership: pd.DataFrame,
    one_day_returns: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    min_coverage: float,
) -> pd.DataFrame:
    members_by_date = {
        date: group["secid"].tolist()
        for date, group in membership.groupby("tradedate", sort=True)
    }

    records = []
    for position, date in enumerate(calendar):
        if position == 0:
            continue

        prior_date = calendar[position - 1]
        prior_members = members_by_date.get(prior_date, [])
        if not prior_members:
            records.append({
                "tradedate": date,
                "benchmark_return_1d": np.nan,
                "benchmark_n_members": 0,
                "benchmark_n_valid": 0,
                "benchmark_coverage": np.nan,
            })
            continue

        available_columns = [
            ticker for ticker in prior_members
            if ticker in one_day_returns.columns
        ]
        values = one_day_returns.loc[date, available_columns].dropna()
        n_members = len(prior_members)
        n_valid = int(values.size)
        coverage = n_valid / n_members if n_members else np.nan

        benchmark_return = (
            float(values.mean())
            if coverage >= min_coverage and n_valid > 0
            else np.nan
        )

        records.append({
            "tradedate": date,
            "benchmark_return_1d": benchmark_return,
            "benchmark_n_members": n_members,
            "benchmark_n_valid": n_valid,
            "benchmark_coverage": coverage,
        })

    benchmark = pd.DataFrame.from_records(records)
    if benchmark.empty:
        raise RuntimeError("Could not construct daily equal-weight benchmark.")

    benchmark = benchmark.set_index("tradedate").reindex(calendar)
    for horizon in (5, 10, 20):
        benchmark[f"benchmark_return_{horizon}d"] = (
            (1.0 + benchmark["benchmark_return_1d"])
            .rolling(horizon, min_periods=horizon)
            .apply(np.prod, raw=True)
            - 1.0
        )

    return benchmark.reset_index()


def matrix_values_for_membership(
    matrix: pd.DataFrame,
    membership: pd.DataFrame,
) -> np.ndarray:
    series = matrix.rename_axis(index="tradedate", columns="secid").stack()
    index = pd.MultiIndex.from_arrays(
        [membership["tradedate"], membership["secid"]],
        names=["tradedate", "secid"],
    )
    return series.reindex(index).to_numpy()


def build_snapshot(
    membership: pd.DataFrame,
    daily: pd.DataFrame,
    features: dict[str, pd.DataFrame],
    benchmark: pd.DataFrame,
) -> pd.DataFrame:
    snapshot = membership.copy()
    for name, matrix in features.items():
        snapshot[name] = matrix_values_for_membership(matrix, snapshot)

    current_bars = daily[
        ["tradedate", "secid", "adjusted_close", "value", "volume", "n_boards", "price_board"]
    ].copy()
    snapshot = snapshot.merge(
        current_bars,
        on=["tradedate", "secid"],
        how="left",
        validate="one_to_one",
    )
    snapshot["bar_available"] = snapshot["adjusted_close"].notna().astype("int8")

    benchmark_columns = [
        "tradedate", "benchmark_return_1d", "benchmark_return_5d",
        "benchmark_return_10d", "benchmark_return_20d",
        "benchmark_n_members", "benchmark_n_valid", "benchmark_coverage",
    ]
    snapshot = snapshot.merge(
        benchmark[benchmark_columns],
        on="tradedate",
        how="left",
        validate="many_to_one",
    )

    for horizon in (5, 10, 20):
        snapshot[f"rs_{horizon}d"] = (
            snapshot[f"return_{horizon}d"]
            - snapshot[f"benchmark_return_{horizon}d"]
        )

    snapshot = snapshot.sort_values(
        ["tradedate", "rank", "secid"]
    ).reset_index(drop=True)

    numeric = snapshot.select_dtypes(include=[np.number])
    if np.isinf(numeric.to_numpy(dtype=float, na_value=np.nan)).any():
        raise RuntimeError("Infinite values found in snapshot.")

    return snapshot


def print_report(snapshot: pd.DataFrame, benchmark: pd.DataFrame) -> None:
    dates = pd.DatetimeIndex(snapshot["tradedate"].drop_duplicates().sort_values())
    latest_date = dates.max()
    latest = snapshot.loc[snapshot["tradedate"] == latest_date].copy()
    latest = latest.sort_values("rs_5d", ascending=False, na_position="last")

    coverage = benchmark["benchmark_coverage"].dropna()
    latest_coverage = benchmark.loc[
        benchmark["tradedate"] == latest_date, "benchmark_coverage"
    ]
    coverage_text = (
        f"{float(latest_coverage.iloc[0]):.1%}"
        if not latest_coverage.empty and pd.notna(latest_coverage.iloc[0])
        else "n/a"
    )

    log("")
    log("=" * 72)
    log("AGGRESSIVE MARKET SNAPSHOT")
    log("=" * 72)
    log(f"History: {dates.min().date()} .. {latest_date.date()} | sessions: {len(dates):,}")
    log(f"Rows: {len(snapshot):,} | unique tickers: {snapshot['secid'].nunique():,}")
    log(f"Latest PIT universe: {len(latest):,} | benchmark coverage: {coverage_text}")
    log(
        "Median daily benchmark coverage: "
        f"{float(coverage.median()):.1%}" if not coverage.empty
        else "Median daily benchmark coverage: n/a"
    )

    columns = [
        "secid", "rank", "return_5d", "rs_5d", "return_20d",
        "rs_20d", "realized_vol_20d_ann", "turnover_vs_20d_median",
    ]
    available = [column for column in columns if column in latest.columns]

    log("")
    log("TOP 5 RELATIVE STRENGTH (5D)")
    log(latest[available].head(5).to_string(
        index=False, float_format=lambda value: f"{value:+.3f}"
    ))
    log("")
    log("BOTTOM 5 RELATIVE STRENGTH (5D)")
    log(latest[available].tail(5).sort_values(
        "rs_5d", ascending=True, na_position="last"
    ).to_string(index=False, float_format=lambda value: f"{value:+.3f}"))
    log("=" * 72)


def main() -> int:
    args = parse_args()
    if not 0.0 < args.min_benchmark_coverage <= 1.0:
        raise ValueError("--min-benchmark-coverage must be in (0, 1].")

    log("Loading point-in-time TOP50 membership...")
    membership = load_membership(args.membership)
    calendar = pd.DatetimeIndex(
        membership["tradedate"].drop_duplicates().sort_values(),
        name="tradedate",
    )

    # Load warm-up history before the first membership date so early returns
    # and rolling statistics can use prior observations.
    log("Loading adjusted daily bars...")
    daily = load_adjusted_daily(args.db, calendar.min())

    log("Building per-ticker time-series features...")
    features, one_day_returns = build_matrices(daily, calendar)

    log("Building lagged equal-weight PIT TOP50 benchmark...")
    benchmark = build_equal_weight_benchmark(
        membership,
        one_day_returns,
        calendar,
        args.min_benchmark_coverage,
    )

    log("Joining historical ticker snapshots...")
    snapshot = build_snapshot(membership, daily, features, benchmark)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = args.output_dir / "market_snapshot.parquet"
    benchmark_path = args.output_dir / "equal_weight_top50_benchmark.parquet"
    latest_path = args.output_dir / "latest_snapshot.csv"
    summary_path = args.output_dir / "summary.json"

    snapshot.to_parquet(snapshot_path, index=False, compression="zstd")
    benchmark.to_parquet(benchmark_path, index=False, compression="zstd")

    latest_date = snapshot["tradedate"].max()
    latest = snapshot.loc[snapshot["tradedate"] == latest_date].copy()
    latest.to_csv(latest_path, index=False, encoding="utf-8-sig")

    summary = {
        "snapshot_start": str(snapshot["tradedate"].min().date()),
        "snapshot_end": str(latest_date.date()),
        "sessions": int(snapshot["tradedate"].nunique()),
        "snapshot_rows": int(len(snapshot)),
        "unique_tickers": int(snapshot["secid"].nunique()),
        "latest_universe_size": int(len(latest)),
        "benchmark": "daily rebalanced equal-weight PIT TOP50",
        "benchmark_membership_lag_sessions": 1,
        "benchmark_min_coverage": args.min_benchmark_coverage,
        "benchmark_median_daily_coverage": (
            float(benchmark["benchmark_coverage"].median())
            if benchmark["benchmark_coverage"].notna().any()
            else None
        ),
        "price_policy": "TQBR preferred, EQBR fallback; no forward-fill",
        "activity_policy": "VALUE and adjusted volume summed across TQBR/EQBR",
        "features": sorted(features.keys()),
        "outputs": {
            "snapshot": str(snapshot_path),
            "benchmark": str(benchmark_path),
            "latest_snapshot": str(latest_path),
        },
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print_report(snapshot, benchmark)
    log(f"Full snapshot: {snapshot_path}")
    log(f"Benchmark:     {benchmark_path}")
    log(f"Latest CSV:    {latest_path}")
    log(f"Summary:       {summary_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
