# Folder: scripts/experiments/primitives/
# File: 01_research_report.py
# Purpose: Run the first primitive research pass and produce an IC/breadth report.
#
# Universe policy:
# - Signal-date universe is strictly the point-in-time TOP50 panel.
# - Adjusted daily bars are used only to build lookback history and measure
#   outcomes for securities that were already in the TOP50 on signal date.
# - A security does not enter the signal-date universe because it exists
#   in adjusted_daily_bars.
#
# Execution:
#   python scripts/experiments/primitives/01_research_report.py

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

PANEL_PATH = (
    PROJECT_ROOT / "data" / "processed" / "top50" / "top50_panel.parquet"
)
ADJUSTED_DB_PATH = (
    PROJECT_ROOT / "data" / "processed" / "moex_daily_adjusted.sqlite"
)
OUTPUT_DIR = PROJECT_ROOT / "data" / "interim" / "primitive_research"

TABLE_NAME = "adjusted_daily_bars"
APPROVED_BOARDS = ("TQBR", "EQBR")
PRICE_BOARD_PRIORITY = {"TQBR": 0, "EQBR": 1}
EXCLUDED_TICKERS = {"GAZC", "GAZS", "GAZT"}
SUSPENSION_START = "2022-02-28"
SUSPENSION_END = "2022-03-23"

FORWARD_HORIZONS = (5, 10, 20)
MIN_CROSS_SECTION = 20
HAC_MAX_LAGS_CAP = 19

