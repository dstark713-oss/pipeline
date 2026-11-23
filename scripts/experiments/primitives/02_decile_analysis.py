
# Folder: scripts/experiments/primitives/
# File: 02_decile_analysis.py
# Purpose: Analyze cross-sectional primitive deciles, monotonicity,
#          top-bottom spreads, and stability across historical periods.
#
# Execution:
#   python scripts/experiments/primitives/02_decile_analysis.py

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BASE_SCRIPT = (
    PROJECT_ROOT
    / "scripts"
    / "experiments"
    / "primitives"
    / "01_research_report.py"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "primitive_research"
    / "decile_analysis"
)

PERIODS = (
    ("FULL", "2005-01-01", "2099-12-31"),
    ("2005-2012", "2005-01-01", "2012-12-31"),
    ("2013-2019", "2013-01-01", "2019-12-31"),
    ("2020+", "2020-01-01", "2099-12-31"),
)

MIN_CROSS_SECTION = 20
N_DECILES = 10


def log(message: str) -> None:
    print(message, flush=True)


def load_base_module():
    if not BASE_SCRIPT.is_file():
        raise FileNotFoundError(f"Base script not found: {BASE_SCRIPT}")

    spec = importlib.util.spec_from_file_location(
        "primitive_research_base",
        BASE_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the base research module.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_research_frame(base) -> pd.DataFrame:
    panel = base.load_panel()
    secids = sorted(panel["secid"].unique())

    history, calendar = base.load_adjusted_history(secids)
    frame = base.build_feature_frame(panel, history, calendar)

    frame = frame[frame["bar_available"].eq(1)].copy()
    frame["tradedate"] = pd.to_datetime(frame["tradedate"])

    return frame


def assign_daily_deciles(
    frame: pd.DataFrame,
    features: list[str],
    horizons: tuple[int, ...],
) -> pd.DataFrame:
    """
    Assign deciles independently for every signal date and primitive.

    Decile 1 = lowest feature values.
    Decile 10 = highest feature values.

    Daily cross-sections receive equal weight in the final summaries.
    """
    records = []

    grouped = frame.groupby("tradedate", sort=True)

    for feature in features:
        log(f"Assigning deciles: {feature}")

        for date, group in grouped:
            values = pd.to_numeric(group[feature], errors="coerce")

            valid = values.notna() & np.isfinite(values)
            if int(valid.sum()) < MIN_CROSS_SECTION:
                continue

            selected = group.loc[valid, ["secid"]].copy()
            selected["feature_value"] = values.loc[valid].to_numpy()

            # Average ranks handle ties without arbitrarily splitting
            # securities with identical primitive values.
            percentile = selected["feature_value"].rank(
                method="average",
                pct=True,
            )

            selected["decile"] = np.ceil(
                percentile * N_DECILES
            ).clip(1, N_DECILES).astype(int)

            selected["tradedate"] = date
            selected["primitive"] = feature

            for horizon in horizons:
                target = f"forward_return_{horizon}"

                if target not in group.columns:
                    continue

                selected[target] = pd.to_numeric(
                    group.loc[valid, target],
                    errors="coerce",
                ).to_numpy()

                outcome = selected.dropna(subset=[target])

                if outcome.empty:
                    continue

                daily = (
                    outcome.groupby("decile", as_index=False)
                    .agg(
                        mean_forward_return=(target, "mean"),
                        median_forward_return=(target, "median"),
                        n_securities=(target, "count"),
                    )
                )

                daily["tradedate"] = date
                daily["primitive"] = feature
                daily["horizon"] = horizon

                records.append(daily)

    if not records:
        raise RuntimeError("No decile observations were generated.")

    return pd.concat(records, ignore_index=True)



def summarize_deciles(
    daily: pd.DataFrame,
    hac_test,
) -> pd.DataFrame:
    """
    Summarize decile returns by period.

    Every signal date has equal weight, rather than every security.
    This prevents dates with larger cross-sections from dominating.
    """
    rows = []

    for (feature, horizon), group in daily.groupby(
        ["primitive", "horizon"],
        sort=True,
    ):
        for period, start, end in PERIODS:
            subset = group[
                (group["tradedate"] >= pd.Timestamp(start))
                & (group["tradedate"] <= pd.Timestamp(end))
            ].copy()

            if subset.empty:
                continue

            decile_stats = (
                subset.groupby("decile")
                .agg(
                    mean_return=("mean_forward_return", "mean"),
                    median_return=("mean_forward_return", "median"),
                    mean_n_securities=("n_securities", "mean"),
                    n_dates=("tradedate", "nunique"),
                )
                .reindex(range(1, N_DECILES + 1))
            )

            # Both extreme deciles must actually have observations.
            low_return = decile_stats.loc[1, "mean_return"]
            high_return = decile_stats.loc[10, "mean_return"]

            # Daily top-minus-bottom spread.
            pivot = subset.pivot_table(
                index="tradedate",
                columns="decile",
                values="mean_forward_return",
                aggfunc="mean",
            )

            if (
                1 in pivot.columns
                and 10 in pivot.columns
            ):
                spread = (pivot[10] - pivot[1]).dropna()
            else:
                spread = pd.Series(dtype=float)

            # Daily Spearman correlation between decile number
            # and average forward return.
            monotonicity_values = []

            for _, day in subset.groupby("tradedate", sort=False):
                valid_day = day.dropna(
                    subset=["mean_forward_return"]
                )

                if valid_day["decile"].nunique() < 5:
                    continue

                correlation = valid_day["decile"].corr(
                    valid_day["mean_forward_return"],
                    method="spearman",
                )

                if pd.notna(correlation):
                    monotonicity_values.append(float(correlation))

            spread_t, spread_p = (
                hac_test(
                    spread,
                    min(int(horizon) - 1, 19),
                )
                if len(spread) >= 30
                else (np.nan, np.nan)
            )

            row = {
                "primitive": feature,
                "horizon": int(horizon),
                "period": period,
                "n_dates": int(subset["tradedate"].nunique()),

                "low_decile_return": (
                    float(low_return)
                    if pd.notna(low_return)
                    else np.nan
                ),
                "high_decile_return": (
                    float(high_return)
                    if pd.notna(high_return)
                    else np.nan
                ),
                "top_bottom_spread": (
                    float(high_return - low_return)
                    if pd.notna(low_return) and pd.notna(high_return)
                    else np.nan
                ),

                "spread_daily_mean": (
                    float(spread.mean())
                    if len(spread) else np.nan
                ),
                "spread_daily_median": (
                    float(spread.median())
                    if len(spread) else np.nan
                ),
                "spread_hac_t": spread_t,
                "spread_hac_pvalue": spread_p,

                "monotonicity_spearman_mean": (
                    float(np.mean(monotonicity_values))
                    if monotonicity_values else np.nan
                ),
                "monotonicity_positive_share": (
                    float(np.mean(
                        np.asarray(monotonicity_values) > 0
                    ))
                    if monotonicity_values else np.nan
                ),

                "mean_forward_coverage_per_date": float(
                    subset.groupby("tradedate")["n_securities"]
                    .sum()
                    .mean()
                ),
            }

            for decile in range(1, N_DECILES + 1):
                value = decile_stats.loc[decile, "mean_return"]
                row[f"decile_{decile}_return"] = (
                    float(value) if pd.notna(value) else np.nan
                )

            rows.append(row)

    return pd.DataFrame(rows)



def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log("=" * 65)
    log("PRIMITIVE DECILE ANALYSIS")
    log("=" * 65)

    base = load_base_module()

    frame = build_research_frame(base)

    log(
        f"Research frame: {len(frame):,} rows; "
        f"{frame['tradedate'].nunique():,} dates; "
        f"{frame['secid'].nunique():,} tickers"
    )

    daily = assign_daily_deciles(
        frame=frame,
        features=base.CROSS_SECTIONAL_FEATURES,
        horizons=base.FORWARD_HORIZONS,
    )

    summary = summarize_deciles(
        daily,
        base.newey_west_mean_test,
    )

    daily_path = OUTPUT_DIR / "decile_daily.csv"
    summary_path = OUTPUT_DIR / "decile_summary.csv"

    daily.to_csv(
        daily_path,
        index=False,
        encoding="utf-8-sig",
    )

    summary.to_csv(
        summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    log("=" * 65)
    log("DECILE ANALYSIS COMPLETE")
    log(f"Daily output: {daily_path}")
    log(f"Summary output: {summary_path}")
    log("=" * 65)

    display_columns = [
        "primitive",
        "horizon",
        "period",
        "n_dates",
        "low_decile_return",
        "high_decile_return",
        "top_bottom_spread",
        "spread_hac_t",
        "spread_hac_pvalue",
        "monotonicity_spearman_mean",
        "monotonicity_positive_share",
    ]

    full = summary[summary["period"].eq("FULL")]

    print("\nFULL PERIOD SUMMARY:")
    print(
        full[display_columns]
        .sort_values(
            ["horizon", "top_bottom_spread"],
            ascending=[True, False],
        )
        .to_string(
            index=False,
            float_format=lambda value: f"{value:.5f}",
        )
    )


if __name__ == "__main__":
    main()
