
# Folder: scripts/experiments/primitives/
# File: 06_primitive_correlation.py
# Purpose: Cross-sectional correlation and redundancy analysis of primitive features.

from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]

INPUT_PATH = (
    ROOT
    / "data/interim/primitive_research/primitive_features.parquet"
)

OUTPUT_DIR = (
    ROOT
    / "data/interim/primitive_research/correlation"
)

FEATURES = [
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

PERIODS = {
    "2005_2012": (2005, 2012),
    "2013_2019": (2013, 2019),
    "2020_2026": (2020, 2026),
}

MIN_PAIR_N = 20
CLUSTER_THRESHOLD = 0.70

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def log(message: str) -> None:
    logging.info(message)


def load_features() -> pd.DataFrame:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Primitive feature file not found: {INPUT_PATH}"
        )

    log(f"Reading {INPUT_PATH}")

    frame = pd.read_parquet(INPUT_PATH)

    required = {"tradedate", "secid", *FEATURES}
    missing = sorted(required - set(frame.columns))

    if missing:
        raise RuntimeError(
            f"Missing required columns: {missing}"
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

    for feature in FEATURES:
        frame[feature] = pd.to_numeric(
            frame[feature],
            errors="coerce",
        )

    if frame.duplicated(
        ["tradedate", "secid"]
    ).any():
        duplicates = frame.loc[
            frame.duplicated(
                ["tradedate", "secid"],
                keep=False,
            ),
            ["tradedate", "secid"],
        ]

        raise RuntimeError(
            "Duplicate tradedate/secid rows found:\n"
            + duplicates.head(20).to_string(index=False)
        )

    frame = frame.sort_values(
        ["tradedate", "secid"]
    ).reset_index(drop=True)

    if frame.empty:
        raise RuntimeError("Feature frame is empty.")

    log(
        f"Loaded {len(frame):,} rows, "
        f"{frame['secid'].nunique():,} tickers, "
        f"{frame['tradedate'].nunique():,} dates."
    )

    return frame


def make_period_masks(
    dates: pd.Series,
) -> dict[str, pd.Series]:
    years = dates.dt.year

    masks = {
        "overall": pd.Series(
            True,
            index=dates.index,
        )
    }

    for name, (start_year, end_year) in PERIODS.items():
        masks[name] = (
            (years >= start_year)
            & (years <= end_year)
        )

    return masks


def calculate_daily_correlations(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate pairwise cross-sectional correlations separately
    for each trading date.

    Each observation in the resulting dataset represents:
    one date + one pair of features.
    """

    feature_count = len(FEATURES)

    feature_indices = [
        (i, j)
        for i in range(feature_count)
        for j in range(i + 1, feature_count)
    ]

    records = []

    grouped = frame.groupby(
        "tradedate",
        sort=True,
    )

    total_dates = len(grouped)

    for date_number, (tradedate, group) in enumerate(
        grouped,
        start=1,
    ):
        values = group[FEATURES]

        valid = values.notna().to_numpy(
            dtype=np.int32
        )

        # Pairwise complete observation count.
        counts = valid.T @ valid

        pearson = values.corr(
            method="pearson",
            min_periods=MIN_PAIR_N,
        )

        spearman = values.corr(
            method="spearman",
            min_periods=MIN_PAIR_N,
        )

        for i, j in feature_indices:
            n = int(counts[i, j])

            if n < MIN_PAIR_N:
                continue

            pearson_value = pearson.iat[i, j]
            spearman_value = spearman.iat[i, j]

            if (
                pd.isna(pearson_value)
                or pd.isna(spearman_value)
            ):
                continue

            records.append(
                {
                    "tradedate": tradedate,
                    "feature_a": FEATURES[i],
                    "feature_b": FEATURES[j],
                    "n": n,
                    "pearson": float(pearson_value),
                    "spearman": float(spearman_value),
                }
            )

        if (
            date_number % 250 == 0
            or date_number == total_dates
        ):
            log(
                f"Processed dates: "
                f"{date_number:,}/{total_dates:,}; "
                f"daily pair observations: {len(records):,}"
            )

    result = pd.DataFrame.from_records(records)

    if result.empty:
        raise RuntimeError(
            "No valid daily correlations were calculated."
        )

    result["year"] = result["tradedate"].dt.year

    return result


def aggregate_correlations(
    daily: pd.DataFrame,
    period_name: str,
) -> pd.DataFrame:
    if period_name == "overall":
        selected = daily.copy()
    else:
        start_year, end_year = PERIODS[period_name]

        selected = daily[
            daily["year"].between(
                start_year,
                end_year,
            )
        ].copy()

    if selected.empty:
        return pd.DataFrame()

    grouped = selected.groupby(
        ["feature_a", "feature_b"],
        sort=True,
    )

    summary = grouped.agg(
        valid_dates=("tradedate", "nunique"),
        mean_n=("n", "mean"),
        median_n=("n", "median"),
        pearson_mean=("pearson", "mean"),
        pearson_median=("pearson", "median"),
        pearson_std=("pearson", "std"),
        pearson_positive_share=(
            "pearson",
            lambda x: (x > 0).mean(),
        ),
        spearman_mean=("spearman", "mean"),
        spearman_median=("spearman", "median"),
        spearman_std=("spearman", "std"),
        spearman_positive_share=(
            "spearman",
            lambda x: (x > 0).mean(),
        ),
    ).reset_index()

    return summary


def build_matrix(
    summary: pd.DataFrame,
    metric: str,
    statistic: str,
) -> pd.DataFrame:
    column = f"{metric}_{statistic}"

    matrix = pd.DataFrame(
        np.nan,
        index=FEATURES,
        columns=FEATURES,
        dtype=float,
    )

    # Создаём изменяемую копию NumPy-массива.
    values = matrix.to_numpy(copy=True)

    np.fill_diagonal(
        values,
        1.0,
    )

    matrix = pd.DataFrame(
        values,
        index=FEATURES,
        columns=FEATURES,
        dtype=float,
    )

    if summary.empty:
        return matrix

    for row in summary.itertuples(index=False):
        value = getattr(row, column)

        matrix.loc[
            row.feature_a,
            row.feature_b,
        ] = value

        matrix.loc[
            row.feature_b,
            row.feature_a,
        ] = value

    return matrix

def save_matrices(
    summary: pd.DataFrame,
    period_name: str,
) -> dict[str, pd.DataFrame]:
    matrices = {}

    for metric in ["pearson", "spearman"]:
        for statistic in ["mean", "median"]:
            name = f"{metric}_{statistic}"

            matrix = build_matrix(
                summary,
                metric,
                statistic,
            )

            matrices[name] = matrix

            path = (
                OUTPUT_DIR
                / f"{period_name}_{name}_matrix.csv"
            )

            matrix.to_csv(
                path,
                index=True,
                index_label="feature",
                float_format="%.6f",
            )

    return matrices


def save_heatmap(
    matrix: pd.DataFrame,
    title: str,
    output_path: Path,
) -> None:
    size = max(
        12,
        len(FEATURES) * 0.72,
    )

    fig, ax = plt.subplots(
        figsize=(size, size),
    )

    image = ax.imshow(
        matrix.to_numpy(dtype=float),
        vmin=-1,
        vmax=1,
        cmap="coolwarm",
        aspect="auto",
    )

    ax.set_xticks(range(len(FEATURES)))
    ax.set_yticks(range(len(FEATURES)))

    ax.set_xticklabels(
        FEATURES,
        rotation=90,
        fontsize=8,
    )

    ax.set_yticklabels(
        FEATURES,
        fontsize=8,
    )

    ax.set_title(
        title,
        fontsize=13,
        pad=16,
    )

    colorbar = fig.colorbar(
        image,
        ax=ax,
        fraction=0.046,
        pad=0.04,
    )

    colorbar.set_label("Correlation")

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close(fig)


def build_clusters(
    summary: pd.DataFrame,
) -> pd.DataFrame:
    """
    Exploratory connected components based on absolute
    median daily cross-sectional Spearman correlation.

    An edge exists when abs(correlation) >= threshold.
    This is a diagnostic grouping, not a final feature-selection rule.
    """

    graph = {
        feature: set()
        for feature in FEATURES
    }

    if not summary.empty:
        for row in summary.itertuples(index=False):
            value = row.spearman_median

            if (
                pd.notna(value)
                and abs(value) >= CLUSTER_THRESHOLD
            ):
                graph[row.feature_a].add(row.feature_b)
                graph[row.feature_b].add(row.feature_a)

    visited = set()
    records = []
    cluster_number = 0

    for feature in FEATURES:
        if feature in visited:
            continue

        cluster_number += 1
        stack = [feature]
        members = []

        while stack:
            current = stack.pop()

            if current in visited:
                continue

            visited.add(current)
            members.append(current)

            for neighbor in graph[current]:
                if neighbor not in visited:
                    stack.append(neighbor)

        members.sort()

        for member in members:
            records.append(
                {
                    "feature": member,
                    "cluster": cluster_number,
                    "cluster_size": len(members),
                    "cluster_members": "|".join(members),
                    "threshold": CLUSTER_THRESHOLD,
                }
            )

    return pd.DataFrame(records)


def build_feature_quality(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    records = []

    for feature in FEATURES:
        series = frame[feature]

        records.append(
            {
                "feature": feature,
                "rows": len(series),
                "non_null": int(series.notna().sum()),
                "missing": int(series.isna().sum()),
                "missing_share": float(series.isna().mean()),
                "unique_values": int(series.nunique()),
                "std": (
                    float(series.std())
                    if series.notna().sum() > 1
                    else None
                ),
            }
        )

    return pd.DataFrame(records)


def main() -> None:
    setup_logging()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    log("Starting primitive correlation analysis.")

    frame = load_features()

    feature_quality = build_feature_quality(frame)

    feature_quality.to_csv(
        OUTPUT_DIR / "feature_quality.csv",
        index=False,
        float_format="%.8f",
    )

    log("Calculating daily cross-sectional correlations...")

    daily = calculate_daily_correlations(frame)

    daily.to_csv(
        OUTPUT_DIR / "daily_pair_correlations.csv",
        index=False,
        float_format="%.8f",
    )

    log(
        f"Daily correlation records: {len(daily):,}; "
        f"dates: {daily['tradedate'].nunique():,}"
    )

    all_summaries = []

    period_names = ["overall", *PERIODS.keys()]

    for period_name in period_names:
        log(f"Aggregating period: {period_name}")

        summary = aggregate_correlations(
            daily,
            period_name,
        )

        if summary.empty:
            log(
                f"No valid correlations for {period_name}; "
                "skipping matrices."
            )
            continue

        summary.insert(
            0,
            "period",
            period_name,
        )

        all_summaries.append(summary)

        summary.to_csv(
            OUTPUT_DIR / f"{period_name}_pair_summary.csv",
            index=False,
            float_format="%.8f",
        )

        matrices = save_matrices(
            summary,
            period_name,
        )

        save_heatmap(
            matrices["pearson_mean"],
            f"Pearson mean daily cross-sectional correlation: {period_name}",
            OUTPUT_DIR / f"{period_name}_pearson_heatmap.png",
        )

        save_heatmap(
            matrices["spearman_mean"],
            f"Spearman mean daily cross-sectional correlation: {period_name}",
            OUTPUT_DIR / f"{period_name}_spearman_heatmap.png",
        )

        log(
            f"{period_name}: "
            f"{len(summary):,} feature pairs saved."
        )

    if not all_summaries:
        raise RuntimeError(
            "No period summaries were generated."
        )

    combined_summary = pd.concat(
        all_summaries,
        ignore_index=True,
    )

    combined_summary.to_csv(
        OUTPUT_DIR / "all_periods_pair_summary.csv",
        index=False,
        float_format="%.8f",
    )

    overall = aggregate_correlations(
        daily,
        "overall",
    )

    clusters = build_clusters(overall)

    clusters.to_csv(
        OUTPUT_DIR / "overall_spearman_clusters.csv",
        index=False,
    )

    metadata = {
        "input_file": str(INPUT_PATH),
        "output_dir": str(OUTPUT_DIR),
        "rows": int(len(frame)),
        "tickers": int(frame["secid"].nunique()),
        "dates": int(frame["tradedate"].nunique()),
        "date_from": str(frame["tradedate"].min().date()),
        "date_till": str(frame["tradedate"].max().date()),
        "features": FEATURES,
        "feature_count": len(FEATURES),
        "method": (
            "Daily cross-sectional pairwise Pearson and Spearman "
            "correlations across securities, aggregated over dates."
        ),
        "min_pair_n": MIN_PAIR_N,
        "cluster_method": (
            "Connected components of absolute overall median "
            "daily cross-sectional Spearman correlation."
        ),
        "cluster_threshold": CLUSTER_THRESHOLD,
        "periods": PERIODS,
        "daily_pair_records": int(len(daily)),
        "daily_pair_dates": int(daily["tradedate"].nunique()),
    }

    with open(
        OUTPUT_DIR / "correlation_metadata.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2,
        )

    log("PRIMITIVE CORRELATION ANALYSIS COMPLETE.")

    log(f"Output directory: {OUTPUT_DIR}")

    log(
        "Main outputs: "
        "all_periods_pair_summary.csv, "
        "overall_spearman_clusters.csv, "
        "overall_spearman_mean_matrix.csv, "
        "overall_spearman_heatmap.png"
    )


if __name__ == "__main__":
    main()
