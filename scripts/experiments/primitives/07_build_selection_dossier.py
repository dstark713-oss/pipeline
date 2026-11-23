
# Folder: scripts/experiments/primitives/
# File: 07_build_selection_dossier.py
# Purpose: Build a unified primitive selection matrix, Markdown report,
#          and dark grayscale correlation heatmap.
#
# Run:
#   python scripts/experiments/primitives/07_build_selection_dossier.py

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = ROOT / "data/interim/primitive_research"
OUTPUT_DIR = DATA_DIR / "selection_dossier"

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

HORIZONS = [5, 10, 20]

PERIODS = [
    "2005-2012",
    "2013-2019",
    "2020-2026",
]

IC_PATH = DATA_DIR / "daily_ic.csv"
PERIOD_PATH = DATA_DIR / "period_stability.csv"
ROLLING_PATH = DATA_DIR / "rolling_ic_summary.csv"
FEATURE_PATH = DATA_DIR / "primitive_features.parquet"

OUTPUT_CSV = OUTPUT_DIR / "primitive_selection_matrix.csv"
OUTPUT_MD = OUTPUT_DIR / "primitive_selection_report.md"
OUTPUT_HEATMAP = OUTPUT_DIR / "primitive_correlation_heatmap.png"


# ============================================================
# HELPERS
# ============================================================

def log(message: str) -> None:
    print(f"[SELECTION] {message}", flush=True)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        str(c).strip().lower()
        for c in df.columns
    ]
    return df


def safe_float(value):
    try:
        value = float(value)
        return value if np.isfinite(value) else np.nan
    except (TypeError, ValueError):
        return np.nan


def fmt(value, digits=4):
    value = safe_float(value)
    if pd.isna(value):
        return "NA"
    return f"{value:.{digits}f}"


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        warnings.warn(f"Missing file: {path}")
        return pd.DataFrame()

    return normalize_columns(pd.read_csv(path))


def find_correlation_file() -> Path | None:
    """
    Find a correlation CSV by its required schema.
    Avoids relying on a hardcoded filename.
    """
    candidates = list(DATA_DIR.glob("*.csv"))

    for path in candidates:
        try:
            sample = pd.read_csv(path, nrows=5)
            sample = normalize_columns(sample)

            required = {
                "feature_a",
                "feature_b",
                "spearman_mean",
            }

            if required.issubset(sample.columns):
                return path

        except Exception:
            continue

    return None


# ============================================================
# LOAD IC DATA
# ============================================================

def load_ic() -> pd.DataFrame:
    df = read_csv_if_exists(IC_PATH)

    if df.empty:
        raise FileNotFoundError(
            f"Required IC file not found or empty: {IC_PATH}"
        )

    required = {
        "tradedate",
        "primitive",
        "horizon",
        "ic",
        "rank_ic",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"daily_ic.csv missing columns: {sorted(missing)}"
        )

    df["tradedate"] = pd.to_datetime(
        df["tradedate"],
        errors="coerce",
    )

    for col in ["ic", "rank_ic", "horizon"]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    df = df.dropna(
        subset=["primitive", "horizon", "tradedate"]
    )

    return df


