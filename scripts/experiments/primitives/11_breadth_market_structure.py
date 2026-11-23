
# Folder: scripts/experiments/primitives/
# File: 11_breadth_market_structure.py
# Purpose: Test whether breadth describes cross-sectional market
#          coherence and dispersion beyond market returns and
#          median values of the three selected core primitives.
#
# Inputs:
#   data/interim/primitive_research/primitive_features.parquet
#   data/processed/top50/top50_panel.parquet
#   data/processed/moex_daily_adjusted.sqlite (read-only)
#
# Outputs:
#   data/interim/primitive_research/breadth_market_structure/
#
# Run:
#   python scripts/experiments/primitives/11_breadth_market_structure.py

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[3]

FEATURE_PATH = (
    ROOT / "data/interim/primitive_research/primitive_features.parquet"
)

PANEL_PATH = (
    ROOT / "data/processed/top50/top50_panel.parquet"
)

DB_PATH = (
    ROOT / "data/processed/moex_daily_adjusted.sqlite"
)

OUT_DIR = (
    ROOT
    / "data/interim/primitive_research/breadth_market_structure"
)

TABLE = "adjusted_daily_bars"

CORE = [
    "drawdown_60",
    "zscore_sma20_20",
    "realized_vol_60",
]

PAST_RETURNS = [
    "return_5",
    "return_20",
    "return_60",
]

HORIZONS = [5, 10, 20]
MIN_NAMES = 20
BATCH_SIZE = 400

PERIODS = {
    "2005_2012": ("2005-01-01", "2012-12-31"),
    "2013_2019": ("2013-01-01", "2019-12-31"),
    "2020_2026": ("2020-01-01", "2026-12-31"),
}

CONTROL_SPECS = {
    "past_returns": [
        "market_return_5",
        "market_return_20",
        "market_return_60",
    ],
    "core_medians": [
        "median_drawdown_60",
        "median_zscore_sma20_20",
        "median_realized_vol_60",
    ],
    "combined": [
        "market_return_5",
        "market_return_20",
        "market_return_60",
        "median_drawdown_60",
        "median_zscore_sma20_20",
        "median_realized_vol_60",
    ],
}


# ============================================================
# HELPERS
# ============================================================

def log(message: str) -> None:
    print(message, flush=True)


def normalize_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(
        series,
        errors="coerce",
    ).dt.strftime("%Y-%m-%d")


