
# Folder: scripts/experiments/primitives/
# File: 09_incremental_breadth.py
# Purpose: Test incremental information in market breadth after controlling
#          for past TOP50 returns and the three selected core primitives.
#
# Inputs:
#   data/interim/primitive_research/primitive_features.parquet
#   data/interim/primitive_research/breadth/breadth_daily.csv
#
# Outputs:
#   data/interim/primitive_research/breadth/incremental_regression.csv
#   data/interim/primitive_research/breadth/incremental_period_stability.csv
#   data/interim/primitive_research/breadth/conditional_spread_bootstrap.csv
#   data/interim/primitive_research/breadth/incremental_breadth_report.md
#   data/interim/primitive_research/breadth/incremental_breadth_metadata.json
#
# Execution:
#   python scripts/experiments/primitives/09_incremental_breadth.py
#
# Methodology:
#   - Time-series OLS coefficient with Newey-West HAC standard errors.
#   - Three control specifications: past returns, core primitives, combined.
#   - Conditional Q5-Q1 spread on residualized breadth and residualized outcome.
#   - Circular moving-block bootstrap to preserve short-range serial dependence.
#   - No trading strategy, no fitted predictive model, no changes to source data.

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

FEATURE_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "primitive_research"
    / "primitive_features.parquet"
)

BREADTH_DAILY_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "primitive_research"
    / "breadth"
    / "breadth_daily.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "primitive_research"
    / "breadth"
)

BREADTH_FEATURES = (
    "breadth_change_5",
    "breadth_change_20",
)

HORIZONS = (5, 10, 20)

OUTCOMES = (
    "mean_return",
    "median_return",
    "positive_share",
)

CORE_FEATURES = (
    "drawdown_60",
    "zscore_sma20_20",
    "realized_vol_60",
)

PAST_RETURN_FEATURES = (
    "cohort_return_5",
    "cohort_return_20",
    "cohort_return_60",
)

CORE_CONTROL_FEATURES = (
    "cohort_median_drawdown_60",
    "cohort_median_zscore_sma20_20",
    "cohort_median_realized_vol_60",
)

CONTROL_SPECS = {
    "past_returns": PAST_RETURN_FEATURES,
    "core_primitives": CORE_CONTROL_FEATURES,
    "combined": PAST_RETURN_FEATURES + CORE_CONTROL_FEATURES,
}

SUBPERIODS = (
    ("2005-2012", "2005-01-01", "2012-12-31"),
    ("2013-2019", "2013-01-01", "2019-12-31"),
    ("2020-2026", "2020-01-01", "2026-12-31"),
)

MIN_COHORT_SIZE = 20

BOOTSTRAP_REPS = 500
BOOTSTRAP_BLOCK_LENGTH = 20
RANDOM_SEED = 7132026

# HAC lag count follows the overlapping forward-return horizon.
MIN_REGRESSION_OBSERVATIONS = 100


# ============================================================
# GENERAL HELPERS
# ============================================================

