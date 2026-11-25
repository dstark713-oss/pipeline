# Path: scripts/experiments/ml_1/eda/analysis.py
# Purpose: Descriptive statistics, temporal structure, consistency and future-price EDA.
"""Descriptive EDA analysis functions."""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import HORIZONS, MARKET_VARIABLES, MEMBERSHIP_VARIABLES


def describe(series: pd.Series) -> dict:
    x = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if x.empty:
        return {"n": 0}
    q = x.quantile([0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99])
    return {
        "n": int(x.size), "mean": float(x.mean()), "std": float(x.std()),
        "min": float(x.min()), "p01": float(q.loc[0.01]),
        "p05": float(q.loc[0.05]), "p25": float(q.loc[0.25]),
        "median": float(q.loc[0.50]), "p75": float(q.loc[0.75]),
        "p95": float(q.loc[0.95]), "p99": float(q.loc[0.99]),
        "max": float(x.max()), "skew": float(x.skew()),
        "excess_kurtosis": float(x.kurt()),
    }


def _year(frame: pd.DataFrame) -> pd.Series:
    return frame["tradedate"].dt.year.astype(int)


def distribution_analysis(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    available = panel[panel["bar_available"].eq(1)].copy()
    rows = []
    yearly_rows = []
    for column in (*MARKET_VARIABLES, *MEMBERSHIP_VARIABLES):
        source = available if column in MARKET_VARIABLES else panel
        stats = describe(source[column])
        rows.append({"variable": column, "sample": "overall", **stats})
        temp = source[["tradedate", column]].copy()
        temp["year"] = _year(temp)
        for year, group in temp.groupby("year", sort=True):
            yearly_rows.append({
                "variable": column, "year": int(year), **describe(group[column])
            })

    per_secid = []
    for secid, group in panel.groupby("secid", sort=True):
        valid = group[group["bar_available"].eq(1)]
        per_secid.append({
            "secid": secid,
            "membership_rows": int(len(group)),
            "available_bars": int(len(valid)),
            "bar_coverage": float(len(valid) / len(group)) if len(group) else None,
            "median_volume": float(valid["volume"].median()) if valid["volume"].notna().any() else None,
            "median_value": float(valid["value"].median()) if valid["value"].notna().any() else None,
            "median_value_60d": float(group["value_60d"].median()) if group["value_60d"].notna().any() else None,
        })
    return pd.DataFrame(rows), pd.DataFrame(yearly_rows), pd.DataFrame(per_secid)


def temporal_analysis(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    frame = panel.copy()
    frame["year"] = _year(frame)
    frame["available"] = frame["bar_available"].eq(1)
    daily = (
        frame.groupby("tradedate")
        .agg(members=("secid", "size"), bar_coverage=("available", "mean"))
        .reset_index()
    )
    daily["year"] = daily["tradedate"].dt.year
    yearly_members = (
        frame.groupby("year")
        .agg(
            membership_rows=("secid", "size"),
            unique_secids=("secid", "nunique"),
            available_bars=("available", "sum"),
            mean_bar_coverage=("available", "mean"),
            median_universe_size=("universe_size", "median"),
        )
        .reset_index()
    )
    yearly_daily = (
        daily.groupby("year")
        .agg(
            dates=("tradedate", "size"),
            mean_daily_members=("members", "mean"),
            median_daily_members=("members", "median"),
            mean_daily_bar_coverage=("bar_coverage", "mean"),
        )
        .reset_index()
    )
    yearly = yearly_members.merge(yearly_daily, on="year", validate="one_to_one")
    daily_sets = {
        date: set(group["secid"])
        for date, group in frame.groupby("tradedate", sort=True)
    }
    churn = []
    previous: set[str] | None = None
    for date, current in daily_sets.items():
        entrants = 0 if previous is None else len(current - previous)
        exits = 0 if previous is None else len(previous - current)
        churn.append({
            "tradedate": date, "members": len(current),
            "entrants": entrants, "exits": exits,
            "jaccard_to_previous": (
                None if previous is None or not (current | previous)
                else len(current & previous) / len(current | previous)
            ),
        })
        previous = current
    churn_frame = pd.DataFrame(churn)
    coverage = frame.groupby("tradedate")["available"].mean()
    summary = {
        "dates": int(frame["tradedate"].nunique()),
        "secids": int(frame["secid"].nunique()),
        "membership_rows": int(len(frame)),
        "available_bar_rows": int(frame["available"].sum()),
        "overall_bar_coverage": float(frame["available"].mean()),
        "daily_bar_coverage_p05": float(coverage.quantile(0.05)),
        "daily_bar_coverage_median": float(coverage.median()),
        "daily_bar_coverage_p95": float(coverage.quantile(0.95)),
        "mean_daily_members": float(churn_frame["members"].mean()),
        "mean_daily_entrants_after_first_date": float(churn_frame["entrants"].iloc[1:].mean()) if len(churn_frame) > 1 else 0.0,
        "mean_daily_exits_after_first_date": float(churn_frame["exits"].iloc[1:].mean()) if len(churn_frame) > 1 else 0.0,
        "median_membership_jaccard": float(churn_frame["jaccard_to_previous"].dropna().median()) if churn_frame["jaccard_to_previous"].notna().any() else None,
    }
    return yearly, {"summary": summary, "daily_churn": churn_frame}


def consistency_analysis(panel: pd.DataFrame) -> pd.DataFrame:
    available = panel[panel["bar_available"].eq(1)].copy()
    checks = []

    def add(name: str, denominator: int, violations: int, note: str) -> None:
        checks.append({
            "check": name, "n_checked": int(denominator),
            "violations": int(violations),
            "violation_rate": float(violations / denominator) if denominator else None,
            "note": note,
        })

    o, h, l, c = (available[name] for name in (
        "adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close"
    ))
    complete = pd.concat([o, h, l, c], axis=1).notna().all(axis=1)
    add("OHLC complete among bar_available=1", len(available), int((~complete).sum()),
        "A current bar is expected to contain all four adjusted OHLC values.")
    valid = complete
    add("high >= low", int(valid.sum()), int((h[valid] < l[valid]).sum()),
        "Constraint checked only where all OHLC values exist.")
    add("high >= max(open, close)", int(valid.sum()),
        int((h[valid] < pd.concat([o[valid], c[valid]], axis=1).max(axis=1)).sum()),
        "No automatic correction is applied.")
    add("low <= min(open, close)", int(valid.sum()),
        int((l[valid] > pd.concat([o[valid], c[valid]], axis=1).min(axis=1)).sum()),
        "No automatic correction is applied.")
    for column in ("adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close"):
        values = available[column]
        add(f"{column} > 0", int(values.notna().sum()), int((values.dropna() <= 0).sum()),
            "Non-positive adjusted prices are flagged, not modified.")
    for column in ("volume", "value"):
        values = available[column]
        add(f"{column} >= 0", int(values.notna().sum()), int((values.dropna() < 0).sum()),
            "Checked on rows with bar_available=1 to avoid treating unavailable-bar placeholders as market activity.")
    close_present = panel["adjusted_close"].notna()
    add("bar_available=0 but adjusted_close present", int(len(panel)),
        int((panel["bar_available"].eq(0) & close_present).sum()),
        "Checks consistency between availability flag and panel close.")
    add("bar_available=1 but adjusted_close missing", int(len(panel)),
        int((panel["bar_available"].eq(1) & ~close_present).sum()),
        "Checks consistency between availability flag and panel close.")
    return pd.DataFrame(checks)


def future_price_analysis(
    panel: pd.DataFrame,
    prices: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Describe Close[t] -> Close[t+h] for h in market sessions; no model target is defined."""
    start = panel.loc[
        panel["bar_available"].eq(1)
        & panel["adjusted_close"].notna()
        & panel["adjusted_close"].gt(0),
        ["tradedate", "secid", "adjusted_close"],
    ].copy()
    if start.empty:
        raise RuntimeError("No valid panel start closes for future-price analysis.")

    endpoint_frames = []
    grouped = {secid: group for secid, group in prices.groupby("secid", sort=False)}
    for secid in start["secid"].unique():
        history = grouped.get(secid)
        if history is None:
            continue
        close = (
            history.set_index("tradedate")["adjusted_close"]
            .reindex(calendar)
            .astype("float64")
        )
        block = pd.DataFrame({"tradedate": calendar, "secid": secid})
        for horizon in HORIZONS:
            block[f"close_t_plus_{horizon}"] = close.shift(-horizon).to_numpy()
        endpoint_frames.append(block)

    if not endpoint_frames:
        raise RuntimeError("No future endpoint series could be constructed.")
    endpoints = pd.concat(endpoint_frames, ignore_index=True)
    frame = start.merge(endpoints, on=["tradedate", "secid"], how="left", validate="one_to_one")
    frame = frame.rename(columns={"adjusted_close": "close_t"})
    frame["year"] = _year(frame)

    summary_rows = []
    by_year_rows = []
    by_secid_rows = []
    for horizon in HORIZONS:
        endpoint = frame[f"close_t_plus_{horizon}"]
        valid = frame["close_t"].gt(0) & endpoint.gt(0) & endpoint.notna()
        sample = frame.loc[valid, ["tradedate", "secid", "year", "close_t"]].copy()
        sample["close_t_plus_h"] = endpoint.loc[valid]
        sample["absolute_change"] = sample["close_t_plus_h"] - sample["close_t"]
        sample["simple_return"] = sample["close_t_plus_h"] / sample["close_t"] - 1.0
        sample["log_return"] = np.log(sample["close_t_plus_h"] / sample["close_t"])
        for metric in ("absolute_change", "simple_return", "log_return"):
            stats = describe(sample[metric])
            values = sample[metric]
            stats.update({
                "positive_share": float((values > 0).mean()) if len(values) else None,
                "negative_share": float((values < 0).mean()) if len(values) else None,
                "zero_share": float((values == 0).mean()) if len(values) else None,
            })
            summary_rows.append({
                "horizon_sessions": horizon, "metric": metric,
                "start_observations": int(len(frame)),
                "valid_endpoints": int(valid.sum()),
                "unavailable_endpoints": int((~valid).sum()),
                "endpoint_coverage": float(valid.mean()),
                **stats,
            })
            for year, group in sample.groupby("year", sort=True):
                by_year_rows.append({
                    "horizon_sessions": horizon, "metric": metric,
                    "year": int(year), "n": int(len(group)),
                    "mean": float(group[metric].mean()),
                    "median": float(group[metric].median()),
                    "std": float(group[metric].std()),
                    "positive_share": float((group[metric] > 0).mean()),
                    "negative_share": float((group[metric] < 0).mean()),
                    "zero_share": float((group[metric] == 0).mean()),
                })
        ticker_stats = sample.groupby("secid").agg(
            n=("simple_return", "size"),
            mean_simple_return=("simple_return", "mean"),
            median_simple_return=("simple_return", "median"),
            std_simple_return=("simple_return", "std"),
            positive_share=("simple_return", lambda x: float((x > 0).mean())),
            negative_share=("simple_return", lambda x: float((x < 0).mean())),
            zero_share=("simple_return", lambda x: float((x == 0).mean())),
        ).reset_index()
        for row in ticker_stats.to_dict("records"):
            by_secid_rows.append({"horizon_sessions": horizon, **row})

    return (
        pd.DataFrame(summary_rows),
        pd.DataFrame(by_year_rows),
        pd.DataFrame(by_secid_rows),
    )