def find_column(columns, candidates):
    lookup = {str(c).lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    raise RuntimeError(
        f"Не найдена колонка из {candidates}. "
        f"Доступные колонки: {list(columns)}"
    )


def safe_numeric(frame: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        )


def bh_adjust(pvalues: pd.Series) -> pd.Series:
    values = pd.to_numeric(
        pvalues,
        errors="coerce",
    )

    result = pd.Series(
        np.nan,
        index=values.index,
        dtype=float,
    )

    valid = values.dropna()

    if valid.empty:
        return result

    ordered = valid.sort_values()
    m = len(ordered)

    adjusted = (
        ordered.to_numpy()
        * m
        / np.arange(1, m + 1)
    )

    adjusted = np.minimum.accumulate(
        adjusted[::-1]
    )[::-1]

    result.loc[ordered.index] = np.clip(
        adjusted,
        0.0,
        1.0,
    )

    return result


# ============================================================
# LOAD INPUTS
# ============================================================

def load_features() -> pd.DataFrame:
    log("Loading primitive feature frame...")

    frame = pd.read_parquet(FEATURE_PATH)

    required = (
        ["secid", "tradedate"]
        + CORE
        + PAST_RETURNS
    )

    missing = [
        column
        for column in required
        if column not in frame.columns
    ]

    if missing:
        raise RuntimeError(
            f"В feature frame отсутствуют колонки: {missing}"
        )

    frame = frame[required].copy()

    frame["secid"] = (
        frame["secid"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    frame["tradedate"] = normalize_dates(
        frame["tradedate"]
    )

    frame = frame.dropna(
        subset=["secid", "tradedate"]
    ).copy()

    if frame.duplicated(["secid", "tradedate"]).any():
        raise RuntimeError(
            "Дубликаты SECID/TRADEDATE в feature frame."
        )

    safe_numeric(
        frame,
        CORE + PAST_RETURNS,
    )

    log(
        f"Feature rows: {len(frame):,}; "
        f"dates: {frame['tradedate'].nunique():,}; "
        f"tickers: {frame['secid'].nunique():,}"
    )

    return frame


def load_calendar() -> list[str]:
    log("Loading TOP50 calendar...")

    panel = pd.read_parquet(PANEL_PATH)

    date_col = find_column(
        panel.columns,
        ["tradedate"],
    )

    dates = normalize_dates(
        panel[date_col]
    ).dropna()

    calendar = sorted(
        dates.unique().tolist()
    )

    if not calendar:
        raise RuntimeError(
            "Не удалось построить торговый календарь."
        )

    log(
        f"Calendar: {len(calendar):,} sessions; "
        f"{calendar[0]} — {calendar[-1]}"
    )

    return calendar


# ============================================================
# LOAD ADJUSTED OHLC
# ============================================================

def load_adjusted_bars(secids: list[str]) -> pd.DataFrame:
    log("Loading adjusted OHLC from SQLite (read-only)...")

    uri = DB_PATH.resolve().as_uri() + "?mode=ro"

    connection = sqlite3.connect(
        uri,
        uri=True,
    )

    connection.execute("PRAGMA query_only = ON")

    try:
        schema = pd.read_sql_query(
            f'PRAGMA table_info("{TABLE}")',
            connection,
        )

        columns = schema["name"].tolist()

        secid_col = find_column(
            columns,
            ["secid"],
        )

        date_col = find_column(
            columns,
            ["tradedate"],
        )

        board_col = find_column(
            columns,
            ["boardid"],
        )

        open_col = find_column(
            columns,
            ["adjusted_open", "open"],
        )

        close_col = find_column(
            columns,
            ["adjusted_close", "close"],
        )

        chunks = []

        secids = sorted(
            set(secids)
        )

        for start in range(
            0,
            len(secids),
            BATCH_SIZE,
        ):
            batch = secids[
                start:start + BATCH_SIZE
            ]

            placeholders = ",".join(
                ["?"] * len(batch)
            )

            query = f"""
                SELECT
                    UPPER(TRIM("{secid_col}")) AS secid,
                    "{date_col}" AS tradedate,
                    UPPER(TRIM("{board_col}")) AS boardid,
                    "{open_col}" AS open,
                    "{close_col}" AS close
                FROM "{TABLE}"
                WHERE UPPER(TRIM("{secid_col}")) IN ({placeholders})
                  AND UPPER(TRIM("{board_col}")) IN ('TQBR', 'EQBR')
            """

            chunk = pd.read_sql_query(
                query,
                connection,
                params=batch,
            )

            if not chunk.empty:
                chunks.append(chunk)

            log(
                f"Loaded SECIDs: "
                f"{min(start + BATCH_SIZE, len(secids)):,}"
                f"/{len(secids):,}"
            )

    finally:
        connection.close()

    if not chunks:
        raise RuntimeError(
            "SQLite не вернула ни одной строки."
        )

    bars = pd.concat(
        chunks,
        ignore_index=True,
    )

    bars["secid"] = (
        bars["secid"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    bars["tradedate"] = normalize_dates(
        bars["tradedate"]
    )

    bars["boardid"] = (
        bars["boardid"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    safe_numeric(
        bars,
        ["open", "close"],
    )

    bars = bars.dropna(
        subset=["secid", "tradedate"]
    ).copy()

    bars = bars[
        (bars["open"] > 0)
        & (bars["close"] > 0)
    ].copy()

    bars["board_priority"] = (
        bars["boardid"]
        .map({
            "TQBR": 0,
            "EQBR": 1,
        })
    )

    bars = bars.sort_values(
        [
            "secid",
            "tradedate",
            "board_priority",
        ],
        kind="mergesort",
    )

    bars = bars.drop_duplicates(
        ["secid", "tradedate"],
        keep="first",
    )

    bars = bars[
        [
            "secid",
            "tradedate",
            "open",
            "close",
        ]
    ].copy()

    if bars.duplicated(
        ["secid", "tradedate"]
    ).any():
        raise RuntimeError(
            "После выбора board остались дубликаты."
        )

    log(
        f"Selected OHLC rows: {len(bars):,}; "
        f"tickers: {bars['secid'].nunique():,}"
    )

    return bars


# ============================================================
# BUILD MARKET STRUCTURE DESCRIPTORS
# ============================================================

def build_market_structure(
    features: pd.DataFrame,
) -> pd.DataFrame:
    log("Building cross-sectional market structure...")

    # One common cohort per date.
    # All three core primitives and past returns must be present.
    required = CORE + PAST_RETURNS

    frame = features.replace(
        [np.inf, -np.inf],
        np.nan,
    ).dropna(
        subset=required
    ).copy()

    rows = []

    for tradedate, group in frame.groupby(
        "tradedate",
        sort=True,
    ):
        if len(group) < MIN_NAMES:
            continue

        dd = group["drawdown_60"]
        zscore = group["zscore_sma20_20"]
        vol = group["realized_vol_60"]

        row = {
            "tradedate": tradedate,
            "n_names": len(group),

            # Distribution medians: controls, not candidate predictors.
            "median_drawdown_60": dd.median(),
            "median_zscore_sma20_20": zscore.median(),
            "median_realized_vol_60": vol.median(),

            # Price-state breadth.
            "share_dd60_above_m5": (dd > -0.05).mean(),
            "share_dd60_above_m10": (dd > -0.10).mean(),

            # Standardized distance from SMA20.
            "share_zscore_above_0": (zscore > 0).mean(),
            "share_zscore_above_1": (zscore > 1).mean(),

            # Joint price-state coherence.
            "share_joint_near_high_and_above_sma20": (
                (dd > -0.05) & (zscore > 0)
            ).mean(),

            "share_joint_weak_price_state": (
                (dd <= -0.10) & (zscore < 0)
            ).mean(),

            # Cross-sectional dispersion.
            "iqr_drawdown_60": (
                dd.quantile(0.75) - dd.quantile(0.25)
            ),

            "range_drawdown_60_p90_p10": (
                dd.quantile(0.90) - dd.quantile(0.10)
            ),

            "iqr_zscore_sma20_20": (
                zscore.quantile(0.75)
                - zscore.quantile(0.25)
            ),

            "range_zscore_p90_p10": (
                zscore.quantile(0.90)
                - zscore.quantile(0.10)
            ),

            "iqr_realized_vol_60": (
                vol.quantile(0.75) - vol.quantile(0.25)
            ),

            "range_realized_vol_p90_p10": (
                vol.quantile(0.90) - vol.quantile(0.10)
            ),

            # Past market returns of the same signal-date cohort.
            "market_return_5": group["return_5"].mean(),
            "market_return_20": group["return_20"].mean(),
            "market_return_60": group["return_60"].mean(),
        }

        rows.append(row)

    result = pd.DataFrame(rows)

    if result.empty:
        raise RuntimeError(
            "Не удалось построить market structure."
        )

    log(
        f"Market structure dates: {len(result):,}; "
        f"mean cohort size: {result['n_names'].mean():.1f}"
    )

    return result


# ============================================================
# BUILD FORWARD COHORT OUTCOMES
# ============================================================

def build_forward_outcomes(
    structure: pd.DataFrame,
    features: pd.DataFrame,
    bars: pd.DataFrame,
    calendar: list[str],
) -> pd.DataFrame:
    log("Building forward outcomes for signal-date cohorts...")

    # Keep the exact signal-date cohort.
    cohort = features[
        ["secid", "tradedate"]
        + CORE
        + PAST_RETURNS
    ].copy()

    cohort = cohort.replace(
        [np.inf, -np.inf],
        np.nan,
    ).dropna(
        subset=CORE + PAST_RETURNS
    )

    cohort = cohort.merge(
        structure[["tradedate"]],
        on="tradedate",
        how="inner",
        validate="many_to_one",
    )

    date_to_position = {
        date: position
        for position, date in enumerate(calendar)
    }

    cohort["calendar_position"] = (
        cohort["tradedate"].map(date_to_position)
    )

    cohort = cohort.dropna(
        subset=["calendar_position"]
    ).copy()

    cohort["calendar_position"] = (
        cohort["calendar_position"].astype(int)
    )

    bar_open = bars[
        ["secid", "tradedate", "open"]
    ].rename(
        columns={
            "tradedate": "execution_date",
            "open": "execution_open",
        }
    )

    bar_close = bars[
        ["secid", "tradedate", "close"]
    ].rename(
        columns={
            "tradedate": "exit_date",
            "close": "exit_close",
        }
    )

    results = []

    for horizon in HORIZONS:
        temp = cohort[
            ["secid", "tradedate", "calendar_position"]
        ].copy()

        execution_positions = (
            temp["calendar_position"] + 1
        )

        exit_positions = (
            temp["calendar_position"] + horizon
        )

        temp["execution_date"] = (
            execution_positions.map(
                lambda p: (
                    calendar[p]
                    if p < len(calendar)
                    else None
                )
            )
        )

        temp["exit_date"] = (
            exit_positions.map(
                lambda p: (
                    calendar[p]
                    if p < len(calendar)
                    else None
                )
            )
        )

        temp = temp.dropna(
            subset=[
                "execution_date",
                "exit_date",
            ]
        )

        temp = temp.merge(
            bar_open,
            on=["secid", "execution_date"],
            how="left",
            validate="many_to_one",
        )

        temp = temp.merge(
            bar_close,
            on=["secid", "exit_date"],
            how="left",
            validate="many_to_one",
        )

        temp["forward_return"] = (
            temp["exit_close"]
            / temp["execution_open"]
            - 1.0
        )

        temp = temp.replace(
            [np.inf, -np.inf],
            np.nan,
        ).dropna(
            subset=["forward_return"]
        )

        temp["horizon"] = horizon

        results.append(temp)

    ticker_outcomes = pd.concat(
        results,
        ignore_index=True,
    )

    daily_rows = []

    for (tradedate, horizon), group in ticker_outcomes.groupby(
        ["tradedate", "horizon"],
        sort=True,
    ):
        returns = group["forward_return"].dropna()

        if len(returns) < MIN_NAMES:
            continue

        daily_rows.append({
            "tradedate": tradedate,
            "horizon": int(horizon),
            "forward_n": len(returns),
            "mean_return": returns.mean(),
            "median_return": returns.median(),
            "positive_share": (returns > 0).mean(),
        })

    outcomes = pd.DataFrame(daily_rows)

    if outcomes.empty:
        raise RuntimeError(
            "Не удалось построить forward outcomes."
        )

    log(
        f"Daily outcome rows: {len(outcomes):,}; "
        f"dates: {outcomes['tradedate'].nunique():,}"
    )

    return outcomes


# ============================================================
# HAC OLS
# ============================================================

def hac_ols(
    y: np.ndarray,
    x: np.ndarray,
    max_lag: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    OLS with Newey-West HAC covariance.
    Returns coefficients, standard errors, and two-sided
    normal-approximation p-values.
    """
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)

    n, k = x.shape

    if n <= k + 5:
        raise ValueError(
            "Недостаточно наблюдений для HAC OLS."
        )

    xtx_inv = np.linalg.pinv(
        x.T @ x
    )

    beta = xtx_inv @ x.T @ y

    residuals = y - x @ beta

    score = x * residuals[:, None]

    meat = score.T @ score

    lag_count = min(
        max_lag,
        n - 1,
    )

    for lag in range(1, lag_count + 1):
        weight = (
            1.0 - lag / (lag_count + 1.0)
        )

        gamma = (
            score[lag:].T @ score[:-lag]
        )

        meat += weight * (
            gamma + gamma.T
        )

    covariance = (
        xtx_inv
        @ meat
        @ xtx_inv
    )

    # Small-sample correction.
    covariance *= n / max(n - k, 1)

    standard_errors = np.sqrt(
        np.maximum(
            np.diag(covariance),
            0.0,
        )
    )

    t_stats = np.divide(
        beta,
        standard_errors,
        out=np.full_like(beta, np.nan),
        where=standard_errors > 0,
    )

    p_values = np.array([
        math.erfc(abs(value) / math.sqrt(2.0))
        if np.isfinite(value)
        else np.nan
        for value in t_stats
    ])

    return beta, standard_errors, p_values


# ============================================================
# REGRESSION DATASET
# ============================================================

PREDICTORS = [
    "share_dd60_above_m5",
    "share_dd60_above_m10",
    "share_zscore_above_0",
    "share_zscore_above_1",
    "share_joint_near_high_and_above_sma20",
    "share_joint_weak_price_state",
    "iqr_drawdown_60",
    "range_drawdown_60_p90_p10",
    "iqr_zscore_sma20_20",
    "range_zscore_p90_p10",
    "iqr_realized_vol_60",
    "range_realized_vol_p90_p10",
]

OUTCOMES = [
    "mean_return",
    "median_return",
    "positive_share",
]


def run_regressions(
    structure: pd.DataFrame,
    outcomes: pd.DataFrame,
) -> pd.DataFrame:
    log("Running incremental market-structure tests...")

    data = structure.merge(
        outcomes,
        on="tradedate",
        how="inner",
        validate="one_to_many",
    )

    rows = []

    for horizon in HORIZONS:
        horizon_data = data[
            data["horizon"] == horizon
        ].copy()

        for outcome in OUTCOMES:
            for predictor in PREDICTORS:
                for spec_name, controls in CONTROL_SPECS.items():

                    required = [
                        predictor,
                        outcome,
                        *controls,
                    ]

                    sample = horizon_data[
                        required
                    ].replace(
                        [np.inf, -np.inf],
                        np.nan,
                    ).dropna()

                    n = len(sample)

                    if n < 100:
                        continue

                    y = sample[outcome].to_numpy(
                        dtype=float
                    )

                    raw_x = sample[predictor].to_numpy(
                        dtype=float
                    )

                    x_std = np.std(
                        raw_x,
                        ddof=1,
                    )

                    if not np.isfinite(x_std) or x_std <= 0:
                        continue

                    # Standardize predictor and controls.
                    predictor_z = (
                        raw_x - np.mean(raw_x)
                    ) / x_std

                    matrix_columns = [
                        np.ones(n),
                        predictor_z,
                    ]

                    for control in controls:
                        values = sample[control].to_numpy(
                            dtype=float
                        )

                        std = np.std(
                            values,
                            ddof=1,
                        )

                        if not np.isfinite(std) or std <= 0:
                            break

                        matrix_columns.append(
                            (values - np.mean(values)) / std
                        )
                    else:
                        x = np.column_stack(
                            matrix_columns
                        )

                        try:
                            beta, se, p = hac_ols(
                                y,
                                x,
                                max_lag=horizon - 1,
                            )
                        except (ValueError, np.linalg.LinAlgError):
                            continue

                        rows.append({
                            "predictor": predictor,
                            "outcome": outcome,
                            "horizon": horizon,
                            "control_spec": spec_name,
                            "controls": "|".join(controls),
                            "n_dates": n,
                            "predictor_sd": x_std,
                            "beta_per_1sd": beta[1],
                            "hac_se": se[1],
                            "hac_t": (
                                beta[1] / se[1]
                                if se[1] > 0
                                else np.nan
                            ),
                            "hac_p": p[1],
                        })

    result = pd.DataFrame(rows)

    if result.empty:
        raise RuntimeError(
            "Regression results пусты."
        )

    result["hac_q"] = bh_adjust(
        result["hac_p"]
    )

    result["period"] = "full"

    for name, (start, end) in PERIODS.items():
        mask = (
            (result["predictor"].notna())
        )

        # Period-specific regressions are calculated below
        # from the date-level merged dataset, not from this table.

    log(
        f"Regression rows: {len(result):,}; "
        f"dates: {result['n_dates'].max():,} max"
    )

    return result


def run_period_regressions(
    structure: pd.DataFrame,
    outcomes: pd.DataFrame,
) -> pd.DataFrame:
    log("Running subperiod regressions...")

    data = structure.merge(
        outcomes,
        on="tradedate",
        how="inner",
        validate="one_to_many",
    )

    rows = []

    for period_name, (start, end) in PERIODS.items():
        period_data = data[
            (data["tradedate"] >= start)
            & (data["tradedate"] <= end)
        ].copy()

        for horizon in HORIZONS:
            horizon_data = period_data[
                period_data["horizon"] == horizon
            ]

            for outcome in OUTCOMES:
                for predictor in PREDICTORS:
                    for spec_name, controls in CONTROL_SPECS.items():
                        required = [
                            predictor,
                            outcome,
                            *controls,
                        ]

                        sample = horizon_data[
                            required
                        ].replace(
                            [np.inf, -np.inf],
                            np.nan,
                        ).dropna()

                        n = len(sample)

                        if n < 100:
                            continue

                        y = sample[outcome].to_numpy(
                            dtype=float
                        )

                        raw_x = sample[predictor].to_numpy(
                            dtype=float
                        )

                        std_x = np.std(
                            raw_x,
                            ddof=1,
                        )

                        if not np.isfinite(std_x) or std_x <= 0:
                            continue

                        matrix_columns = [
                            np.ones(n),
                            (raw_x - np.mean(raw_x)) / std_x,
                        ]

                        valid = True

                        for control in controls:
                            values = sample[control].to_numpy(
                                dtype=float
                            )

                            std = np.std(
                                values,
                                ddof=1,
                            )

                            if not np.isfinite(std) or std <= 0:
                                valid = False
                                break

                            matrix_columns.append(
                                (values - np.mean(values)) / std
                            )

                        if not valid:
                            continue

                        try:
                            beta, se, p = hac_ols(
                                y,
                                np.column_stack(matrix_columns),
                                max_lag=horizon - 1,
                            )
                        except (ValueError, np.linalg.LinAlgError):
                            continue

                        rows.append({
                            "period": period_name,
                            "predictor": predictor,
                            "outcome": outcome,
                            "horizon": horizon,
                            "control_spec": spec_name,
                            "n_dates": n,
                            "beta_per_1sd": beta[1],
                            "hac_se": se[1],
                            "hac_p": p[1],
                        })

    result = pd.DataFrame(rows)

    if not result.empty:
        result["hac_q"] = bh_adjust(
            result["hac_p"]
        )

    return result


# ============================================================
# REPORT
# ============================================================

def write_report(
    structure: pd.DataFrame,
    outcomes: pd.DataFrame,
    full: pd.DataFrame,
    periods: pd.DataFrame,
) -> None:
    log("Writing report...")

    report = [
        "# Breadth as Market Structure",
        "",
        "## Research question",
        "",
        "Does cross-sectional market coherence or dispersion",
        "contain information beyond past market returns and",
        "the medians of the three selected core primitives?",
        "",
        "## Methodology",
        "",
        "- Signal-date universe: PIT TOP50.",
        "- One common cohort per date with all three core primitives",
        "  and past returns available.",
        "- Forward outcomes use the same signal-date cohort.",
        "- Forward return: Close[T+H] / Open[T+1] - 1.",
        "- No future TOP50 membership is used.",
        "- No price forward-fill.",
        "- Predictor beta is expressed per one standard deviation.",
        "- HAC Newey-West lag = horizon - 1.",
        "- P-values use a two-sided normal approximation.",
        "- BH q-values are calculated across the full regression family.",
        "",
        "## Market structure descriptors",
        "",
        "### Price-state breadth",
        "",
        "- Share with drawdown_60 > -5%.",
        "- Share with drawdown_60 > -10%.",
        "- Share with zscore_sma20_20 > 0.",
        "- Share with zscore_sma20_20 > 1.",
        "- Share simultaneously near highs and above SMA20.",
        "- Share simultaneously in weak price state.",
        "",
        "### Cross-sectional dispersion",
        "",
        "- IQR and P90-P10 range of drawdown_60.",
        "- IQR and P90-P10 range of zscore_sma20_20.",
        "- IQR and P90-P10 range of realized_vol_60.",
        "",
        "## Coverage",
        "",
        f"- Structure dates: {len(structure):,}",
        f"- Outcome rows: {len(outcomes):,}",
        f"- Mean cohort size: {structure['n_names'].mean():.2f}",
        f"- Mean forward coverage: {outcomes['forward_n'].mean():.2f}",
        "",
        "## Full-period incremental regressions",
        "",
    ]

    display = full.sort_values(
        ["control_spec", "outcome", "horizon", "hac_q"]
    )

    report.append(
        display.to_markdown(index=False)
    )

    report += [
        "",
        "## Subperiod regressions",
        "",
    ]

    if not periods.empty:
        report.append(
            periods.sort_values(
                [
                    "period",
                    "control_spec",
                    "outcome",
                    "horizon",
                    "hac_q",
                ]
            ).to_markdown(index=False)
        )

    report += [
        "",
        "## Interpretation guide",
        "",
        "- `past_returns`: tests whether structure adds information",
        "  beyond recent market movement.",
        "- `core_medians`: tests whether structure adds information",
        "  beyond the central state of the three core primitives.",
        "- `combined`: the strictest specification.",
        "- A descriptor significant only against `core_medians` may",
        "  simply be another representation of recent market returns.",
        "- A descriptor that survives `combined` is more interesting,",
        "  but still not proof of causality or strategy profitability.",
        "- A non-significant result does not prove that breadth has",
        "  no descriptive or risk-management role.",
        "- Positive-share is bounded [0, 1]; OLS is diagnostic only.",
        "",
        "## Important limitations",
        "",
        "- Core medians do not capture the entire cross-sectional",
        "  distribution. This experiment explicitly tests some of",
        "  the missing distribution information.",
        "- Threshold shares depend on the chosen thresholds.",
        "- The thresholds are fixed in advance and are not optimized.",
        "- Forward horizons overlap; HAC only partially addresses",
        "  time dependence.",
        "- No transaction costs, slippage, or portfolio simulation.",
        "",
    ]

    path = OUT_DIR / "breadth_market_structure_report.md"

    path.write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    log(f"Report saved: {path}")


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    log("=" * 72)
    log("EXPERIMENT 11: BREADTH AS MARKET STRUCTURE")
    log("=" * 72)

    features = load_features()
    calendar = load_calendar()

    structure = build_market_structure(
        features
    )

    bars = load_adjusted_bars(
        features["secid"].unique().tolist()
    )

    outcomes = build_forward_outcomes(
        structure,
        features,
        bars,
        calendar,
    )

    full = run_regressions(
        structure,
        outcomes,
    )

    periods = run_period_regressions(
        structure,
        outcomes,
    )

    structure.to_csv(
        OUT_DIR / "market_structure_daily.csv",
        index=False,
        encoding="utf-8-sig",
    )

    outcomes.to_csv(
        OUT_DIR / "market_structure_outcomes.csv",
        index=False,
        encoding="utf-8-sig",
    )

    full.to_csv(
        OUT_DIR / "market_structure_incremental_full.csv",
        index=False,
        encoding="utf-8-sig",
    )

    periods.to_csv(
        OUT_DIR / "market_structure_incremental_periods.csv",
        index=False,
        encoding="utf-8-sig",
    )

    metadata = {
        "experiment": 11,
        "core": CORE,
        "past_returns": PAST_RETURNS,
        "predictors": PREDICTORS,
        "outcomes": OUTCOMES,
        "horizons": HORIZONS,
        "control_specs": CONTROL_SPECS,
        "min_names": MIN_NAMES,
        "structure_dates": int(len(structure)),
        "outcome_rows": int(len(outcomes)),
        "mean_cohort_size": float(
            structure["n_names"].mean()
        ),
        "mean_forward_coverage": float(
            outcomes["forward_n"].mean()
        ),
        "method": (
            "PIT TOP50 cross-sectional breadth and dispersion; "
            "time-series HAC OLS with past-return and core-median "
            "controls; same signal-date cohort forward outcomes."
        ),
    }

    (OUT_DIR / "metadata.json").write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    write_report(
        structure,
        outcomes,
        full,
        periods,
    )

    log("=" * 72)
    log("EXPERIMENT 11 COMPLETE")
    log("=" * 72)
    log(f"Output directory: {OUT_DIR}")


if __name__ == "__main__":
    main()