# Predeclared broad subperiods for stability diagnostics.
SUBPERIODS = (
    ("2005-2012", "2005-01-01", "2012-12-31"),
    ("2013-2019", "2013-01-01", "2019-12-31"),
    ("2020+", "2020-01-01", "2099-12-31"),
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def readonly_connection(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def validate_inputs() -> None:
    if not PANEL_PATH.is_file():
        raise FileNotFoundError(f"TOP50 panel not found: {PANEL_PATH}")
    if not ADJUSTED_DB_PATH.is_file():
        raise FileNotFoundError(
            f"Adjusted SQLite database not found: {ADJUSTED_DB_PATH}"
        )


def safe_corr(x: pd.Series, y: pd.Series, method: str = "pearson") -> float:
    pair = pd.concat([x, y], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(pair) < 3 or pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
        return np.nan
    return float(pair.iloc[:, 0].corr(pair.iloc[:, 1], method=method))


def normal_two_sided_pvalue(t_stat: float) -> float:
    if not np.isfinite(t_stat):
        return np.nan
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def newey_west_mean_test(values: pd.Series, max_lags: int) -> tuple[float, float]:
    """
    HAC t-statistic for the mean of a time series.
    Bartlett weights are used for autocovariances.
    """
    x = pd.to_numeric(values, errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    ).dropna().to_numpy(dtype=float)

    n = len(x)
    if n < 10:
        return np.nan, np.nan

    mean = float(np.mean(x))
    residual = x - mean
    lag_count = min(max_lags, n - 1)

    long_run_variance = float(np.dot(residual, residual) / n)

    for lag in range(1, lag_count + 1):
        covariance = float(
            np.dot(residual[lag:], residual[:-lag]) / n
        )
        weight = 1.0 - lag / (lag_count + 1.0)
        long_run_variance += 2.0 * weight * covariance

    long_run_variance = max(long_run_variance, 0.0)
    standard_error = math.sqrt(long_run_variance / n)

    if standard_error == 0:
        return np.nan, np.nan

    t_stat = mean / standard_error
    return float(t_stat), normal_two_sided_pvalue(t_stat)


def benjamini_hochberg(pvalues: pd.Series) -> pd.Series:
    values = pd.to_numeric(pvalues, errors="coerce")
    result = pd.Series(np.nan, index=values.index, dtype=float)
    valid = values.dropna()

    if valid.empty:
        return result

    ordered = valid.sort_values()
    m = len(ordered)
    adjusted = ordered.to_numpy() * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    result.loc[ordered.index] = np.clip(adjusted, 0.0, 1.0)
    return result


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


# ============================================================
# LOAD POINT-IN-TIME TOP50 MEMBERSHIP
# ============================================================

def load_panel() -> pd.DataFrame:
    log(f"Reading TOP50 panel: {PANEL_PATH}")
    panel = pd.read_parquet(PANEL_PATH)

    required = {
        "tradedate", "secid", "rank", "universe_size",
        "adjusted_close", "bar_available",
    }
    missing = required - set(panel.columns)
    if missing:
        raise RuntimeError(f"TOP50 panel is missing columns: {sorted(missing)}")

    panel["tradedate"] = pd.to_datetime(panel["tradedate"], errors="coerce")
    panel["secid"] = panel["secid"].astype(str).str.upper()
    panel = panel.dropna(subset=["tradedate", "secid"]).copy()
    panel = panel[~panel["secid"].isin(EXCLUDED_TICKERS)].copy()

    if panel.duplicated(["tradedate", "secid"]).any():
        raise RuntimeError("Duplicate tradedate/SECID rows in TOP50 panel.")

    panel["bar_available"] = pd.to_numeric(
        panel["bar_available"], errors="coerce"
    ).fillna(0).astype(int)

    panel["adjusted_close"] = pd.to_numeric(
        panel["adjusted_close"], errors="coerce"
    )

    log(
        f"Panel rows: {len(panel):,}; dates: {panel['tradedate'].nunique():,}; "
        f"tickers: {panel['secid'].nunique():,}"
    )
    return panel


# ============================================================
# LOAD PRICE HISTORY FOR THE PANEL'S SECID SET
# ============================================================

def load_market_calendar(connection: sqlite3.Connection) -> pd.DatetimeIndex:
    placeholders = ",".join("?" for _ in APPROVED_BOARDS)
    query = f"""
        SELECT DISTINCT tradedate
        FROM "{TABLE_NAME}"
        WHERE boardid IN ({placeholders})
          AND tradedate IS NOT NULL
        ORDER BY tradedate
    """
    dates = pd.read_sql_query(query, connection, params=list(APPROVED_BOARDS))
    calendar = pd.DatetimeIndex(pd.to_datetime(dates["tradedate"], errors="coerce"))
    calendar = calendar.dropna().unique().sort_values()
    calendar = calendar[
        (calendar < pd.Timestamp(SUSPENSION_START))
        | (calendar > pd.Timestamp(SUSPENSION_END))
    ]
    return calendar


def load_adjusted_history(secids: list[str]) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    log("Opening adjusted SQLite read-only for historical lookback/outcomes...")
    with readonly_connection(ADJUSTED_DB_PATH) as connection:
        calendar = load_market_calendar(connection)

        chunks = []
        chunk_size = 400
        board_placeholders = ",".join("?" for _ in APPROVED_BOARDS)

        for start in range(0, len(secids), chunk_size):
            batch = secids[start:start + chunk_size]
            secid_placeholders = ",".join("?" for _ in batch)

            query = f"""
                SELECT
                    secid,
                    tradedate,
                    boardid,
                    adjusted_open,
                    adjusted_high,
                    adjusted_low,
                    adjusted_close,
                    adjusted_volume,
                    value
                FROM "{TABLE_NAME}"
                WHERE boardid IN ({board_placeholders})
                  AND secid IN ({secid_placeholders})
                  AND tradedate IS NOT NULL
                ORDER BY tradedate, secid, boardid
            """

            frame = pd.read_sql_query(
                query,
                connection,
                params=[*APPROVED_BOARDS, *batch],
            )
            if not frame.empty:
                chunks.append(frame)

    if not chunks:
        raise RuntimeError("No adjusted daily bars found for TOP50 panel tickers.")

    source = pd.concat(chunks, ignore_index=True)
    source["secid"] = source["secid"].astype(str).str.upper()
    source["boardid"] = source["boardid"].astype(str).str.upper()
    source["tradedate"] = pd.to_datetime(source["tradedate"], errors="coerce")

    source = source.dropna(subset=["secid", "tradedate"]).copy()
    source = source[~source["secid"].isin(EXCLUDED_TICKERS)].copy()
    source = source[
        (source["tradedate"] < pd.Timestamp(SUSPENSION_START))
        | (source["tradedate"] > pd.Timestamp(SUSPENSION_END))
    ].copy()

    numeric = [
        "adjusted_open", "adjusted_high", "adjusted_low",
        "adjusted_close", "adjusted_volume", "value",
    ]
    for column in numeric:
        source[column] = pd.to_numeric(source[column], errors="coerce")

    if source.duplicated(["secid", "tradedate", "boardid"]).any():
        raise RuntimeError(
            "Duplicate SECID/TRADEDATE/BOARDID rows in adjusted history."
        )

    # Activity is summed across TQBR/EQBR. OHLC is selected from one board:
    # prefer a row with complete OHLC, then TQBR, then EQBR.
    source["value"] = source["value"].fillna(0.0)
    source["adjusted_volume"] = source["adjusted_volume"].fillna(0.0)

    activity = (
        source.groupby(["secid", "tradedate"], as_index=False)
        .agg(
            value=("value", "sum"),
            adjusted_volume=("adjusted_volume", "sum"),
        )
    )

    source["_valid_ohlc"] = (
        source[
            ["adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close"]
        ].notna().all(axis=1).astype("int8")
    )
    source["_board_priority"] = (
        source["boardid"].map(PRICE_BOARD_PRIORITY).fillna(999)
    )
    prices = source.sort_values(
        ["secid", "tradedate", "_valid_ohlc", "_board_priority", "boardid"],
        ascending=[True, True, False, True, True],
        kind="mergesort",
    ).drop_duplicates(["secid", "tradedate"], keep="first")

    prices = prices[
        [
            "secid", "tradedate", "adjusted_open", "adjusted_high",
            "adjusted_low", "adjusted_close", "boardid",
        ]
    ].rename(columns={"boardid": "price_board"})

    history = activity.merge(
        prices,
        on=["secid", "tradedate"],
        how="left",
        validate="one_to_one",
    )

    history = history.sort_values(
        ["secid", "tradedate"]
    ).reset_index(drop=True)

    log(
        f"Adjusted history rows after board aggregation: {len(history):,}; "
        f"tickers: {history['secid'].nunique():,}; "
        f"calendar sessions: {len(calendar):,}"
    )
    return history, calendar


# ============================================================
# CALCULATE PRIMITIVES AND FORWARD RETURNS
# ============================================================

CROSS_SECTIONAL_FEATURES = [
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
    "up_down_turnover_ratio_20",
    "positive_turnover_share_20",
]

BREADTH_FEATURES = [
    "breadth_sma20",
    "breadth_sma50",
    "breadth_sma200",
    "breadth_change_5",
    "breadth_change_20",
]


def build_ticker_features(
    ticker_history: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    ticker = ticker_history["secid"].iloc[0]
    indexed = ticker_history.set_index("tradedate").reindex(calendar)

    close = pd.to_numeric(indexed["adjusted_close"], errors="coerce")
    open_ = pd.to_numeric(indexed["adjusted_open"], errors="coerce")

    # Match the panel's activity convention: after the first observed bar,
    # a missing ticker/session observation contributes zero turnover.
    # Before the first observed bar, turnover history remains unknown.
    first_observed = ticker_history["tradedate"].min()
    turnover = pd.to_numeric(indexed["value"], errors="coerce")
    turnover = turnover.fillna(0.0)
    turnover.loc[turnover.index < first_observed] = np.nan

    daily_return = close.pct_change(fill_method=None)

    sma20 = close.rolling(20, min_periods=20).mean()
    sma50 = close.rolling(50, min_periods=50).mean()
    sma200 = close.rolling(200, min_periods=200).mean()

    residual20 = close - sma20
    residual_std20 = residual20.rolling(20, min_periods=20).std(ddof=1)

    features = pd.DataFrame(index=calendar)
    features["secid"] = ticker

    features["price_sma20"] = close / sma20 - 1.0
    features["sma20_sma50"] = sma20 / sma50 - 1.0
    features["sma50_sma200"] = sma50 / sma200 - 1.0

    features["return_5"] = close / close.shift(5) - 1.0
    features["return_20"] = close / close.shift(20) - 1.0
    features["return_60"] = close / close.shift(60) - 1.0

    features["realized_vol_20"] = (
        daily_return.rolling(20, min_periods=20).std(ddof=1) * math.sqrt(252)
    )
    features["realized_vol_60"] = (
        daily_return.rolling(60, min_periods=60).std(ddof=1) * math.sqrt(252)
    )

    features["drawdown_20"] = (
        close / close.rolling(20, min_periods=20).max() - 1.0
    )
    features["drawdown_60"] = (
        close / close.rolling(60, min_periods=60).max() - 1.0
    )

    mean_turnover20 = turnover.rolling(20, min_periods=20).mean()
    features["turnover_ratio_20"] = turnover / mean_turnover20

    features["rebound_20"] = (
        close / close.rolling(20, min_periods=20).min() - 1.0
    )
    features["rebound_60"] = (
        close / close.rolling(60, min_periods=60).min() - 1.0
    )

    features["zscore_sma20_20"] = residual20 / residual_std20

    return20 = features["return_20"]
    features["momentum_acceleration_20"] = return20 - return20.shift(5)

    net_move20 = (close - close.shift(20)).abs()
    path_length20 = close.diff().abs().rolling(20, min_periods=20).sum()
    features["efficiency_ratio_20"] = net_move20 / path_length20

    up_mask = daily_return > 0
    down_mask = daily_return < 0
    up_turnover = turnover.where(up_mask, 0.0)
    down_turnover = turnover.where(down_mask, 0.0)

    up_count = up_mask.astype(float).rolling(20, min_periods=20).sum()
    down_count = down_mask.astype(float).rolling(20, min_periods=20).sum()

    mean_up_turnover = (
        up_turnover.rolling(20, min_periods=20).sum() / up_count.replace(0, np.nan)
    )
    mean_down_turnover = (
        down_turnover.rolling(20, min_periods=20).sum()
        / down_count.replace(0, np.nan)
    )
    features["up_down_turnover_ratio_20"] = (
        mean_up_turnover / mean_down_turnover
    )

    total_turnover20 = turnover.rolling(20, min_periods=20).sum()
    features["positive_turnover_share_20"] = (
        up_turnover.rolling(20, min_periods=20).sum()
        / total_turnover20.replace(0, np.nan)
    )

    # Signal is observed after close T. Outcome starts at the next session's
    # open and ends at close T+h. No same-close execution assumption.
    for horizon in FORWARD_HORIZONS:
        features[f"forward_return_{horizon}"] = (
            close.shift(-horizon) / open_.shift(-1) - 1.0
        )

    return features.rename_axis("tradedate").reset_index()


def build_feature_frame(
    panel: pd.DataFrame,
    history: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    log("Calculating per-ticker time-series primitives...")
    membership = panel[
        ["tradedate", "secid", "rank", "universe_size", "bar_available"]
    ].copy()

    membership = membership[
        membership["bar_available"].eq(1)
    ].copy()

    history_groups = {
        ticker: group
        for ticker, group in history.groupby("secid", sort=False)
    }

    chunks = []
    selected_tickers = sorted(membership["secid"].unique())

    for number, ticker in enumerate(selected_tickers, start=1):
        ticker_history = history_groups.get(ticker)
        if ticker_history is None:
            continue

        full_features = build_ticker_features(ticker_history, calendar)
        ticker_dates = membership.loc[
            membership["secid"].eq(ticker), "tradedate"
        ].unique()

        selected = full_features[
            full_features["tradedate"].isin(ticker_dates)
        ].copy()
        chunks.append(selected)

        if number % 50 == 0:
            log(f"Processed {number:,}/{len(selected_tickers):,} tickers")

    if not chunks:
        raise RuntimeError("No primitive feature rows were produced.")

    features = pd.concat(chunks, ignore_index=True)
    features["tradedate"] = pd.to_datetime(features["tradedate"])

    frame = membership.merge(
        features,
        on=["tradedate", "secid"],
        how="left",
        validate="one_to_one",
    )

    # Cross-sectional relative-strength ranks are calculated only within
    # the PIT TOP50 cohort on each signal date. Rank 1 means strongest.
    frame["rs_rank_20"] = frame.groupby("tradedate")["return_20"].rank(
        ascending=False, method="average"
    )
    frame["rs_rank_60"] = frame.groupby("tradedate")["return_60"].rank(
        ascending=False, method="average"
    )

    return frame


# ============================================================
# MARKET BREADTH: SEPARATE TIME-SERIES ANALYSIS
# ============================================================

def build_breadth_frame(
    frame: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    log("Calculating point-in-time market breadth...")

    rows = []
    for date, group in frame.groupby("tradedate", sort=True):
        row = {"tradedate": date, "universe_size": int(len(group))}

        for window in (20, 50, 200):
            sma_column = {
                20: None,
                50: None,
                200: None,
            }[window]

            # Recover the SMA comparison from price/SMA ratios:
            # price_sma20 is available directly; longer SMAs are derived
            # from the corresponding moving-average relationship.
            if window == 20:
                values = group["price_sma20"]
            elif window == 50:
                # price/SMA50 = (price/SMA20 + 1) * (SMA20/SMA50 + 1) - 1
                values = (
                    (group["price_sma20"] + 1.0)
                    * (group["sma20_sma50"] + 1.0)
                    - 1.0
                )
            else:
                # price/SMA200 = price/SMA50 * SMA50/SMA200
                price_sma50 = (
                    (group["price_sma20"] + 1.0)
                    * (group["sma20_sma50"] + 1.0)
                    - 1.0
                )
                values = (
                    (price_sma50 + 1.0)
                    * (group["sma50_sma200"] + 1.0)
                    - 1.0
                )

            valid = values.replace([np.inf, -np.inf], np.nan).dropna()
            row[f"breadth_sma{window}"] = (
                float((valid > 0).mean()) if len(valid) else np.nan
            )
            row[f"breadth_sma{window}_n"] = int(len(valid))

        rows.append(row)

    breadth = pd.DataFrame(rows).set_index("tradedate").reindex(calendar)
    for column in ("breadth_sma20", "breadth_sma50", "breadth_sma200"):
        breadth[f"{column}_change_5"] = breadth[column].diff(5)
        breadth[f"{column}_change_20"] = breadth[column].diff(20)

    # The v1 pack uses changes in 20-day breadth, not all six possible
    # breadth-change combinations.
    breadth["breadth_change_5"] = breadth["breadth_sma20"].diff(5)
    breadth["breadth_change_20"] = breadth["breadth_sma20"].diff(20)

    breadth = breadth.reset_index()
    breadth = breadth.rename(columns={"index": "tradedate"})

    # For each signal date, aggregate future returns of the cohort that was
    # in TOP50 on that date. This does not require the ticker to remain TOP50.
    forward_columns = [
        f"forward_return_{h}" for h in FORWARD_HORIZONS
    ]
    outcome = frame.groupby("tradedate")[forward_columns].mean().reset_index()
    outcome = outcome.rename(
        columns={
            column: f"top50_cohort_{column}"
            for column in forward_columns
        }
    )

    breadth = breadth.merge(outcome, on="tradedate", how="left")
    return breadth, outcome


# ============================================================
# CROSS-SECTIONAL IC / RANK IC REPORT
# ============================================================

def calculate_daily_ic(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    log("Calculating daily cross-sectional IC and Rank IC...")
    records = []

    for feature in CROSS_SECTIONAL_FEATURES:
        for horizon in FORWARD_HORIZONS:
            target = f"forward_return_{horizon}"
            subset = frame[["tradedate", feature, target]].copy()

            for date, group in subset.groupby("tradedate", sort=True):
                pair = group[[feature, target]].replace(
                    [np.inf, -np.inf], np.nan
                ).dropna()

                if len(pair) < MIN_CROSS_SECTION:
                    continue

                if pair[feature].nunique() < 2 or pair[target].nunique() < 2:
                    continue

                records.append({
                    "tradedate": date,
                    "primitive": feature,
                    "horizon": horizon,
                    "n": int(len(pair)),
                    "ic": float(pair[feature].corr(pair[target], method="pearson")),
                    "rank_ic": float(pair[feature].corr(pair[target], method="spearman")),
                })

    if not records:
        raise RuntimeError(
            "No daily IC observations. Check history coverage and "
            "MIN_CROSS_SECTION."
        )

    return pd.DataFrame(records)


def summarize_ic(daily_ic: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for (primitive, horizon), group in daily_ic.groupby(
        ["primitive", "horizon"], sort=True
    ):
        ic = group["ic"].dropna()
        rank_ic = group["rank_ic"].dropna()
        lag_count = min(int(horizon) - 1, HAC_MAX_LAGS_CAP)

        ic_t, ic_p = newey_west_mean_test(ic, lag_count)
        rank_t, rank_p = newey_west_mean_test(rank_ic, lag_count)

        row = {
            "primitive": primitive,
            "horizon": int(horizon),
            "n_dates": int(len(group)),
            "mean_n_securities": float(group["n"].mean()),
            "mean_ic": float(ic.mean()),
            "mean_rank_ic": float(rank_ic.mean()),
            "ic_std": float(ic.std(ddof=1)),
            "rank_ic_std": float(rank_ic.std(ddof=1)),
            "ic_ir": (
                float(ic.mean() / ic.std(ddof=1))
                if ic.std(ddof=1) > 0 else np.nan
            ),
            "rank_ic_ir": (
                float(rank_ic.mean() / rank_ic.std(ddof=1))
                if rank_ic.std(ddof=1) > 0 else np.nan
            ),
            "ic_hac_t": ic_t,
            "ic_pvalue": ic_p,
            "rank_ic_hac_t": rank_t,
            "rank_ic_pvalue": rank_p,
        }

        for label, start, end in SUBPERIODS:
            period = group[
                (group["tradedate"] >= pd.Timestamp(start))
                & (group["tradedate"] <= pd.Timestamp(end))
            ]
            row[f"mean_ic_{label}"] = float(period["ic"].mean())
            row[f"mean_rank_ic_{label}"] = float(period["rank_ic"].mean())
            row[f"n_dates_{label}"] = int(len(period))

        rows.append(row)

    summary = pd.DataFrame(rows)
    summary["ic_qvalue"] = benjamini_hochberg(summary["ic_pvalue"])
    summary["rank_ic_qvalue"] = benjamini_hochberg(summary["rank_ic_pvalue"])
    return summary.sort_values(
        ["horizon", "ic_qvalue", "primitive"],
        na_position="last",
    ).reset_index(drop=True)


# ============================================================
# BREADTH REPORT
# ============================================================

def summarize_breadth(breadth: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for feature in BREADTH_FEATURES:
        for horizon in FORWARD_HORIZONS:
            target = f"top50_cohort_forward_return_{horizon}"
            pair = breadth[[feature, target]].replace(
                [np.inf, -np.inf], np.nan
            ).dropna()

            rows.append({
                "primitive": feature,
                "horizon": int(horizon),
                "n_dates": int(len(pair)),
                "pearson_correlation": safe_corr(
                    pair[feature], pair[target], "pearson"
                ),
                "spearman_correlation": safe_corr(
                    pair[feature], pair[target], "spearman"
                ),
                "mean_feature": (
                    float(pair[feature].mean()) if len(pair) else np.nan
                ),
                "mean_future_top50_cohort_return": (
                    float(pair[target].mean()) if len(pair) else np.nan
                ),
            })

    return pd.DataFrame(rows)


# ============================================================
# OUTPUT REPORT
# ============================================================

def write_markdown_report(
    ic_summary: pd.DataFrame,
    breadth_summary: pd.DataFrame,
    panel: pd.DataFrame,
    frame: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    latest_date = panel["tradedate"].max()
    min_date = panel["tradedate"].min()

    lines = [
        "# Primitive Research Report v1",
        "",
        f"- Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"- TOP50 panel period: {min_date.date()} — {latest_date.date()}",
        f"- Panel rows: {len(panel):,}",
        f"- Signal rows with current bar: {int((panel['bar_available'] == 1).sum()):,}",
        f"- Cross-sectional primitives: {len(CROSS_SECTIONAL_FEATURES)}",
        f"- Breadth primitives: {len(BREADTH_FEATURES)}",
        f"- Total primitives: {len(CROSS_SECTIONAL_FEATURES) + len(BREADTH_FEATURES)}",
        "",
        "## Methodology",
        "",
        "- Signal-date universe is the historical point-in-time TOP50 membership.",
        "- Adjusted bars outside TOP50 are used only for ticker lookback history and forward outcome measurement.",
        "- Forward return horizon H = close[T+H] / open[T+1] - 1. Signal is formed after close T.",
        "- No price forward-fill is used.",
        "- Cross-sectional IC is computed per date across available TOP50 members.",
        f"- Dates with fewer than {MIN_CROSS_SECTION} valid cross-sectional observations are omitted.",
        "- IC IR = mean daily IC / standard deviation of daily IC; it is not annualized.",
        "- HAC/Newey-West mean tests use a lag window up to H-1; p-values use a two-sided normal approximation.",
        "- Benjamini-Hochberg q-values are calculated separately for IC and Rank IC test families.",
        "- Breadth is evaluated separately as a time-series market-state variable; it is not assigned cross-sectional IC.",
        "- Breadth outcomes are equal-weight mean forward returns of the TOP50 cohort selected on the signal date.",
        "",
        "## Cross-sectional IC summary",
        "",
        "```\\n" + ic_summary.to_string(index=False, float_format=lambda x: f"{x:.5f}") + "\\n```",
        "",
        "## Market breadth summary",
        "",
        "```\\n" + breadth_summary.to_string(index=False, float_format=lambda x: f"{x:.5f}") + "\\n```",
        "",
        "## Interpretation warnings",
        "",
        "- IC measures information association, not standalone strategy profitability.",
        "- A low q-value does not establish economic usefulness or causal effect.",
        "- Overlapping forward-return horizons create serial dependence; HAC is used as a first correction, not a guarantee against every form of bias.",
        "- Results must be reviewed for period stability, coverage, and feature redundancy before any primitive is selected.",
        "- No primitive selector or production screener is created by this experiment.",
        "",
    ]

    (OUTPUT_DIR / "research_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    validate_inputs()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    panel = load_panel()
    secids = sorted(panel["secid"].unique())

    history, calendar = load_adjusted_history(secids)
    frame = build_feature_frame(panel, history, calendar)

    # The report's signal universe is the panel membership. A panel row with
    # bar_available=0 is intentionally excluded from same-day signal tests.
    frame = frame[frame["bar_available"].eq(1)].copy()

    breadth, _ = build_breadth_frame(frame, calendar)

    daily_ic = calculate_daily_ic(frame)
    ic_summary = summarize_ic(daily_ic)
    breadth_summary = summarize_breadth(breadth)

    daily_ic.to_csv(
        OUTPUT_DIR / "daily_ic.csv",
        index=False,
        encoding="utf-8-sig",
    )
    ic_summary.to_csv(
        OUTPUT_DIR / "cross_sectional_ic_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    breadth.to_csv(
        OUTPUT_DIR / "breadth_daily.csv",
        index=False,
        encoding="utf-8-sig",
    )
    breadth_summary.to_csv(
        OUTPUT_DIR / "breadth_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "panel_path": str(PANEL_PATH),
        "adjusted_database_path": str(ADJUSTED_DB_PATH),
        "signal_universe": "point-in-time TOP50 membership only",
        "adjusted_history_usage": (
            "lookback history and forward outcome measurement only; "
            "does not expand signal-date universe"
        ),
        "panel_rows": int(len(panel)),
        "signal_rows_with_bar": int(len(frame)),
        "panel_start": str(panel["tradedate"].min().date()),
        "panel_end": str(panel["tradedate"].max().date()),
        "tickers": int(panel["secid"].nunique()),
        "calendar_sessions": int(len(calendar)),
        "cross_sectional_primitives": CROSS_SECTIONAL_FEATURES,
        "breadth_primitives": BREADTH_FEATURES,
        "total_primitives": len(CROSS_SECTIONAL_FEATURES) + len(BREADTH_FEATURES),
        "forward_horizons": list(FORWARD_HORIZONS),
        "forward_return_definition": "close[T+H] / open[T+1] - 1",
        "minimum_cross_section": MIN_CROSS_SECTION,
        "no_forward_fill": True,
        "selector_created": False,
        "screener_created": False,
    }
    write_json(OUTPUT_DIR / "run_metadata.json", metadata)
    write_markdown_report(ic_summary, breadth_summary, panel, frame)

    log("=" * 65)
    log("PRIMITIVE RESEARCH REPORT COMPLETE")
    log(f"Output directory: {OUTPUT_DIR}")
    log(f"Report: {OUTPUT_DIR / 'research_report.md'}")
    log("=" * 65)


if __name__ == "__main__":
    main()
