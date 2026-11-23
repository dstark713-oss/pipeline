# Folder: scripts/one_use/
# File: validate_breadth_exposure.py
# Purpose: Test the historical breadth-based exposure heuristic without look-ahead.
#
# Research question:
#   Did the documented 25/50/75/100% exposure rule improve the return/risk
#   profile of a PIT TOP50 equal-weight stock sleeve, and is the result
#   sensitive to the 50% breadth threshold?
#
# Timing:
#   Signal is formed after close T from PIT membership and features at T.
#   Portfolio enters at adjusted open on the next MOEX session and exits
#   at adjusted close of that same session. No future membership is used.
#
# Comparisons:
#   100% equity, static 75/50/25% equity, and dynamic rule at 40/50/60%
#   breadth thresholds. Residual allocation earns either 0% or the supplied
#   constant annual cash-yield scenario. The latter is NOT historical LQDT.
#
# Inputs:
#   data/processed/top50/top50_panel.parquet
#   data/interim/primitive_research/primitive_features.parquet
#   data/processed/moex_daily_adjusted.sqlite (read-only)
#
# Outputs:
#   data/interim/screener/breadth_exposure_daily.csv
#   data/interim/screener/breadth_exposure_summary.csv
#
# Run from repository root:
#   python scripts/one_use/validate_breadth_exposure.py --cash-yield 0.12
#
# Limitations:
#   Intraday open-to-close returns only; overnight gaps are excluded.
#   No fees, slippage, taxes, or actual historical LQDT returns.
#   Daily equal-weight rebalancing is a research construction, not the
#   user's live portfolio. Missing next-session outcomes are reported;
#   dates below the coverage threshold are excluded from every strategy.
#   This is a diagnostic test, not proof of causality or a production rule.

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

BOARDS = ("TQBR", "EQBR")
BOARD_PRIORITY = {"TQBR": 0, "EQBR": 1}
EXCLUDED_TICKERS = {"GAZC", "GAZS", "GAZT"}
SUSPENSION_START = pd.Timestamp("2022-02-28")
SUSPENSION_END = pd.Timestamp("2022-03-23")
IS_END = pd.Timestamp("2024-01-29")
VAL_START = pd.Timestamp("2024-01-30")


def log(message: str) -> None:
    print(message, flush=True)


def resolve_column(frame: pd.DataFrame, expected: str) -> str:
    lookup = {str(c).strip().lower(): c for c in frame.columns}
    if expected.lower() not in lookup:
        raise RuntimeError(
            f"Missing column '{expected}'. Available: {list(frame.columns)}"
        )
    return lookup[expected.lower()]


def normalize_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.normalize()


def readonly_connection() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Adjusted DB not found: {DB_PATH}")
    con = sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only = ON")
    return con


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    for path in (PANEL_PATH, FEATURE_PATH):
        if not path.is_file():
            raise FileNotFoundError(f"Required input not found: {path}")

    panel = pd.read_parquet(PANEL_PATH)
    panel = panel[
        [
            resolve_column(panel, "tradedate"),
            resolve_column(panel, "secid"),
            resolve_column(panel, "bar_available"),
        ]
    ].copy()
    panel.columns = ["tradedate", "secid", "bar_available"]
    panel["tradedate"] = normalize_dates(panel["tradedate"])
    panel["secid"] = panel["secid"].astype(str).str.strip().str.upper()
    panel["bar_available"] = pd.to_numeric(
        panel["bar_available"], errors="coerce"
    ).fillna(0).astype(int)
    panel = panel.dropna(subset=["tradedate", "secid"])
    panel = panel[~panel["secid"].isin(EXCLUDED_TICKERS)].copy()

    if panel.duplicated(["tradedate", "secid"]).any():
        raise RuntimeError("Duplicate PIT panel rows for TRADEDATE/SECID.")

    features = pd.read_parquet(FEATURE_PATH)
    features = features[
        [
            resolve_column(features, "tradedate"),
            resolve_column(features, "secid"),
            resolve_column(features, "price_sma20"),
        ]
    ].copy()
    features.columns = ["tradedate", "secid", "price_sma20"]
    features["tradedate"] = normalize_dates(features["tradedate"])
    features["secid"] = features["secid"].astype(str).str.strip().str.upper()
    features["price_sma20"] = pd.to_numeric(
        features["price_sma20"], errors="coerce"
    ).replace([np.inf, -np.inf], np.nan)
    features = features.dropna(subset=["tradedate", "secid"])

    if features.duplicated(["tradedate", "secid"]).any():
        raise RuntimeError("Duplicate primitive feature rows for TRADEDATE/SECID.")

    return panel, features


