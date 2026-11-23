# Folder: scripts/experiments/primitives/breadth/
# File: breadth_statistics.py
# Purpose: Time-series statistics for breadth research. No regression models.

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def safe_corr(x: pd.Series, y: pd.Series, method: str = "pearson") -> float:
    pair = pd.concat([x, y], axis=1).replace(
        [np.inf, -np.inf], np.nan
    ).dropna()
    if len(pair) < 3:
        return np.nan
    if pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
        return np.nan
    return float(pair.iloc[:, 0].corr(pair.iloc[:, 1], method=method))


def normal_two_sided_pvalue(t_stat: float) -> float:
    if not np.isfinite(t_stat):
        return np.nan
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def newey_west_mean_test(values: pd.Series, max_lags: int) -> tuple[float, float]:
    """Newey-West HAC test of a time-series mean with Bartlett weights."""
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
    if standard_error <= 0:
        return np.nan, np.nan

    t_stat = mean / standard_error
    return float(t_stat), normal_two_sided_pvalue(t_stat)


def hac_correlation_test(
    x: pd.Series,
    y: pd.Series,
    method: str,
    max_lags: int,
) -> tuple[float, float]:
    """HAC test for correlation, using ranked observations for Spearman."""
    pair = pd.concat([x, y], axis=1).replace(
        [np.inf, -np.inf], np.nan
    ).dropna()

    if len(pair) < 30:
        return np.nan, np.nan

    left = pair.iloc[:, 0]
    right = pair.iloc[:, 1]
    if method == "spearman":
        left = left.rank(method="average")
        right = right.rank(method="average")

    left_std = left.std(ddof=0)
    right_std = right.std(ddof=0)
    if left_std <= 0 or right_std <= 0:
        return np.nan, np.nan

    cross_product = (
        (left - left.mean()) / left_std
    ) * (
        (right - right.mean()) / right_std
    )
    return newey_west_mean_test(cross_product, max_lags)


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


def quantile_labels(values: pd.Series, q: int) -> pd.Series:
    """Return zero-based quantile labels; duplicate edges reduce bucket count."""
    numeric = pd.to_numeric(values, errors="coerce")
    result = pd.Series(np.nan, index=values.index, dtype=float)
    valid = numeric.replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) < q * 5 or valid.nunique() < 2:
        return result
    try:
        labels = pd.qcut(valid, q=q, labels=False, duplicates="drop")
    except ValueError:
        return result
    result.loc[labels.index] = labels.astype(float)
    return result