def summarize_ic(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for (feature, horizon), group in df.groupby(
        ["primitive", "horizon"],
        sort=True,
    ):
        for metric in ["ic", "rank_ic"]:
            values = group[metric].dropna()

            n = len(values)
            mean = values.mean() if n else np.nan
            std = values.std(ddof=1) if n > 1 else np.nan

            rows.append({
                "primitive": feature,
                "horizon": int(horizon),
                "metric": metric,
                "n_dates": n,
                "mean": mean,
                "std": std,
                "ir": (
                    mean / std
                    if n > 1 and pd.notna(std) and std > 0
                    else np.nan
                ),
                "positive_share": (
                    (values > 0).mean()
                    if n else np.nan
                ),
                "negative_share": (
                    (values < 0).mean()
                    if n else np.nan
                ),
            })

    return pd.DataFrame(rows)


# ============================================================
# PERIOD STABILITY
# ============================================================

def load_period_stability() -> pd.DataFrame:
    df = read_csv_if_exists(PERIOD_PATH)

    if df.empty:
        return df

    required = {
        "primitive",
        "horizon",
        "period",
        "metric",
        "mean",
        "positive_share",
    }

    if not required.issubset(df.columns):
        warnings.warn(
            "period_stability.csv has unexpected schema. "
            "Period stability will be omitted."
        )
        return pd.DataFrame()

    return df


def summarize_periods(
    df: pd.DataFrame,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    rows = []

    for feature in FEATURES:
        for horizon in HORIZONS:
            for metric in ["ic", "rank_ic"]:
                part = df[
                    (df["primitive"] == feature)
                    & (df["horizon"] == horizon)
                    & (df["metric"] == metric)
                ]

                row = {
                    "primitive": feature,
                    "horizon": horizon,
                    "metric": metric,
                }

                for period in PERIODS:
                    selected = part[
                        part["period"].astype(str) == period
                    ]

                    if selected.empty:
                        row[f"{period}_mean"] = np.nan
                        row[f"{period}_positive_share"] = np.nan
                    else:
                        item = selected.iloc[0]
                        row[f"{period}_mean"] = safe_float(
                            item["mean"]
                        )
                        row[f"{period}_positive_share"] = safe_float(
                            item["positive_share"]
                        )

                rows.append(row)

    return pd.DataFrame(rows)


# ============================================================
# ROLLING IC
# ============================================================

def load_rolling() -> pd.DataFrame:
    df = read_csv_if_exists(ROLLING_PATH)

    if df.empty:
        return df

    required = {
        "primitive",
        "horizon",
        "ic_current",
        "ic_positive_window_share",
        "rank_ic_current",
        "rank_ic_positive_window_share",
    }

    if not required.issubset(df.columns):
        warnings.warn(
            "rolling_ic_summary.csv has unexpected schema. "
            "Rolling metrics will be omitted."
        )
        return pd.DataFrame()

    return df


# ============================================================
# FEATURE COVERAGE
# ============================================================

def load_feature_coverage() -> pd.DataFrame:
    if not FEATURE_PATH.exists():
        warnings.warn(
            f"Feature frame not found: {FEATURE_PATH}"
        )
        return pd.DataFrame()

    log("Reading primitive feature frame...")

    frame = pd.read_parquet(FEATURE_PATH)

    rows = []

    for feature in FEATURES:
        if feature not in frame.columns:
            rows.append({
                "primitive": feature,
                "feature_rows": len(frame),
                "valid_rows": 0,
                "missing_share": np.nan,
            })
            continue

        valid = frame[feature].notna().sum()

        rows.append({
            "primitive": feature,
            "feature_rows": len(frame),
            "valid_rows": int(valid),
            "missing_share": (
                1.0 - valid / len(frame)
                if len(frame) else np.nan
            ),
        })

    return pd.DataFrame(rows)


# ============================================================
# CORRELATION DATA
# ============================================================

def load_correlations():
    path = find_correlation_file()

    if path is None:
        warnings.warn(
            "Correlation CSV not found. "
            "Heatmap and redundancy metrics will be omitted."
        )
        return pd.DataFrame(), pd.DataFrame()

    log(f"Correlation source: {path.name}")

    df = read_csv_if_exists(path)

    required = {
        "feature_a",
        "feature_b",
        "spearman_mean",
    }

    if not required.issubset(df.columns):
        return pd.DataFrame(), pd.DataFrame()

    if "period" in df.columns:
        df = df[
            df["period"].astype(str).str.lower() == "overall"
        ].copy()

    if df.empty:
        warnings.warn(
            "No overall correlation rows found."
        )
        return pd.DataFrame(), pd.DataFrame()

    # Spearman is the primary redundancy measure.
    # Pearson is retained as a secondary diagnostic.
    matrix = pd.DataFrame(
        np.nan,
        index=FEATURES,
        columns=FEATURES,
        dtype=float,
    )

    np.fill_diagonal(matrix.values, 1.0)

    for row in df.itertuples(index=False):
        a = getattr(row, "feature_a")
        b = getattr(row, "feature_b")

        if a not in FEATURES or b not in FEATURES:
            continue

        value = safe_float(
            getattr(row, "spearman_mean")
        )

        matrix.loc[a, b] = value
        matrix.loc[b, a] = value

    return df, matrix


def build_redundancy(
    matrix: pd.DataFrame,
) -> pd.DataFrame:
    if matrix.empty:
        return pd.DataFrame()

    rows = []

    for feature in FEATURES:
        peers = matrix.loc[feature].drop(
            labels=[feature],
            errors="ignore",
        ).dropna()

        if peers.empty:
            rows.append({
                "primitive": feature,
                "max_abs_spearman": np.nan,
                "nearest_feature": None,
                "nearest_spearman": np.nan,
            })
            continue

        nearest = peers.abs().idxmax()

        rows.append({
            "primitive": feature,
            "max_abs_spearman": abs(peers[nearest]),
            "nearest_feature": nearest,
            "nearest_spearman": peers[nearest],
        })

    return pd.DataFrame(rows)


# ============================================================
# HEATMAP
# ============================================================

def build_heatmap(matrix: pd.DataFrame) -> None:
    if matrix.empty:
        return

    log("Building dark grayscale heatmap...")

    n = len(FEATURES)

    fig, ax = plt.subplots(
        figsize=(17, 15),
        facecolor="#080808",
    )

    ax.set_facecolor("#080808")

    values = matrix.to_numpy(dtype=float)

    image = ax.imshow(
        values,
        cmap="Greys",
        vmin=-1,
        vmax=1,
        interpolation="nearest",
        aspect="auto",
    )

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))

    ax.set_xticklabels(
        FEATURES,
        rotation=65,
        ha="right",
        fontsize=8,
        color="#c8c8c8",
    )

    ax.set_yticklabels(
        FEATURES,
        fontsize=8,
        color="#c8c8c8",
    )

    ax.tick_params(
        axis="both",
        colors="#aaaaaa",
        length=0,
    )

    # Cell values
    for i in range(n):
        for j in range(n):
            value = values[i, j]

            if not np.isfinite(value):
                continue

            # Text contrast against grayscale background.
            text_color = (
                "#111111"
                if value > 0.35
                else "#eeeeee"
            )

            ax.text(
                j,
                i,
                f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=6.5,
                color=text_color,
            )

    ax.set_title(
        "Primitive cross-sectional correlation",
        color="#eeeeee",
        fontsize=14,
        pad=18,
    )

    for spine in ax.spines.values():
        spine.set_color("#555555")

    colorbar = fig.colorbar(
        image,
        ax=ax,
        fraction=0.025,
        pad=0.025,
    )

    colorbar.ax.yaxis.set_tick_params(
        color="#aaaaaa"
    )

    plt.setp(
        colorbar.ax.get_yticklabels(),
        color="#cccccc",
    )

    colorbar.set_label(
        "Mean daily Spearman correlation",
        color="#cccccc",
    )

    fig.tight_layout()

    fig.savefig(
        OUTPUT_HEATMAP,
        dpi=220,
        facecolor=fig.get_facecolor(),
        bbox_inches="tight",
    )

    plt.close(fig)

    log(f"Saved heatmap: {OUTPUT_HEATMAP}")


