# Folder: scripts/experiments/primitives/breadth/
# File: breadth_analysis.py
# Purpose: Build and evaluate point-in-time market breadth as a separate time-series layer.

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from breadth_config import (
    BREADTH_FEATURES,
    DOUBLE_SORT_BREADTH_BUCKETS,
    DOUBLE_SORT_MARKET_BUCKETS,
    HORIZONS,
    MIN_FORWARD_COVERAGE,
    OUTCOME_TYPES,
    OUTPUT_DIR,
    QUANTILE_COUNT,
    ROLLING_MIN_PERIODS,
    ROLLING_WINDOW,
    SUBPERIODS,
)
from breadth_statistics import (
    benjamini_hochberg,
    hac_correlation_test,
    newey_west_mean_test,
    quantile_labels,
    safe_corr,
)


def _require_columns(frame: pd.DataFrame) -> None:
    required = {
        "tradedate", "secid", "bar_available",
        "price_sma20", "sma20_sma50", "sma50_sma200",
        "return_5", "return_20",
    }
    required.update(f"forward_return_{h}" for h in HORIZONS)
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(
            "Primitive source frame is missing required columns: "
            + ", ".join(sorted(missing))
        )


def build_breadth_daily(
    frame: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    """
    Breadth uses only signal-date PIT TOP50 members with a valid current bar.
    Forward outcomes use the same signal-date cohort, even if a ticker later
    leaves TOP50. No future membership is used to define the cohort.
    """
    _require_columns(frame)
    data = frame.loc[frame["bar_available"].eq(1)].copy().reset_index(drop=True)
    data["tradedate"] = pd.to_datetime(data["tradedate"])
    data = data.sort_values(["tradedate", "secid"])

    price_sma50 = (
        (data["price_sma20"] + 1.0)
        * (data["sma20_sma50"] + 1.0)
        - 1.0
    )
    price_sma200 = (
        (price_sma50 + 1.0)
        * (data["sma50_sma200"] + 1.0)
        - 1.0
    )
    comparisons = {
        "breadth_sma20": data["price_sma20"],
        "breadth_sma50": price_sma50,
        "breadth_sma200": price_sma200,
    }

    rows = []
    for date, positions in data.groupby("tradedate", sort=True).groups.items():
        idx = pd.Index(positions)
        row = {
            "tradedate": date,
            "signal_cohort_n": int(len(idx)),
            "top50_cohort_past_return_5": float(
                pd.to_numeric(data.loc[idx, "return_5"], errors="coerce").mean()
            ),
            "top50_cohort_mean_member_return_20": float(
                pd.to_numeric(data.loc[idx, "return_20"], errors="coerce").mean()
            ),
        }

        for name, values in comparisons.items():
            valid = pd.to_numeric(values.loc[idx], errors="coerce")
            valid = valid.replace([np.inf, -np.inf], np.nan).dropna()
            row[name] = float((valid > 0).mean()) if len(valid) else np.nan
            row[f"{name}_n"] = int(len(valid))

        for horizon in HORIZONS:
            column = f"forward_return_{horizon}"
            future = pd.to_numeric(
                data.loc[idx, column], errors="coerce"
            ).replace([np.inf, -np.inf], np.nan).dropna()

            row[f"top50_cohort_forward_mean_return_{horizon}"] = (
                float(future.mean()) if len(future) else np.nan
            )
            row[f"top50_cohort_forward_median_return_{horizon}"] = (
                float(future.median()) if len(future) else np.nan
            )
            row[f"top50_cohort_forward_positive_share_{horizon}"] = (
                float((future > 0).mean()) if len(future) else np.nan
            )
            row[f"top50_cohort_forward_n_{horizon}"] = int(len(future))

        rows.append(row)

    daily = pd.DataFrame(rows).set_index("tradedate").reindex(calendar)
    daily.index.name = "tradedate"

    for column in ("breadth_sma20", "breadth_sma50", "breadth_sma200"):
        daily[f"{column}_change_5"] = daily[column].diff(5)
        daily[f"{column}_change_20"] = daily[column].diff(20)

    daily["breadth_change_5"] = daily["breadth_sma20"].diff(5)
    daily["breadth_change_20"] = daily["breadth_sma20"].diff(20)

    # Keep the full pre-sample calendar for lookback calculations, but only
    # report signal dates that actually belong to the historical TOP50 panel.
    first_signal_date = data["tradedate"].min()
    daily = daily.loc[daily.index >= first_signal_date]

    # The market return control is backward-looking and calculated on the
    # same signal-date PIT cohort. It is used only for a nonparametric
    # double-sort diagnostic, not as a fitted regression control.
    daily = daily.reset_index()
    return daily


def _target_column(outcome: str, horizon: int) -> str:
    suffix = {
        "mean_return": "mean_return",
        "median_return": "median_return",
        "positive_share": "positive_share",
    }[outcome]
    return f"top50_cohort_forward_{suffix}_{horizon}"


def summarize_correlations(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature in BREADTH_FEATURES:
        for outcome in OUTCOME_TYPES:
            for horizon in HORIZONS:
                target = _target_column(outcome, horizon)
                count = f"top50_cohort_forward_n_{horizon}"
                pair = daily[[feature, target, count]].replace(
                    [np.inf, -np.inf], np.nan
                ).dropna()
                pair = pair[pair[count] >= MIN_FORWARD_COVERAGE]

                lag_count = min(horizon - 1, 19)
                pearson_t, pearson_p = hac_correlation_test(
                    pair[feature], pair[target], "pearson", lag_count
                )
                spearman_t, spearman_p = hac_correlation_test(
                    pair[feature], pair[target], "spearman", lag_count
                )

                rows.append({
                    "breadth_feature": feature,
                    "outcome": outcome,
                    "horizon": horizon,
                    "n_dates": int(len(pair)),
                    "mean_forward_coverage": (
                        float(pair[count].mean()) if len(pair) else np.nan
                    ),
                    "pearson_corr": safe_corr(pair[feature], pair[target], "pearson"),
                    "pearson_hac_t": pearson_t,
                    "pearson_pvalue": pearson_p,
                    "spearman_corr": safe_corr(pair[feature], pair[target], "spearman"),
                    "spearman_hac_t": spearman_t,
                    "spearman_pvalue": spearman_p,
                })

    result = pd.DataFrame(rows)
    result["pearson_qvalue"] = benjamini_hochberg(result["pearson_pvalue"])
    result["spearman_qvalue"] = benjamini_hochberg(result["spearman_pvalue"])
    return result.sort_values(
        ["outcome", "horizon", "spearman_qvalue", "breadth_feature"],
        na_position="last",
    ).reset_index(drop=True)


def summarize_period_stability(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature in BREADTH_FEATURES:
        for outcome in ("mean_return", "positive_share"):
            for horizon in HORIZONS:
                target = _target_column(outcome, horizon)
                count = f"top50_cohort_forward_n_{horizon}"
                for label, start, end in SUBPERIODS:
                    period = daily[
                        daily["tradedate"].between(
                            pd.Timestamp(start), pd.Timestamp(end)
                        )
                    ][[feature, target, count]].replace(
                        [np.inf, -np.inf], np.nan
                    ).dropna()
                    period = period[period[count] >= MIN_FORWARD_COVERAGE]

                    lag_count = min(horizon - 1, 19)
                    pearson_t, pearson_p = hac_correlation_test(
                        period[feature], period[target], "pearson", lag_count
                    )
                    spearman_t, spearman_p = hac_correlation_test(
                        period[feature], period[target], "spearman", lag_count
                    )
                    rows.append({
                        "breadth_feature": feature,
                        "outcome": outcome,
                        "horizon": horizon,
                        "period": label,
                        "n_dates": int(len(period)),
                        "pearson_corr": safe_corr(
                            period[feature], period[target], "pearson"
                        ),
                        "pearson_pvalue": pearson_p,
                        "spearman_corr": safe_corr(
                            period[feature], period[target], "spearman"
                        ),
                        "spearman_pvalue": spearman_p,
                    })
    return pd.DataFrame(rows)


def summarize_quantiles(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature in BREADTH_FEATURES:
        labels = quantile_labels(daily[feature], QUANTILE_COUNT)
        for horizon in HORIZONS:
            for outcome in ("mean_return", "positive_share"):
                target = _target_column(outcome, horizon)
                count = f"top50_cohort_forward_n_{horizon}"
                temp = daily[[feature, target, count]].copy()
                temp["quantile"] = labels
                temp = temp.replace([np.inf, -np.inf], np.nan).dropna(
                    subset=["quantile", target, count]
                )
                temp = temp[temp[count] >= MIN_FORWARD_COVERAGE]

                for bucket, group in temp.groupby("quantile", sort=True):
                    rows.append({
                        "breadth_feature": feature,
                        "horizon": horizon,
                        "outcome": outcome,
                        "quantile": f"Q{int(bucket) + 1}",
                        "n_dates": int(len(group)),
                        "mean_breadth": float(group[feature].mean()),
                        "mean_future_outcome": float(group[target].mean()),
                        "median_future_outcome": float(group[target].median()),
                    })
    return pd.DataFrame(rows)


def summarize_double_sort(daily: pd.DataFrame) -> pd.DataFrame:
    """
    Nonparametric incremental-information diagnostic:
    first bucket dates by backward-looking mean 20-session return of the signal-date TOP50
    members, then bucket breadth within each past-return bucket.
    This is a descriptive conditional sort, not a regression.
    """
    rows = []
    market_bucket = quantile_labels(
        daily["top50_cohort_mean_member_return_20"],
        DOUBLE_SORT_MARKET_BUCKETS,
    )

    for feature in BREADTH_FEATURES:
        work = daily[[
            "tradedate", "top50_cohort_mean_member_return_20", feature,
            "top50_cohort_forward_mean_return_5",
            "top50_cohort_forward_mean_return_10",
            "top50_cohort_forward_mean_return_20",
            "top50_cohort_forward_n_5",
            "top50_cohort_forward_n_10",
            "top50_cohort_forward_n_20",
        ]].copy()
        work["past_return_bucket"] = market_bucket
        work = work.dropna(subset=["past_return_bucket", feature])

        for market_bucket_id, market_group in work.groupby(
            "past_return_bucket", sort=True
        ):
            breadth_bucket = quantile_labels(
                market_group[feature],
                DOUBLE_SORT_BREADTH_BUCKETS,
            )
            market_group = market_group.copy()
            market_group["breadth_bucket"] = breadth_bucket

            for breadth_bucket_id, group in market_group.dropna(
                subset=["breadth_bucket"]
            ).groupby("breadth_bucket", sort=True):
                for horizon in HORIZONS:
                    target = f"top50_cohort_forward_mean_return_{horizon}"
                    count = f"top50_cohort_forward_n_{horizon}"
                    valid = group[[target, count]].dropna()
                    valid = valid[valid[count] >= MIN_FORWARD_COVERAGE]
                    rows.append({
                        "breadth_feature": feature,
                        "past_return_bucket": f"M{int(market_bucket_id) + 1}",
                        "breadth_bucket": f"B{int(breadth_bucket_id) + 1}",
                        "horizon": horizon,
                        "n_dates": int(len(valid)),
                        "mean_member_past_return_20": float(
                            group["top50_cohort_mean_member_return_20"].mean()
                        ),
                        "mean_future_cohort_return": (
                            float(valid[target].mean()) if len(valid) else np.nan
                        ),
                    })
    return pd.DataFrame(rows)


def summarize_rolling(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    indexed = daily.set_index("tradedate").sort_index()

    for feature in BREADTH_FEATURES:
        for horizon in HORIZONS:
            target = _target_column("mean_return", horizon)
            # Keep missing sessions in place: a 252-row window must mean
            # 252 market sessions, not 252 observations after compressing gaps.
            pair = indexed[[feature, target]].replace(
                [np.inf, -np.inf], np.nan
            )
            rolling = pair[feature].rolling(
                ROLLING_WINDOW, min_periods=ROLLING_MIN_PERIODS
            ).corr(pair[target]).dropna()

            rows.append({
                "breadth_feature": feature,
                "horizon": horizon,
                "window": ROLLING_WINDOW,
                "min_periods": ROLLING_MIN_PERIODS,
                "n_rolling_windows": int(len(rolling)),
                "mean_rolling_corr": (
                    float(rolling.mean()) if len(rolling) else np.nan
                ),
                "median_rolling_corr": (
                    float(rolling.median()) if len(rolling) else np.nan
                ),
                "positive_window_share": (
                    float((rolling > 0).mean()) if len(rolling) else np.nan
                ),
                "negative_window_share": (
                    float((rolling < 0).mean()) if len(rolling) else np.nan
                ),
                "min_rolling_corr": (
                    float(rolling.min()) if len(rolling) else np.nan
                ),
                "max_rolling_corr": (
                    float(rolling.max()) if len(rolling) else np.nan
                ),
                "latest_rolling_corr": (
                    float(rolling.iloc[-1]) if len(rolling) else np.nan
                ),
            })
    return pd.DataFrame(rows)


def _markdown_table(frame: pd.DataFrame, columns: list[str], limit: int = 30) -> str:
    if frame.empty:
        return "_Нет доступных наблюдений._"
    view = frame.loc[:, [c for c in columns if c in frame.columns]].head(limit)
    return view.to_string(index=False, float_format=lambda x: f"{x:.5f}")


def write_report(
    daily: pd.DataFrame,
    correlations: pd.DataFrame,
    periods: pd.DataFrame,
    quantiles: pd.DataFrame,
    double_sort: pd.DataFrame,
    rolling: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    key = correlations[
        (correlations["outcome"] == "mean_return")
        & (correlations["horizon"].isin([5, 10, 20]))
    ].sort_values(["horizon", "spearman_qvalue"], na_position="last")

    lines = [
        "# Market Breadth Research",
        "",
        f"- Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"- Dates: {daily['tradedate'].min()} — {daily['tradedate'].max()}",
        f"- Daily observations: {len(daily):,}",
        "- Universe: signal-date point-in-time TOP50 cohort only.",
        "- Forward cohort outcomes retain the signal-date constituents even if they later leave TOP50.",
        "- Forward return: close[T+H] / open[T+1] - 1; H = 5, 10, 20.",
        "- Breadth is a time-series market-state variable, not a cross-sectional IC feature.",
        "- No forward-fill, no regression, no fitted model, no trading strategy.",
        "",
        "## What is measured",
        "",
        "- Breadth SMA20/50/200: share of valid signal-date TOP50 members above the corresponding moving average.",
        "- Breadth change 5/20: change in breadth_sma20 over 5/20 market sessions.",
        "- Future mean and median return: equal-weight/median outcome of the signal-date cohort.",
        "- Future positive share: fraction of that cohort with a positive forward return.",
        "- Incremental diagnostic: double-sort by backward-looking TOP50 20-session return, then by breadth within each past-return bucket.",
        "",
        "## Time-series correlation: future mean cohort return",
        "",
        _markdown_table(
            key,
            ["breadth_feature", "horizon", "n_dates", "pearson_corr",
             "pearson_qvalue", "spearman_corr", "spearman_qvalue",
             "mean_forward_coverage"],
            60,
        ),
        "",
        "## Period stability",
        "",
        _markdown_table(
            periods[periods["outcome"] == "mean_return"].sort_values(
                ["breadth_feature", "horizon", "period"]
            ),
            ["breadth_feature", "horizon", "period", "n_dates",
             "pearson_corr", "pearson_pvalue", "spearman_corr", "spearman_pvalue"],
            100,
        ),
        "",
        "## Quantile analysis",
        "",
        _markdown_table(
            quantiles[quantiles["outcome"] == "mean_return"],
            ["breadth_feature", "horizon", "quantile", "n_dates",
             "mean_breadth", "mean_future_outcome"],
            100,
        ),
        "",
        "## Conditional double-sort",
        "",
        _markdown_table(
            double_sort.sort_values(
                ["breadth_feature", "horizon", "past_return_bucket", "breadth_bucket"]
            ),
            ["breadth_feature", "horizon", "past_return_bucket",
             "breadth_bucket", "n_dates", "mean_future_cohort_return"],
            150,
        ),
        "",
        "## Rolling stability",
        "",
        _markdown_table(
            rolling,
            ["breadth_feature", "horizon", "n_rolling_windows",
             "mean_rolling_corr", "positive_window_share",
             "negative_window_share", "latest_rolling_corr"],
            100,
        ),
        "",
        "## Interpretation constraints",
        "",
        "- Correlation is association, not causality or standalone profitability.",
        "- Overlapping forward horizons create serial dependence; HAC uses lags up to H-1.",
        "- BH q-values are computed separately for Pearson and Spearman tests across the full breadth-feature/outcome/horizon family.",
        "- Quantile and double-sort tables are descriptive. They are not independent out-of-sample validation.",
        "- Breadth is useful as a fourth scanner layer only if the relationship is stable, adds information within past-return regimes, and changes a meaningful market-level decision.",
        "- If breadth only tracks recent market return, it may be redundant rather than an independent layer.",
        "",
    ]
    (OUTPUT_DIR / "breadth_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def run_breadth_analysis(
    frame: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    metadata: dict | None = None,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[BREADTH] Building daily PIT breadth and cohort outcomes...", flush=True)
    daily = build_breadth_daily(frame, calendar)

    print("[BREADTH] Correlation and HAC analysis...", flush=True)
    correlations = summarize_correlations(daily)

    print("[BREADTH] Period stability...", flush=True)
    periods = summarize_period_stability(daily)

    print("[BREADTH] Quantile analysis...", flush=True)
    quantiles = summarize_quantiles(daily)

    print("[BREADTH] Conditional double-sort...", flush=True)
    double_sort = summarize_double_sort(daily)

    print("[BREADTH] Rolling stability...", flush=True)
    rolling = summarize_rolling(daily)

    outputs = {
        "breadth_daily.csv": daily,
        "breadth_correlation_summary.csv": correlations,
        "breadth_period_stability.csv": periods,
        "breadth_quantile_summary.csv": quantiles,
        "breadth_double_sort.csv": double_sort,
        "breadth_rolling_summary.csv": rolling,
    }
    for filename, table in outputs.items():
        table.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    run_metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_script": str(metadata.get("source_script")) if metadata else None,
        "panel_start": str(daily["tradedate"].min()),
        "panel_end": str(daily["tradedate"].max()),
        "daily_rows": int(len(daily)),
        "signal_date_universe": "point-in-time TOP50 membership only",
        "future_outcome_cohort": "same signal-date TOP50 cohort; future membership not required",
        "breadth_features": list(BREADTH_FEATURES),
        "forward_horizons": list(HORIZONS),
        "forward_return_definition": "close[T+H] / open[T+1] - 1",
        "minimum_forward_coverage": MIN_FORWARD_COVERAGE,
        "rolling_window": ROLLING_WINDOW,
        "rolling_min_periods": ROLLING_MIN_PERIODS,
        "no_forward_fill": True,
        "no_regression": True,
        "no_strategy_backtest": True,
    }
    if metadata:
        run_metadata.update({
            "panel_rows": metadata.get("panel_rows"),
            "signal_rows_with_bar": metadata.get("signal_rows_with_bar"),
            "calendar_sessions": metadata.get("calendar_sessions"),
        })

    (OUTPUT_DIR / "breadth_metadata.json").write_text(
        json.dumps(run_metadata, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    write_report(daily, correlations, periods, quantiles, double_sort, rolling)

    print("=" * 68, flush=True)
    print("[BREADTH] MARKET BREADTH RESEARCH COMPLETE", flush=True)
    print(f"[BREADTH] Output: {OUTPUT_DIR}", flush=True)
    print(f"[BREADTH] Report: {OUTPUT_DIR / 'breadth_report.md'}", flush=True)
    print("=" * 68, flush=True)
