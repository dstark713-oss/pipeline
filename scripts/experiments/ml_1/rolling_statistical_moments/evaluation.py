# Folder: scripts/experiments/ml_1/rolling_statistical_moments/
# File: evaluation.py
# Purpose: Cross-sectional IC, missingness diagnostics, HAC inference,
#          multiple-testing correction, coverage, and redundancy diagnostics.

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from config import MIN_CROSS_SECTION, SUBPERIODS
from hac_calendar import calendar_aware_hac, equal_spacing_hac


def _safe_corr(x: pd.Series, y: pd.Series, method: str) -> float:
    pair = pd.concat([x, y], axis=1).replace(
        [np.inf, -np.inf], np.nan
    ).dropna()
    if len(pair) < 3:
        return np.nan
    if pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
        return np.nan
    return float(pair.iloc[:, 0].corr(pair.iloc[:, 1], method=method))


def calculate_daily_ic(
    frame: pd.DataFrame,
    feature_columns: list[str],
    calendar: pd.Index,
) -> pd.DataFrame:
    """Return a complete calendar x feature grid, retaining missing IC dates."""
    calendar = pd.DatetimeIndex(calendar).sort_values()
    groups = {date: group for date, group in frame.groupby("tradedate", sort=False)}
    records = []

    for tradedate in calendar:
        group = groups.get(tradedate)
        for feature in feature_columns:
            if group is None or group.empty:
                records.append({
                    "tradedate": tradedate, "feature": feature,
                    "n": 0, "up_rate": np.nan, "ic": np.nan,
                    "rank_ic": np.nan, "missing_reason": "no_signal_rows",
                })
                continue

            pair = group[[feature, "target"]].replace(
                [np.inf, -np.inf], np.nan
            ).dropna()
            n = len(pair)
            up_rate = float(pair["target"].mean()) if n else np.nan
            reason = None
            ic = rank_ic = np.nan

            if n == 0:
                reason = "no_valid_feature_target_pairs"
            elif n < MIN_CROSS_SECTION:
                reason = "insufficient_cross_section"
            elif pair["target"].nunique() < 2:
                reason = "single_target_class"
            else:
                ic = _safe_corr(pair[feature], pair["target"], "pearson")
                rank_ic = _safe_corr(pair[feature], pair["target"], "spearman")
                if not np.isfinite(ic) or not np.isfinite(rank_ic):
                    reason = "undefined_correlation"

            records.append({
                "tradedate": tradedate,
                "feature": feature,
                "n": n,
                "up_rate": up_rate,
                "ic": ic,
                "rank_ic": rank_ic,
                "missing_reason": reason,
            })

    return pd.DataFrame(records)


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
    """Descriptive IC statistics only. Inferential results live in hac_inference.csv."""
    rows = []
    for feature, group in daily_ic.groupby("feature", sort=True):
        ic = pd.to_numeric(group["ic"], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        ).dropna()
        rank_ic = pd.to_numeric(group["rank_ic"], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        ).dropna()
        row = {
            "feature": feature,
            "n_calendar_sessions": int(len(group)),
            "n_valid_ic": int(ic.size),
            "n_valid_rank_ic": int(rank_ic.size),
            "mean_n_securities": float(group.loc[group["ic"].notna(), "n"].mean()),
            "mean_ic": float(ic.mean()),
            "median_ic": float(ic.median()),
            "ic_std": float(ic.std(ddof=1)),
            "positive_ic_share": float((ic > 0).mean()),
            "mean_rank_ic": float(rank_ic.mean()),
            "median_rank_ic": float(rank_ic.median()),
            "rank_ic_std": float(rank_ic.std(ddof=1)),
            "positive_rank_ic_share": float((rank_ic > 0).mean()),
            "missing_ic_share": float(1.0 - ic.size / len(group)) if len(group) else np.nan,
        }
        for label, start, end in SUBPERIODS:
            period = group[
                (group["tradedate"] >= pd.Timestamp(start))
                & (group["tradedate"] <= pd.Timestamp(end))
            ]
            row[f"mean_ic_{label}"] = float(period["ic"].mean())
            row[f"mean_rank_ic_{label}"] = float(period["rank_ic"].mean())
            row[f"n_valid_ic_{label}"] = int(period["ic"].notna().sum())
        rows.append(row)
    return pd.DataFrame(rows)