# ============================================================
# BUILD MASTER SELECTION MATRIX
# ============================================================

def build_master_matrix(
    ic_summary: pd.DataFrame,
    period_summary: pd.DataFrame,
    rolling: pd.DataFrame,
    coverage: pd.DataFrame,
    redundancy: pd.DataFrame,
) -> pd.DataFrame:

    result = pd.DataFrame({
        "primitive": FEATURES,
    })

    # IC and Rank IC metrics for each horizon.
    for metric in ["ic", "rank_ic"]:
        part = ic_summary[
            ic_summary["metric"] == metric
        ]

        for horizon in HORIZONS:
            selected = part[
                part["horizon"] == horizon
            ].set_index("primitive")

            for column in [
                "mean",
                "ir",
                "positive_share",
                "negative_share",
                "n_dates",
            ]:
                name = f"{metric}_h{horizon}_{column}"

                result[name] = result["primitive"].map(
                    selected[column]
                    if column in selected.columns
                    else pd.Series(dtype=float)
                )

    # Period stability for H20.
    if not period_summary.empty:
        for metric in ["ic", "rank_ic"]:
            part = period_summary[
                (period_summary["horizon"] == 20)
                & (period_summary["metric"] == metric)
            ].set_index("primitive")

            for period in PERIODS:
                for suffix in ["mean", "positive_share"]:
                    column = f"{period}_{suffix}"
                    name = f"{metric}_{period}_{suffix}"

                    result[name] = result["primitive"].map(
                        part[column]
                        if column in part.columns
                        else pd.Series(dtype=float)
                    )

    # Rolling stability.
    if not rolling.empty:
        roll = rolling[
            rolling["horizon"] == 20
        ].set_index("primitive")

        for column in [
            "ic_current",
            "ic_current_ir",
            "ic_current_positive_share",
            "rank_ic_current",
            "rank_ic_current_ir",
            "rank_ic_current_positive_share",
            "ic_positive_window_share",
            "rank_ic_positive_window_share",
        ]:
            if column in roll.columns:
                result[f"rolling_{column}"] = result[
                    "primitive"
                ].map(roll[column])

    # Coverage.
    if not coverage.empty:
        cov = coverage.set_index("primitive")

        for column in [
            "valid_rows",
            "missing_share",
        ]:
            result[column] = result["primitive"].map(
                cov[column]
            )

    # Redundancy.
    if not redundancy.empty:
        red = redundancy.set_index("primitive")

        for column in [
            "max_abs_spearman",
            "nearest_feature",
            "nearest_spearman",
        ]:
            result[column] = result["primitive"].map(
                red[column]
            )

    return result