def build_breadth(panel: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    merged = panel.merge(
        features, on=["tradedate", "secid"], how="left", validate="one_to_one"
    )
    # Match the screener: only actual signal-date bars and valid price_sma20
    # enter the denominator. Missing bars/features are not negative signals.
    valid = merged[
        merged["bar_available"].eq(1) & merged["price_sma20"].notna()
    ].copy()
    valid["above_sma20"] = valid["price_sma20"] > 0

    calendar = pd.DatetimeIndex(sorted(panel["tradedate"].unique()))
    daily = valid.groupby("tradedate")["above_sma20"].agg(
        breadth_sma20="mean",
        breadth_valid_n="count",
    ).reindex(calendar)

    universe_n = panel.groupby("tradedate")["secid"].nunique().reindex(calendar)
    daily["breadth_change_5"] = daily["breadth_sma20"].diff(5)
    daily["breadth_universe_n"] = universe_n
    daily.index.name = "signal_date"
    return daily.reset_index()


def load_price_history(
    secids: list[str],
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    board_marks = ",".join("?" for _ in BOARDS)
    chunks: list[pd.DataFrame] = []

    with readonly_connection() as con:
        cal = pd.read_sql_query(
            f"""
            SELECT DISTINCT tradedate
            FROM "{TABLE_NAME}"
            WHERE boardid IN ({board_marks})
              AND tradedate IS NOT NULL
              AND tradedate >= ?
              AND tradedate <= ?
            ORDER BY tradedate
            """,
            con,
            params=[*BOARDS, start_date.strftime("%Y-%m-%d"),
                    (end_date + pd.Timedelta(days=14)).strftime("%Y-%m-%d")],
        )

        calendar = pd.DatetimeIndex(
            pd.to_datetime(cal["tradedate"], errors="coerce").dropna().unique()
        ).sort_values()
        calendar = calendar[
            (calendar < SUSPENSION_START) | (calendar > SUSPENSION_END)
        ]

        for offset in range(0, len(secids), 350):
            batch = secids[offset:offset + 350]
            ticker_marks = ",".join("?" for _ in batch)
            frame = pd.read_sql_query(
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
                WHERE boardid IN ({board_marks})
                  AND UPPER(TRIM(secid)) IN ({ticker_marks})
                  AND tradedate >= ?
                  AND tradedate <= ?
                ORDER BY tradedate, secid, boardid
                """,
                con,
                params=[
                    *BOARDS, *batch,
                    start_date.strftime("%Y-%m-%d"),
                    (end_date + pd.Timedelta(days=14)).strftime("%Y-%m-%d"),
                ],
            )
            if not frame.empty:
                chunks.append(frame)

    if not chunks:
        raise RuntimeError("No adjusted OHLC rows loaded for PIT TOP50 tickers.")

    prices = pd.concat(chunks, ignore_index=True)
    prices["tradedate"] = normalize_dates(prices["tradedate"])
    for col in ("adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close"):
        prices[col] = pd.to_numeric(prices[col], errors="coerce")

    prices = prices.dropna(subset=["tradedate", "secid", "boardid"])
    prices = prices[
        (prices["tradedate"] < SUSPENSION_START)
        | (prices["tradedate"] > SUSPENSION_END)
    ].copy()

    if prices.duplicated(["secid", "tradedate", "boardid"]).any():
        raise RuntimeError("Duplicate SECID/TRADEDATE/BOARDID in adjusted DB.")

    prices["_valid_ohlc"] = prices[
        ["adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close"]
    ].notna().all(axis=1).astype(int)
    prices["_board_priority"] = prices["boardid"].map(BOARD_PRIORITY).fillna(999)
    prices = (
        prices.sort_values(
            ["secid", "tradedate", "_valid_ohlc", "_board_priority", "boardid"],
            ascending=[True, True, False, True, True],
            kind="mergesort",
        )
        .drop_duplicates(["secid", "tradedate"], keep="first")
    )

    return prices, calendar


def make_daily_stock_returns(
    panel: pd.DataFrame,
    breadth: pd.DataFrame,
    prices: pd.DataFrame,
    market_calendar: pd.DatetimeIndex,
    min_coverage: float,
) -> pd.DataFrame:
    price_lookup = prices.set_index(["tradedate", "secid"])
    memberships = {
        date: group[group["bar_available"].eq(1)]["secid"].tolist()
        for date, group in panel.groupby("tradedate", sort=True)
    }
    breadth_lookup = breadth.set_index("signal_date")
    dates = pd.DatetimeIndex(sorted(memberships))
    rows = []

    for signal_date in dates:
        # Strictly next session: no close-T execution and no same-day return.
        next_pos = market_calendar.searchsorted(signal_date, side="right")
        if next_pos >= len(market_calendar):
            continue
        execution_date = market_calendar[next_pos]

        tickers = memberships[signal_date]
        if not tickers or signal_date not in breadth_lookup.index:
            continue

        returns = []
        for ticker in tickers:
            key = (execution_date, ticker)
            if key not in price_lookup.index:
                continue
            item = price_lookup.loc[key]
            if isinstance(item, pd.DataFrame):
                raise RuntimeError(f"Non-unique price lookup for {key}")
            open_price = item["adjusted_open"]
            close_price = item["adjusted_close"]
            if (
                pd.notna(open_price) and pd.notna(close_price)
                and float(open_price) > 0 and float(close_price) > 0
            ):
                returns.append(float(close_price) / float(open_price) - 1.0)

        coverage = len(returns) / len(tickers)
        b = breadth_lookup.loc[signal_date]
        breadth_value = b["breadth_sma20"]
        breadth_change = b["breadth_change_5"]

        if coverage < min_coverage or len(returns) < 20:
            stock_return = np.nan
        else:
            # Equal-weight among names with a valid executable next-session
            # OHLC pair. Coverage is retained so missingness is visible.
            stock_return = float(np.mean(returns))

        rows.append({
            "signal_date": signal_date,
            "execution_date": execution_date,
            "pit_members_n": len(tickers),
            "outcome_valid_n": len(returns),
            "outcome_coverage": coverage,
            "breadth_sma20": breadth_value,
            "breadth_valid_n": b["breadth_valid_n"],
            "breadth_universe_n": b["breadth_universe_n"],
            "breadth_change_5": breadth_change,
            "equal_weight_stock_return_open_close": stock_return,
        })

    result = pd.DataFrame(rows)
    result = result.dropna(
        subset=["breadth_sma20", "breadth_change_5",
                "equal_weight_stock_return_open_close"]
    ).copy()
    return result.sort_values("signal_date").reset_index(drop=True)


def exposure_rule(breadth: float, change: float, threshold: float) -> float:
    if breadth >= threshold:
        return 1.00 if change > 0 else 0.75
    return 0.50 if change > 0 else 0.25


def metric_row(
    frame: pd.DataFrame,
    strategy_name: str,
    period_name: str,
    cash_yield: float,
    returns: pd.Series,
    exposures: pd.Series,
    stock_returns: pd.Series,
) -> dict:
    r = pd.to_numeric(returns, errors="coerce").dropna()
    e = pd.to_numeric(exposures.reindex(r.index), errors="coerce")
    s = pd.to_numeric(stock_returns.reindex(r.index), errors="coerce")
    if r.empty:
        return {}

    wealth = (1.0 + r).cumprod()
    years = len(r) / 252.0
    cagr = wealth.iloc[-1] ** (1.0 / years) - 1.0 if years > 0 and wealth.iloc[-1] > 0 else np.nan
    vol = r.std(ddof=1) * math.sqrt(252) if len(r) > 1 else np.nan
    cash_daily = (1.0 + cash_yield) ** (1.0 / 252.0) - 1.0
    excess = r - cash_daily
    sharpe = (
        excess.mean() / r.std(ddof=1) * math.sqrt(252)
        if len(r) > 1 and r.std(ddof=1) > 0 else np.nan
    )
    drawdown = wealth / wealth.cummax() - 1.0

    return {
        "period": period_name,
        "strategy": strategy_name,
        "cash_proxy_annual_yield": cash_yield,
        "observations": int(len(r)),
        "total_return": float(wealth.iloc[-1] - 1.0),
        "cagr": float(cagr) if pd.notna(cagr) else np.nan,
        "annualized_volatility": float(vol) if pd.notna(vol) else np.nan,
        "max_drawdown": float(drawdown.min()),
        "sharpe_vs_cash_proxy": float(sharpe) if pd.notna(sharpe) else np.nan,
        "average_equity_exposure": float(e.mean()),
        "average_stock_sleeve_return": float(s.mean()),
        "average_outcome_coverage": float(frame.loc[r.index, "outcome_coverage"].mean()),
        "average_daily_exposure_change": float(e.diff().abs().mean()),
    }


def run_backtest(
    daily: pd.DataFrame,
    cash_yield: float,
) -> pd.DataFrame:
    work = daily.copy().reset_index(drop=True)
    cash_daily = (1.0 + cash_yield) ** (1.0 / 252.0) - 1.0
    work["cash_proxy_return_0"] = 0.0
    work["cash_proxy_return_configured"] = cash_daily

    strategies: dict[str, pd.Series] = {
        "all_equity_100": pd.Series(1.0, index=work.index),
        "static_equity_75": pd.Series(0.75, index=work.index),
        "static_equity_50": pd.Series(0.50, index=work.index),
        "static_equity_25": pd.Series(0.25, index=work.index),
    }
    for threshold in (0.40, 0.50, 0.60):
        strategies[f"breadth_rule_threshold_{int(threshold * 100)}"] = pd.Series(
            [
                exposure_rule(float(b), float(d), threshold)
                for b, d in zip(work["breadth_sma20"], work["breadth_change_5"])
            ],
            index=work.index,
        )

    for name, exposure in strategies.items():
        work[f"{name}_exposure"] = exposure
        work[f"{name}_return_cash0"] = (
            exposure * work["equal_weight_stock_return_open_close"]
        )
        work[f"{name}_return_configured_cash"] = (
            exposure * work["equal_weight_stock_return_open_close"]
            + (1.0 - exposure) * cash_daily
        )

    return work


def build_summary(daily: pd.DataFrame, cash_yield: float) -> pd.DataFrame:
    rows = []
    strategies = [
        "all_equity_100", "static_equity_75", "static_equity_50",
        "static_equity_25", "breadth_rule_threshold_40",
        "breadth_rule_threshold_50", "breadth_rule_threshold_60",
    ]
    periods = {
        "FULL": pd.Series(True, index=daily.index),
        "IS_2013_2024-01-29": (
            daily["signal_date"].between(pd.Timestamp("2013-01-02"), IS_END)
        ),
        "VAL_2024-01-30+": (daily["signal_date"] >= VAL_START),
    }

    for period_name, mask in periods.items():
        subset = daily.loc[mask].copy()
        if subset.empty:
            continue
        for strategy in strategies:
            exposure = subset[f"{strategy}_exposure"]
            for cash_name, return_col, rate in (
                ("zero_cash", f"{strategy}_return_cash0", 0.0),
                ("configured_flat_cash_proxy",
                 f"{strategy}_return_configured_cash", cash_yield),
            ):
                row = metric_row(
                    subset,
                    strategy,
                    period_name,
                    rate,
                    subset[return_col],
                    exposure,
                    subset["equal_weight_stock_return_open_close"],
                )
                if row:
                    row["cash_scenario"] = cash_name
                    rows.append(row)

    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Historical PIT breadth exposure diagnostic."
    )
    parser.add_argument(
        "--cash-yield", type=float, default=0.12,
        help="Flat annual effective cash-yield sensitivity (default 0.12). "
             "Not historical LQDT performance.",
    )
    parser.add_argument(
        "--min-coverage", type=float, default=0.80,
        help="Minimum next-session OHLC coverage per date (default 0.80).",
    )
    parser.add_argument("--start-date", default=None, help="Optional YYYY-MM-DD.")
    parser.add_argument("--end-date", default=None, help="Optional YYYY-MM-DD.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 0 <= args.cash_yield <= 1:
        raise ValueError("--cash-yield must be between 0 and 1.")
    if not 0 < args.min_coverage <= 1:
        raise ValueError("--min-coverage must be in (0, 1].")

    log("Loading PIT panel and primitive features...")
    panel, features = load_inputs()
    panel_dates = sorted(panel["tradedate"].unique())
    start_date = pd.Timestamp(args.start_date).normalize() if args.start_date else pd.Timestamp(panel_dates[0]).normalize()
    end_date = pd.Timestamp(args.end_date).normalize() if args.end_date else pd.Timestamp(panel_dates[-1]).normalize()
    if start_date >= end_date:
        raise ValueError("start-date must be earlier than end-date.")

    panel = panel[panel["tradedate"].between(start_date, end_date)].copy()
    features = features[features["tradedate"].between(start_date, end_date)].copy()
    if panel.empty:
        raise RuntimeError("No PIT panel rows in requested date range.")

    log("Reconstructing daily PIT breadth exactly as the screener...")
    breadth = build_breadth(panel, features)

    secids = sorted(panel["secid"].unique().tolist())
    log(f"Loading adjusted OHLC for {len(secids):,} PIT tickers...")
    prices, market_calendar = load_price_history(
        secids, start_date, end_date
    )

    log("Building next-session open-to-close returns...")
    daily = make_daily_stock_returns(
        panel, breadth, prices, market_calendar, args.min_coverage
    )
    if daily.empty:
        raise RuntimeError(
            "No dates passed coverage checks. Inspect panel, price history, "
            "or lower --min-coverage only if justified by data quality."
        )

    daily = run_backtest(daily, args.cash_yield)
    summary = build_summary(daily, args.cash_yield)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    daily_path = OUTPUT_DIR / "breadth_exposure_daily.csv"
    summary_path = OUTPUT_DIR / "breadth_exposure_summary.csv"
    daily.to_csv(daily_path, index=False, encoding="utf-8-sig", float_format="%.10g")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig", float_format="%.10g")

    print()
    print("BREADTH EXPOSURE VALIDATION")
    print(f"Signal dates evaluated: {len(daily):,}")
    print(f"Signal range: {daily['signal_date'].min().date()} to {daily['signal_date'].max().date()}")
    print(f"Mean outcome coverage: {daily['outcome_coverage'].mean():.2%}")
    print(f"Configured flat cash proxy: {args.cash_yield:.2%} annual")
    print("WARNING: configured cash proxy is held constant over the entire history; it is not historical LQDT.")
    print()
    display_cols = [
        "period", "strategy", "cash_scenario", "observations",
        "cagr", "annualized_volatility", "max_drawdown",
        "sharpe_vs_cash_proxy", "average_equity_exposure",
    ]
    if not summary.empty:
        print(summary[display_cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print()
    print(f"Daily output:   {daily_path.relative_to(PROJECT_ROOT)}")
    print(f"Summary output: {summary_path.relative_to(PROJECT_ROOT)}")
    print("Read-only SQLite; source panel/features/database were not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