def log(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def write_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")

    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    temporary.replace(path)


def normal_two_sided_pvalue(t_stat: float) -> float:
    if not np.isfinite(t_stat):
        return np.nan

    return float(
        math.erfc(abs(t_stat) / math.sqrt(2.0))
    )


def benjamini_hochberg(
    pvalues: pd.Series,
) -> pd.Series:
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
    count = len(ordered)

    adjusted = (
        ordered.to_numpy()
        * count
        / np.arange(1, count + 1)
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


def clean_numeric(
    frame: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    result = frame.copy()

    for column in columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    return result.replace(
        [np.inf, -np.inf],
        np.nan,
    )


# ============================================================
# INPUT VALIDATION AND LOADING
# ============================================================

def validate_inputs() -> None:
    if not FEATURE_PATH.is_file():
        raise FileNotFoundError(
            f"Primitive feature frame not found: {FEATURE_PATH}"
        )

    if not BREADTH_DAILY_PATH.is_file():
        raise FileNotFoundError(
            f"Breadth daily data not found: {BREADTH_DAILY_PATH}"
        )


def load_breadth_daily() -> pd.DataFrame:
    log(f"Loading breadth daily data: {BREADTH_DAILY_PATH}")

    daily = pd.read_csv(
        BREADTH_DAILY_PATH,
        parse_dates=["tradedate"],
    )

    required = {
        "tradedate",
        *BREADTH_FEATURES,
    }

    for horizon in HORIZONS:
        required.update({
            f"top50_cohort_forward_mean_return_{horizon}",
            f"top50_cohort_forward_median_return_{horizon}",
            f"top50_cohort_forward_positive_share_{horizon}",
            f"top50_cohort_forward_n_{horizon}",
        })

    missing = required - set(daily.columns)

    if missing:
        raise RuntimeError(
            "breadth_daily.csv is missing columns: "
            f"{sorted(missing)}"
        )

    daily["tradedate"] = pd.to_datetime(
        daily["tradedate"],
        errors="coerce",
    )

    daily = daily.dropna(
        subset=["tradedate"]
    ).copy()

    if daily["tradedate"].duplicated().any():
        raise RuntimeError(
            "Duplicate dates in breadth_daily.csv."
        )

    return daily.sort_values(
        "tradedate"
    ).reset_index(drop=True)



def build_cohort_controls() -> pd.DataFrame:
    log(f"Loading primitive feature frame: {FEATURE_PATH}")

    frame = pd.read_parquet(FEATURE_PATH)

    # primitive_features.parquet already contains only
    # PIT TOP50 rows with an actual signal-date bar.
    # The builder intentionally does not save bar_available.

    required = {
        "tradedate",
        "secid",
        "return_5",
        "return_20",
        "return_60",
        *CORE_FEATURES,
    }

    missing = required - set(frame.columns)

    if missing:
        raise RuntimeError(
            "Primitive feature frame is missing columns: "
            f"{sorted(missing)}"
        )

    frame["tradedate"] = pd.to_datetime(
        frame["tradedate"],
        errors="coerce",
    )

    frame["secid"] = (
        frame["secid"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    frame = frame.dropna(
        subset=["tradedate", "secid"]
    ).copy()

    numeric_columns = [
        "return_5",
        "return_20",
        "return_60",
        *CORE_FEATURES,
    ]

    frame = clean_numeric(
        frame,
        numeric_columns,
    )

    aggregations = {
        "cohort_return_5": ("return_5", "mean"),
        "cohort_return_20": ("return_20", "mean"),
        "cohort_return_60": ("return_60", "mean"),
        "cohort_median_drawdown_60": (
            "drawdown_60", "median"
        ),
        "cohort_median_zscore_sma20_20": (
            "zscore_sma20_20", "median"
        ),
        "cohort_median_realized_vol_60": (
            "realized_vol_60", "median"
        ),
    }

    grouped = frame.groupby(
        "tradedate",
        sort=True,
    )

    result = grouped.agg(
        **aggregations,
        cohort_size=("secid", "nunique"),
        n_return_5=("return_5", "count"),
        n_return_20=("return_20", "count"),
        n_return_60=("return_60", "count"),
        n_drawdown_60=("drawdown_60", "count"),
        n_zscore_sma20_20=("zscore_sma20_20", "count"),
        n_realized_vol_60=("realized_vol_60", "count"),
    ).reset_index()

    count_map = {
        "cohort_return_5": "n_return_5",
        "cohort_return_20": "n_return_20",
        "cohort_return_60": "n_return_60",
        "cohort_median_drawdown_60": "n_drawdown_60",
        "cohort_median_zscore_sma20_20": "n_zscore_sma20_20",
        "cohort_median_realized_vol_60": "n_realized_vol_60",
    }

    for value_column, count_column in count_map.items():
        result.loc[
            result[count_column] < MIN_COHORT_SIZE,
            value_column,
        ] = np.nan

    log(
        f"Built cohort controls for "
        f"{len(result):,} dates."
    )

    return result



def build_analysis_frame() -> pd.DataFrame:
    daily = load_breadth_daily()
    controls = build_cohort_controls()

    frame = daily.merge(
        controls,
        on="tradedate",
        how="left",
        validate="one_to_one",
    )

    frame = frame.sort_values(
        "tradedate"
    ).reset_index(drop=True)

    log(
        f"Combined daily rows: {len(frame):,}; "
        f"date range: {frame['tradedate'].min()} — "
        f"{frame['tradedate'].max()}"
    )

    return frame


# ============================================================
# REGRESSION AND RESIDUALIZATION
# ============================================================

def residualize(
    values: np.ndarray,
    controls: np.ndarray,
) -> np.ndarray:
    """
    Remove the linear component explained by controls.
    An intercept is always included.
    """
    values = np.asarray(
        values,
        dtype=float,
    )

    if controls.size == 0:
        return values - np.mean(values)

    design = np.column_stack([
        np.ones(len(values)),
        controls,
    ])

    coefficients = np.linalg.lstsq(
        design,
        values,
        rcond=None,
    )[0]

    return values - design @ coefficients


def fit_hac_ols(
    y: np.ndarray,
    x: np.ndarray,
    controls: np.ndarray,
    max_lags: int,
) -> dict:
    """
    OLS:
        y = intercept + controls + breadth

    Newey-West HAC covariance with Bartlett weights.
    Returns the breadth coefficient and its HAC inference.
    """
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)

    columns = [
        np.ones(len(y))
    ]

    if controls.size:
        columns.extend(
            controls[:, index]
            for index in range(controls.shape[1])
        )

    columns.append(x)

    design = np.column_stack(columns)

    n, k = design.shape

    if n < MIN_REGRESSION_OBSERVATIONS:
        return {
            "coefficient": np.nan,
            "hac_se": np.nan,
            "hac_t": np.nan,
            "pvalue": np.nan,
            "standardized_beta": np.nan,
            "residual_correlation": np.nan,
            "rank": int(np.linalg.matrix_rank(design)),
        }

    rank = int(np.linalg.matrix_rank(design))

    if rank < k:
        return {
            "coefficient": np.nan,
            "hac_se": np.nan,
            "hac_t": np.nan,
            "pvalue": np.nan,
            "standardized_beta": np.nan,
            "residual_correlation": np.nan,
            "rank": rank,
        }

    coefficients = np.linalg.lstsq(
        design,
        y,
        rcond=None,
    )[0]

    residuals = y - design @ coefficients

    bread = np.linalg.inv(
        design.T @ design
    )

    scores = design * residuals[:, None]

    meat = scores.T @ scores

    lag_count = min(
        max_lags,
        n - 1,
    )

    for lag in range(1, lag_count + 1):
        weight = (
            1.0 - lag / (lag_count + 1.0)
        )

        cross = (
            scores[lag:].T
            @ scores[:-lag]
        )

        meat += weight * (
            cross + cross.T
        )

    covariance = (
        bread
        @ meat
        @ bread
    )

    # Small-sample degrees-of-freedom correction.
    covariance *= n / (n - k)

    coefficient = float(
        coefficients[-1]
    )

    variance = float(
        covariance[-1, -1]
    )

    standard_error = (
        math.sqrt(variance)
        if variance > 0
        else np.nan
    )

    t_stat = (
        coefficient / standard_error
        if np.isfinite(standard_error)
        and standard_error > 0
        else np.nan
    )

    pvalue = normal_two_sided_pvalue(
        t_stat
    )

    x_residual = residualize(
        x,
        controls,
    )

    y_residual = residualize(
        y,
        controls,
    )

    residual_correlation = (
        float(np.corrcoef(
            x_residual,
            y_residual,
        )[0, 1])
        if np.std(x_residual) > 0
        and np.std(y_residual) > 0
        else np.nan
    )

    y_std = float(np.std(y, ddof=0))
    x_std = float(np.std(x, ddof=0))

    standardized_beta = (
        coefficient * x_std / y_std
        if y_std > 0
        else np.nan
    )

    return {
        "coefficient": coefficient,
        "hac_se": standard_error,
        "hac_t": t_stat,
        "pvalue": pvalue,
        "standardized_beta": standardized_beta,
        "residual_correlation": residual_correlation,
        "rank": rank,
    }


# ============================================================
# CONDITIONAL Q5-Q1 SPREAD
# ============================================================

def circular_block_indices(
    n: int,
    block_length: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Generate one circular moving-block bootstrap sample.
    Blocks retain the order of adjacent market sessions.
    """
    blocks_needed = int(
        math.ceil(n / block_length)
    )

    starts = rng.integers(
        0,
        n,
        size=blocks_needed,
    )

    offsets = np.arange(
        block_length
    )

    indices = np.concatenate([
        (start + offsets) % n
        for start in starts
    ])

    return indices[:n]


def conditional_spread_bootstrap(
    x_residual: np.ndarray,
    y_residual: np.ndarray,
    rng: np.random.Generator,
) -> dict:
    """
    Q5-Q1 spread:
      - Q1/Q5 are based on residualized breadth.
      - Outcome is also residualized against the same controls.
      - Bootstrap resamples contiguous blocks of sessions.
      - Original Q1/Q5 thresholds are held fixed in bootstrap samples.
    """
    x_residual = np.asarray(
        x_residual,
        dtype=float,
    )

    y_residual = np.asarray(
        y_residual,
        dtype=float,
    )

    if len(x_residual) < 100:
        return {
            "spread": np.nan,
            "ci_2_5": np.nan,
            "ci_97_5": np.nan,
            "bootstrap_pvalue": np.nan,
            "bootstrap_reps": 0,
            "q1_n": 0,
            "q5_n": 0,
        }

    q20, q80 = np.quantile(
        x_residual,
        [0.20, 0.80],
    )

    low_mask = x_residual <= q20
    high_mask = x_residual >= q80

    if (
        low_mask.sum() < 20
        or high_mask.sum() < 20
    ):
        return {
            "spread": np.nan,
            "ci_2_5": np.nan,
            "ci_97_5": np.nan,
            "bootstrap_pvalue": np.nan,
            "bootstrap_reps": 0,
            "q1_n": int(low_mask.sum()),
            "q5_n": int(high_mask.sum()),
        }

    observed = float(
        y_residual[high_mask].mean()
        - y_residual[low_mask].mean()
    )

    bootstrap_values = np.empty(
        BOOTSTRAP_REPS,
        dtype=float,
    )

    n = len(x_residual)

    for iteration in range(BOOTSTRAP_REPS):
        indices = circular_block_indices(
            n,
            BOOTSTRAP_BLOCK_LENGTH,
            rng,
        )

        sampled_y = y_residual[indices]
        sampled_low = low_mask[indices]
        sampled_high = high_mask[indices]

        low_n = int(sampled_low.sum())
        high_n = int(sampled_high.sum())

        if low_n == 0 or high_n == 0:
            bootstrap_values[iteration] = np.nan
            continue

        bootstrap_values[iteration] = (
            sampled_y[sampled_high].mean()
            - sampled_y[sampled_low].mean()
        )

    bootstrap_values = bootstrap_values[
        np.isfinite(bootstrap_values)
    ]

    if len(bootstrap_values) < BOOTSTRAP_REPS * 0.8:
        return {
            "spread": observed,
            "ci_2_5": np.nan,
            "ci_97_5": np.nan,
            "bootstrap_pvalue": np.nan,
            "bootstrap_reps": int(len(bootstrap_values)),
            "q1_n": int(low_mask.sum()),
            "q5_n": int(high_mask.sum()),
        }

    lower, upper = np.quantile(
        bootstrap_values,
        [0.025, 0.975],
    )

    p_lower = (
        np.sum(bootstrap_values <= 0) + 1
    ) / (
        len(bootstrap_values) + 1
    )

    p_upper = (
        np.sum(bootstrap_values >= 0) + 1
    ) / (
        len(bootstrap_values) + 1
    )

    bootstrap_pvalue = min(
        1.0,
        2.0 * min(p_lower, p_upper),
    )

    return {
        "spread": observed,
        "ci_2_5": float(lower),
        "ci_97_5": float(upper),
        "bootstrap_pvalue": float(bootstrap_pvalue),
        "bootstrap_reps": int(len(bootstrap_values)),
        "q1_n": int(low_mask.sum()),
        "q5_n": int(high_mask.sum()),
    }


# ============================================================
# BUILD MODEL SAMPLES
# ============================================================

def target_column(
    outcome: str,
    horizon: int,
) -> str:
    return (
        f"top50_cohort_forward_{outcome}_{horizon}"
    )


def coverage_column(
    horizon: int,
) -> str:
    return (
        f"top50_cohort_forward_n_{horizon}"
    )


def prepare_sample(
    frame: pd.DataFrame,
    feature: str,
    outcome: str,
    horizon: int,
    controls: tuple[str, ...],
) -> pd.DataFrame:
    target = target_column(
        outcome,
        horizon,
    )

    count = coverage_column(
        horizon
    )

    columns = [
        "tradedate",
        feature,
        target,
        count,
        *controls,
    ]

    sample = frame[columns].copy()

    sample = clean_numeric(
        sample,
        columns[1:],
    )

    sample = sample.dropna(
        subset=[
            feature,
            target,
            *controls,
        ]
    )

    sample = sample[
        sample[count] >= MIN_COHORT_SIZE
    ]

    return sample.sort_values(
        "tradedate"
    ).reset_index(drop=True)


def extract_arrays(
    sample: pd.DataFrame,
    feature: str,
    outcome: str,
    horizon: int,
    controls: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    y = sample[
        target_column(outcome, horizon)
    ].to_numpy(dtype=float)

    x = sample[
        feature
    ].to_numpy(dtype=float)

    if controls:
        control_matrix = sample[
            list(controls)
        ].to_numpy(dtype=float)
    else:
        control_matrix = np.empty(
            (len(sample), 0),
            dtype=float,
        )

    # Drop zero-variance controls to avoid rank deficiency.
    if control_matrix.size:
        keep = (
            np.nanstd(
                control_matrix,
                axis=0,
            ) > 1e-12
        )

        control_matrix = control_matrix[:, keep]

    return y, x, control_matrix


# ============================================================
# MAIN ANALYSIS
# ============================================================

def run_regression_analysis(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(
        RANDOM_SEED
    )

    regression_rows = []
    period_rows = []
    bootstrap_rows = []

    total = (
        len(BREADTH_FEATURES)
        * len(CONTROL_SPECS)
        * len(OUTCOMES)
        * len(HORIZONS)
    )

    current = 0

    for feature in BREADTH_FEATURES:
        for spec_name, controls in CONTROL_SPECS.items():
            for outcome in OUTCOMES:
                for horizon in HORIZONS:
                    current += 1

                    log(
                        f"Analysis {current}/{total}: "
                        f"{feature} | {spec_name} | "
                        f"{outcome} | H{horizon}"
                    )

                    sample = prepare_sample(
                        frame,
                        feature,
                        outcome,
                        horizon,
                        controls,
                    )

                    y, x, control_matrix = extract_arrays(
                        sample,
                        feature,
                        outcome,
                        horizon,
                        controls,
                    )

                    max_lags = min(
                        horizon - 1,
                        19,
                    )

                    fit = fit_hac_ols(
                        y,
                        x,
                        control_matrix,
                        max_lags,
                    )

                    regression_rows.append({
                        "breadth_feature": feature,
                        "control_spec": spec_name,
                        "outcome": outcome,
                        "horizon": horizon,
                        "n_dates": int(len(sample)),
                        "n_controls": int(control_matrix.shape[1]),
                        "hac_max_lags": max_lags,
                        **fit,
                    })

                    # Period stability uses exactly the same model
                    # and control specification in each subperiod.
                    for period_name, start, end in SUBPERIODS:
                        period_sample = sample[
                            sample["tradedate"].between(
                                pd.Timestamp(start),
                                pd.Timestamp(end),
                            )
                        ].reset_index(drop=True)

                        py, px, pc = extract_arrays(
                            period_sample,
                            feature,
                            outcome,
                            horizon,
                            controls,
                        )

                        period_fit = fit_hac_ols(
                            py,
                            px,
                            pc,
                            max_lags,
                        )

                        period_rows.append({
                            "breadth_feature": feature,
                            "control_spec": spec_name,
                            "outcome": outcome,
                            "horizon": horizon,
                            "period": period_name,
                            "n_dates": int(len(period_sample)),
                            "n_controls": int(pc.shape[1]),
                            **period_fit,
                        })

                    # Conditional Q5-Q1 spread:
                    # residualize breadth and outcome on the same controls.
                    if len(sample) >= MIN_REGRESSION_OBSERVATIONS:
                        x_residual = residualize(
                            x,
                            control_matrix,
                        )

                        y_residual = residualize(
                            y,
                            control_matrix,
                        )

                        spread = conditional_spread_bootstrap(
                            x_residual,
                            y_residual,
                            rng,
                        )
                    else:
                        spread = {
                            "spread": np.nan,
                            "ci_2_5": np.nan,
                            "ci_97_5": np.nan,
                            "bootstrap_pvalue": np.nan,
                            "bootstrap_reps": 0,
                            "q1_n": 0,
                            "q5_n": 0,
                        }

                    bootstrap_rows.append({
                        "breadth_feature": feature,
                        "control_spec": spec_name,
                        "outcome": outcome,
                        "horizon": horizon,
                        "n_dates": int(len(sample)),
                        "block_length": BOOTSTRAP_BLOCK_LENGTH,
                        **spread,
                    })

    regression = pd.DataFrame(
        regression_rows
    )

    periods = pd.DataFrame(
        period_rows
    )

    bootstrap = pd.DataFrame(
        bootstrap_rows
    )

    # Correct for the full family of incremental tests.
    regression["hac_qvalue"] = benjamini_hochberg(
        regression["pvalue"]
    )

    bootstrap["bootstrap_qvalue"] = benjamini_hochberg(
        bootstrap["bootstrap_pvalue"]
    )

    return regression, periods, bootstrap


# ============================================================
# REPORT
# ============================================================

def format_table(
    frame: pd.DataFrame,
    columns: list[str],
    limit: int = 100,
) -> str:
    if frame.empty:
        return "_Нет доступных наблюдений._"

    available = [
        column
        for column in columns
        if column in frame.columns
    ]

    return frame[available].head(limit).to_string(
        index=False,
        float_format=lambda value: f"{value:.5f}",
    )


def write_report(
    frame: pd.DataFrame,
    regression: pd.DataFrame,
    periods: pd.DataFrame,
    bootstrap: pd.DataFrame,
) -> None:
    lines = [
        "# Incremental Market Breadth Research",
        "",
        f"- Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"- Dates: {frame['tradedate'].min()} — {frame['tradedate'].max()}",
        f"- Daily observations: {len(frame):,}",
        "- Signal-date universe: PIT TOP50 cohort.",
        "- Forward outcomes retain the signal-date cohort.",
        "- Forward return: close[T+H] / open[T+1] - 1.",
        "- Breadth candidates: breadth_change_5 and breadth_change_20.",
        "",
        "## Methodology",
        "",
        "- OLS coefficient of breadth with Newey-West HAC standard errors.",
        "- Three control specifications: past returns, core primitives, combined.",
        "- Past-return controls: mean cohort return_5, return_20, return_60.",
        "- Core controls: median drawdown_60, zscore_sma20_20, realized_vol_60.",
        "- Conditional Q5-Q1 compares residualized outcomes across residualized breadth buckets.",
        f"- Circular moving-block bootstrap: {BOOTSTRAP_REPS} replications, block length {BOOTSTRAP_BLOCK_LENGTH}.",
        "- HAC lag count: horizon minus one.",
        "- BH q-values are calculated across the full test family.",
        "- This is a conditional association test, not a predictive model or strategy backtest.",
        "",
        "## Incremental regression: full sample",
        "",
        format_table(
            regression.sort_values(
                ["control_spec", "outcome", "horizon", "hac_qvalue"],
                na_position="last",
            ),
            [
                "breadth_feature",
                "control_spec",
                "outcome",
                "horizon",
                "n_dates",
                "standardized_beta",
                "residual_correlation",
                "hac_t",
                "pvalue",
                "hac_qvalue",
            ],
            200,
        ),
        "",
        "## Period stability",
        "",
        format_table(
            periods.sort_values(
                [
                    "breadth_feature",
                    "control_spec",
                    "outcome",
                    "horizon",
                    "period",
                ]
            ),
            [
                "breadth_feature",
                "control_spec",
                "outcome",
                "horizon",
                "period",
                "n_dates",
                "standardized_beta",
                "residual_correlation",
                "hac_t",
                "pvalue",
            ],
            300,
        ),
        "",
        "## Conditional Q5-Q1 block bootstrap",
        "",
        format_table(
            bootstrap.sort_values(
                [
                    "control_spec",
                    "outcome",
                    "horizon",
                    "bootstrap_qvalue",
                ],
                na_position="last",
            ),
            [
                "breadth_feature",
                "control_spec",
                "outcome",
                "horizon",
                "n_dates",
                "spread",
                "ci_2_5",
                "ci_97_5",
                "bootstrap_pvalue",
                "bootstrap_qvalue",
                "bootstrap_reps",
            ],
            200,
        ),
        "",
        "## Interpretation",
        "",
        "- Positive standardized_beta means stronger breadth is associated with a higher future outcome after controls.",
        "- Positive conditional Q5-Q1 means high residualized breadth has a higher residualized outcome than low residualized breadth.",
        "- A result that disappears after past-return controls is likely redundant with recent market movement.",
        "- A result that survives past returns but disappears after core controls may overlap with the selected price-state primitives.",
        "- A result that survives combined controls and remains directionally stable across periods is stronger evidence of incremental information.",
        "- The core realized_vol_60 primitive is a risk descriptor; its inclusion here is a control for market risk state, not a claim that it predicts return.",
        "- Bootstrap intervals are conditional on the original residualized-breadth quintile thresholds.",
        "- Results remain historical associations. They do not establish causality or profitability.",
        "",
    ]

    report_path = (
        OUTPUT_DIR
        / "incremental_breadth_report.md"
    )

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


# ============================================================
# ENTRY POINT
# ============================================================

def main() -> None:
    validate_inputs()
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    frame = build_analysis_frame()

    log("Starting incremental breadth analysis...")

    regression, periods, bootstrap = run_regression_analysis(
        frame
    )

    regression_path = (
        OUTPUT_DIR
        / "incremental_regression.csv"
    )

    periods_path = (
        OUTPUT_DIR
        / "incremental_period_stability.csv"
    )

    bootstrap_path = (
        OUTPUT_DIR
        / "conditional_spread_bootstrap.csv"
    )

    regression.to_csv(
        regression_path,
        index=False,
        encoding="utf-8-sig",
    )

    periods.to_csv(
        periods_path,
        index=False,
        encoding="utf-8-sig",
    )

    bootstrap.to_csv(
        bootstrap_path,
        index=False,
        encoding="utf-8-sig",
    )

    write_report(
        frame,
        regression,
        periods,
        bootstrap,
    )

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": str(PROJECT_ROOT),
        "feature_path": str(FEATURE_PATH),
        "breadth_daily_path": str(BREADTH_DAILY_PATH),
        "output_dir": str(OUTPUT_DIR),
        "date_start": str(frame["tradedate"].min()),
        "date_end": str(frame["tradedate"].max()),
        "daily_rows": int(len(frame)),
        "breadth_features": list(BREADTH_FEATURES),
        "outcomes": list(OUTCOMES),
        "horizons": list(HORIZONS),
        "control_specs": {
            key: list(value)
            for key, value in CONTROL_SPECS.items()
        },
        "subperiods": [
            {
                "name": name,
                "start": start,
                "end": end,
            }
            for name, start, end in SUBPERIODS
        ],
        "hac_method": "Newey-West Bartlett kernel",
        "hac_lags": "horizon - 1",
        "bootstrap_method": "circular moving-block bootstrap",
        "bootstrap_reps": BOOTSTRAP_REPS,
        "bootstrap_block_length": BOOTSTRAP_BLOCK_LENGTH,
        "random_seed": RANDOM_SEED,
        "minimum_cohort_size": MIN_COHORT_SIZE,
        "no_forward_fill": True,
        "no_source_data_mutation": True,
        "no_strategy_backtest": True,
    }

    write_json(
        OUTPUT_DIR / "incremental_breadth_metadata.json",
        metadata,
    )

    log("=" * 68)
    log("INCREMENTAL BREADTH RESEARCH COMPLETE")
    log(f"Output directory: {OUTPUT_DIR}")
    log(f"Report: {OUTPUT_DIR / 'incremental_breadth_report.md'}")
    log("=" * 68)


if __name__ == "__main__":
    main()