def build_hac_inference(
    daily_ic: pd.DataFrame,
    calendar: pd.Index,
    bandwidths: tuple[int, ...] = (4, 10, 20, 60),
    min_observations: int = 30,
) -> pd.DataFrame:
    """Run AM and ES for Pearson/Rank IC; BH is applied across features per specification."""
    rows = []
    for feature, group in daily_ic.groupby("feature", sort=True):
        indexed = group.set_index("tradedate")
        for metric in ("ic", "rank_ic"):
            series = indexed[metric].reindex(calendar)
            finite_n = int(np.isfinite(
                pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
            ).sum())
            for method, estimator in (
                ("AM", calendar_aware_hac),
                ("ES", equal_spacing_hac),
            ):
                for bandwidth in bandwidths:
                    if finite_n < min_observations:
                        rows.append({
                            "feature": feature, "metric": metric,
                            "estimator": method, "bandwidth": bandwidth,
                            "n_observations": finite_n, "n_sessions": len(calendar),
                            "mean": float(series.mean()), "long_run_variance": np.nan,
                            "variance_of_mean": np.nan, "std_error": np.nan,
                            "t_stat": np.nan, "p_value": np.nan,
                            "status": "insufficient_observations",
                        })
                        continue
                    try:
                        result = estimator(series, calendar, bandwidth)
                        rows.append({
                            "feature": feature, "metric": metric,
                            "estimator": method, "bandwidth": bandwidth,
                            "n_observations": result.n_observations,
                            "n_sessions": result.n_sessions,
                            "mean": result.mean,
                            "long_run_variance": result.long_run_variance,
                            "variance_of_mean": result.variance,
                            "std_error": result.std_error,
                            "t_stat": result.t_stat, "p_value": result.p_value,
                            "status": "ok",
                        })
                    except (ValueError, TypeError, FloatingPointError) as exc:
                        rows.append({
                            "feature": feature, "metric": metric,
                            "estimator": method, "bandwidth": bandwidth,
                            "n_observations": finite_n, "n_sessions": len(calendar),
                            "mean": float(series.mean()), "long_run_variance": np.nan,
                            "variance_of_mean": np.nan, "std_error": np.nan,
                            "t_stat": np.nan, "p_value": np.nan,
                            "status": f"error:{type(exc).__name__}",
                        })

    result = pd.DataFrame(rows)
    result["q_value"] = np.nan
    for _, indices in result.groupby(
        ["metric", "estimator", "bandwidth"], sort=False
    ).groups.items():
        result.loc[indices, "q_value"] = benjamini_hochberg(
            result.loc[indices, "p_value"]
        )
    return result


def summarize_missingness(daily_ic: pd.DataFrame) -> pd.DataFrame:
    counts = (
        daily_ic.assign(
            is_valid=daily_ic["ic"].notna() & daily_ic["rank_ic"].notna()
        )
        .groupby(["feature", "missing_reason"], dropna=False)
        .agg(n_sessions=("tradedate", "nunique"), mean_cross_section=("n", "mean"))
        .reset_index()
    )
    return counts


def calculate_feature_coverage(
    frame: pd.DataFrame,
    feature_columns: list[str],
) -> pd.DataFrame:
    rows = []
    total = len(frame)
    for feature in feature_columns:
        valid = int(np.isfinite(
            pd.to_numeric(frame[feature], errors="coerce").to_numpy(dtype=float)
        ).sum())
        rows.append({
            "feature": feature, "n_total_signal_rows": total,
            "n_valid": valid, "n_missing": total - valid,
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
                    "tradedate": tradedate, "feature_a": left,
                    "feature_b": right, "n": len(pair),
                    "pearson": pearson, "spearman": spearman,
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
