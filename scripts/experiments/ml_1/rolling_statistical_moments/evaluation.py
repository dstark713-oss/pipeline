# Folder: scripts/experiments/ml_1/rolling_statistical_moments/
# File: evaluation.py
# Purpose: Cross-sectional IC, HAC inference, multiple-testing correction,
#          feature coverage, and within-date redundancy diagnostics.

from __future__ import annotations

import math
from itertools import combinations

import numpy as np
import pandas as pd

from config import (
    HAC_MAX_LAGS,
    MIN_CROSS_SECTION,
    SUBPERIODS,
)


def _safe_corr(x: pd.Series, y: pd.Series, method: str) -> float:
    pair = pd.concat([x, y], axis=1).replace(
        [np.inf, -np.inf], np.nan
    ).dropna()

    if len(pair) < 3:
        return np.nan
    if pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
        return np.nan

    return float(pair.iloc[:, 0].corr(pair.iloc[:, 1], method=method))


def calculate_daily_ic(frame: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    records = []

    for tradedate, group in frame.groupby("tradedate", sort=True):
        for feature in feature_columns:
            pair = group[[feature, "target"]].replace(
                [np.inf, -np.inf], np.nan
            ).dropna()

            n = len(pair)
            if n < MIN_CROSS_SECTION or pair["target"].nunique() < 2:
                continue

            ic = _safe_corr(pair[feature], pair["target"], "pearson")
            rank_ic = _safe_corr(pair[feature], pair["target"], "spearman")

            if not np.isfinite(ic) or not np.isfinite(rank_ic):
                continue

            records.append({
                "tradedate": tradedate,
                "feature": feature,
                "n": n,
                "up_rate": float(pair["target"].mean()),
                "ic": ic,
                "rank_ic": rank_ic,
            })

    if not records:
        raise RuntimeError(
            "No daily IC observations. Check panel coverage and "
            "MIN_CROSS_SECTION."
        )

    return pd.DataFrame(records)


def _normal_two_sided_pvalue(t_stat: float) -> float:
    if not np.isfinite(t_stat):
        return np.nan
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def newey_west_mean_test(values: pd.Series, max_lags: int) -> tuple[float, float]:
    """Newey-West HAC t-statistic for a time-series mean."""
    x = pd.to_numeric(values, errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    ).dropna().to_numpy(dtype=float)

    n = len(x)
    if n < 30:
        return np.nan, np.nan

    mean = float(np.mean(x))
    residual = x - mean
    lag_count = min(max_lags, n - 1)

    long_run_variance = float(np.dot(residual, residual) / n)
    for lag in range(1, lag_count + 1):
        covariance = float(np.dot(residual[lag:], residual[:-lag]) / n)
        weight = 1.0 - lag / (lag_count + 1.0)
        long_run_variance += 2.0 * weight * covariance

    long_run_variance = max(long_run_variance, 0.0)
    standard_error = math.sqrt(long_run_variance / n)

    if standard_error == 0:
        return np.nan, np.nan

    t_stat = mean / standard_error
    return float(t_stat), _normal_two_sided_pvalue(t_stat)


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


def summarize_ic(daily_ic: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for feature, group in daily_ic.groupby("feature", sort=True):
        ic = group["ic"].dropna()
        rank_ic = group["rank_ic"].dropna()

        ic_t, ic_p = newey_west_mean_test(ic, HAC_MAX_LAGS)
        rank_t, rank_p = newey_west_mean_test(rank_ic, HAC_MAX_LAGS)

        row = {
            "feature": feature,
            "n_dates": int(len(group)),
            "mean_n_securities": float(group["n"].mean()),
            "mean_ic": float(ic.mean()),
            "median_ic": float(ic.median()),
            "ic_std": float(ic.std(ddof=1)),
            "positive_ic_share": float((ic > 0).mean()),
            "mean_rank_ic": float(rank_ic.mean()),
            "median_rank_ic": float(rank_ic.median()),
            "rank_ic_std": float(rank_ic.std(ddof=1)),
            "positive_rank_ic_share": float((rank_ic > 0).mean()),
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
    summary["rank_ic_qvalue"] = benjamini_hochberg(
        summary["rank_ic_pvalue"]
    )

    return summary.sort_values(
        ["ic_qvalue", "feature"],
        na_position="last",
    ).reset_index(drop=True)


def calculate_feature_coverage(
    frame: pd.DataFrame,
    feature_columns: list[str],
) -> pd.DataFrame:
    rows = []
    total = len(frame)

    for feature in feature_columns:
        valid = int(frame[feature].notna().sum())
        rows.append({
            "feature": feature,
            "n_total_signal_rows": total,
            "n_valid": valid,
            "n_missing": total - valid,
            "coverage_pct": 100.0 * valid / total if total else np.nan,
        })

    return pd.DataFrame(rows)


def calculate_daily_feature_correlations(
    frame: pd.DataFrame,
    feature_columns: list[str],
) -> pd.DataFrame:
    """Pairwise correlations are calculated cross-sectionally within each date."""
    records = []

    for tradedate, group in frame.groupby("tradedate", sort=True):
        for left, right in combinations(feature_columns, 2):
            pair = group[[left, right]].replace(
                [np.inf, -np.inf], np.nan
            ).dropna()

            if len(pair) < MIN_CROSS_SECTION:
                continue
            if pair[left].nunique() < 2 or pair[right].nunique() < 2:
                continue

            pearson = float(pair[left].corr(pair[right], method="pearson"))
            spearman = float(pair[left].corr(pair[right], method="spearman"))

            if np.isfinite(pearson) and np.isfinite(spearman):
                records.append({
                    "tradedate": tradedate,
                    "feature_a": left,
                    "feature_b": right,
                    "n": len(pair),
                    "pearson": pearson,
                    "spearman": spearman,
                })

    if not records:
        return pd.DataFrame(columns=[
            "feature_a", "feature_b", "n_dates", "median_pearson",
            "median_spearman", "median_abs_pearson",
            "share_abs_pearson_gt_080",
        ])

    daily = pd.DataFrame(records)
    summary = (
        daily.groupby(["feature_a", "feature_b"], as_index=False)
        .agg(
            n_dates=("tradedate", "nunique"),
            median_pearson=("pearson", "median"),
            median_spearman=("spearman", "median"),
            median_abs_pearson=("pearson", lambda x: x.abs().median()),
            share_abs_pearson_gt_080=("pearson", lambda x: (x.abs() > 0.80).mean()),
        )
    )

    return summary.sort_values(
        ["median_abs_pearson", "feature_a", "feature_b"],
        ascending=[False, True, True],
    ).reset_index(drop=True)