# ============================================================
# MARKDOWN REPORT
# ============================================================

def build_markdown(
    matrix: pd.DataFrame,
    correlations: pd.DataFrame,
    source_files: list[str],
) -> None:

    lines = []

    lines.append("# Primitive Selection Dossier")
    lines.append("")
    lines.append(
        "Automated evidence compilation for preliminary "
        "selection of cross-sectional primitives."
    )
    lines.append("")

    lines.append("## Methodology")
    lines.append("")
    lines.append(
        "- IC and Rank IC are evaluated separately."
    )
    lines.append(
        "- H20 is used as the main comparison horizon in "
        "period and rolling stability summaries."
    )
    lines.append(
        "- Rolling statistics use the existing 252-session "
        "window with 126 minimum observations."
    )
    lines.append(
        "- Redundancy is measured using absolute mean daily "
        "cross-sectional Spearman correlation."
    )
    lines.append(
        "- No composite score or automatic keep/drop decision "
        "is generated."
    )
    lines.append(
        "- Correlation does not establish incremental predictive "
        "information or conditional IC."
    )
    lines.append("")

    lines.append("## Data sources")
    lines.append("")

    for source in source_files:
        lines.append(f"- `{source}`")

    lines.append("")

    lines.append("## H20 summary")
    lines.append("")

    columns = [
        "primitive",
        "ic_h20_mean",
        "rank_ic_h20_mean",
        "rolling_ic_current",
        "rolling_rank_ic_current",
        "rolling_ic_positive_window_share",
        "max_abs_spearman",
        "nearest_feature",
        "missing_share",
    ]

    available = [
        c for c in columns
        if c in matrix.columns
    ]

    view = matrix[available].copy()

    lines.append(
        view.to_markdown(
            index=False,
            floatfmt=".4f",
        )
    )

    lines.append("")

    lines.append("## Period stability: H20")
    lines.append("")

    period_columns = [
        c for c in matrix.columns
        if any(
            period in c
            for period in PERIODS
        )
    ]

    period_view = matrix[
        ["primitive"] + period_columns
    ]

    lines.append(
        period_view.to_markdown(
            index=False,
            floatfmt=".4f",
        )
    )

    lines.append("")

    lines.append("## Highly correlated pairs")
    lines.append("")

    if not correlations.empty:
        corr = correlations.copy()

        corr["abs_spearman"] = pd.to_numeric(
            corr["spearman_mean"],
            errors="coerce",
        ).abs()

        corr = corr.sort_values(
            "abs_spearman",
            ascending=False,
        )

        corr = corr[
            corr["feature_a"] != corr["feature_b"]
        ].drop_duplicates(
            subset=["feature_a", "feature_b"]
        )

        lines.append(
            "| Feature A | Feature B | Spearman | Pearson |"
        )
        lines.append(
            "|---|---|---:|---:|"
        )

        for row in corr.head(30).itertuples(index=False):
            pearson = getattr(
                row,
                "pearson_mean",
                np.nan,
            )

            lines.append(
                f"| {row.feature_a} | {row.feature_b} "
                f"| {fmt(row.spearman_mean)} "
                f"| {fmt(pearson)} |"
            )

    else:
        lines.append(
            "Correlation data unavailable."
        )

    lines.append("")

    lines.append("## Interpretation warnings")
    lines.append("")
    lines.append(
        "1. A high absolute correlation indicates overlap, "
        "not necessarily complete redundancy."
    )
    lines.append(
        "2. A feature with low correlation may still have "
        "little predictive value."
    )
    lines.append(
        "3. IC values across overlapping forward horizons "
        "are not independent observations."
    )
    lines.append(
        "4. Historical period stability does not guarantee "
        "future stability."
    )
    lines.append(
        "5. The current rolling window is descriptive and "
        "should not be treated as a standalone selection rule."
    )
    lines.append(
        "6. Correlation matrices aggregated over time can hide "
        "regime-dependent relationships."
    )
    lines.append("")

    lines.append("## Preliminary selection")
    lines.append("")
    lines.append(
        "No automatic selection is made by this script. "
        "The evidence table is intended for a documented "
        "keep / conditional / drop decision."
    )
    lines.append("")

    OUTPUT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    log("Loading daily IC...")
    daily_ic = load_ic()
    ic_summary = summarize_ic(daily_ic)

    log("Loading period stability...")
    period_raw = load_period_stability()
    period_summary = summarize_periods(period_raw)

    log("Loading rolling IC...")
    rolling = load_rolling()

    log("Loading feature coverage...")
    coverage = load_feature_coverage()

    log("Loading correlation data...")
    correlations, correlation_matrix = load_correlations()

    redundancy = build_redundancy(
        correlation_matrix
    )

    log("Building master selection matrix...")
    master = build_master_matrix(
        ic_summary,
        period_summary,
        rolling,
        coverage,
        redundancy,
    )

    master.to_csv(
        OUTPUT_CSV,
        index=False,
        float_format="%.8f",
    )

    build_heatmap(correlation_matrix)

    source_files = [
        IC_PATH.name,
        PERIOD_PATH.name,
        ROLLING_PATH.name,
        FEATURE_PATH.name,
    ]

    if not correlations.empty:
        source_files.append(
            find_correlation_file().name
        )

    build_markdown(
        master,
        correlations,
        source_files,
    )

    metadata = {
        "feature_count": len(FEATURES),
        "horizons": HORIZONS,
        "periods": PERIODS,
        "rows": len(master),
        "outputs": {
            "matrix": str(OUTPUT_CSV.relative_to(ROOT)),
            "report": str(OUTPUT_MD.relative_to(ROOT)),
            "heatmap": str(OUTPUT_HEATMAP.relative_to(ROOT)),
        },
    }

    (OUTPUT_DIR / "metadata.json").write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    log("COMPLETE")
    log(f"CSV: {OUTPUT_CSV}")
    log(f"MD: {OUTPUT_MD}")
    log(f"HEATMAP: {OUTPUT_HEATMAP}")

    print("\nH20 QUICK VIEW")

    display = [
        "primitive",
        "ic_h20_mean",
        "rank_ic_h20_mean",
        "rolling_ic_current",
        "max_abs_spearman",
        "nearest_feature",
    ]

    display = [
        c for c in display
        if c in master.columns
    ]

    print(
        master[display].to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )


if __name__ == "__main__":
    main()
