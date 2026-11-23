
# pipeline/scripts/experiments/primitives/04_rolling_ic_stability.py

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]

INPUT_PATH = ROOT / "data/interim/primitive_research/daily_ic.csv"
OUTPUT_DIR = ROOT / "data/interim/primitive_research"

WINDOW = 252
MIN_PERIODS = 126


def load_data() -> pd.DataFrame:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH, parse_dates=["tradedate"])

    required = {
        "tradedate",
        "primitive",
        "horizon",
        "n",
        "ic",
        "rank_ic",
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df["ic"] = pd.to_numeric(df["ic"], errors="coerce")
    df["rank_ic"] = pd.to_numeric(df["rank_ic"], errors="coerce")
    df["n"] = pd.to_numeric(df["n"], errors="coerce")

    df = df.dropna(subset=["tradedate", "primitive", "horizon"])
    df = df.sort_values(["primitive", "horizon", "tradedate"])

    duplicates = df.duplicated(
        subset=["tradedate", "primitive", "horizon"]
    )

    if duplicates.any():
        examples = df.loc[
            duplicates,
            ["tradedate", "primitive", "horizon"]
        ].head(10)

        raise ValueError(
            "Duplicate date/primitive/horizon observations found:\n"
            f"{examples.to_string(index=False)}"
        )

    return df


def calculate_rolling(group: pd.DataFrame) -> pd.DataFrame:
    group = group.sort_values("tradedate").copy()

    for metric in ("ic", "rank_ic"):
        values = group[metric]

        rolling = values.rolling(
            window=WINDOW,
            min_periods=MIN_PERIODS,
        )

        group[f"{metric}_rolling_mean"] = rolling.mean()
        group[f"{metric}_rolling_std"] = rolling.std(ddof=1)

        group[f"{metric}_rolling_ir"] = (
            group[f"{metric}_rolling_mean"]
            / group[f"{metric}_rolling_std"].replace(0, np.nan)
        )

        group[f"{metric}_rolling_positive_share"] = (
            (values > 0)
            .rolling(
                window=WINDOW,
                min_periods=MIN_PERIODS,
            )
            .mean()
        )

    group["rolling_observations"] = (
        group["ic"]
        .rolling(
            window=WINDOW,
            min_periods=1,
        )
        .count()
    )

    return group


def build_summary(rolling: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for (primitive, horizon), group in rolling.groupby(
        ["primitive", "horizon"],
        sort=True,
    ):
        valid = group.dropna(subset=["ic_rolling_mean"])

        if valid.empty:
            continue

        last = valid.iloc[-1]

        rows.append({
            "primitive": primitive,
            "horizon": int(horizon),
            "first_rolling_date": valid["tradedate"].min(),
            "last_rolling_date": last["tradedate"],
            "rolling_windows": len(valid),

            "ic_current": last["ic_rolling_mean"],
            "ic_current_ir": last["ic_rolling_ir"],
            "ic_current_positive_share": (
                last["ic_rolling_positive_share"]
            ),

            "rank_ic_current": last["rank_ic_rolling_mean"],
            "rank_ic_current_ir": last["rank_ic_rolling_ir"],
            "rank_ic_current_positive_share": (
                last["rank_ic_rolling_positive_share"]
            ),

            "ic_rolling_min": valid["ic_rolling_mean"].min(),
            "ic_rolling_max": valid["ic_rolling_mean"].max(),

            "rank_ic_rolling_min": (
                valid["rank_ic_rolling_mean"].min()
            ),
            "rank_ic_rolling_max": (
                valid["rank_ic_rolling_mean"].max()
            ),

            "ic_positive_window_share": (
                valid["ic_rolling_mean"] > 0
            ).mean(),

            "rank_ic_positive_window_share": (
                valid["rank_ic_rolling_mean"] > 0
            ).mean(),
        })

    return pd.DataFrame(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading daily IC...")
    df = load_data()

    print(f"Rows: {len(df):,}")
    print(f"Primitives: {df['primitive'].nunique()}")
    print(f"Horizons: {sorted(df['horizon'].unique())}")
    print(
        f"Date range: {df['tradedate'].min().date()} — "
        f"{df['tradedate'].max().date()}"
    )

    print("\nCalculating rolling statistics...")

    rolling_groups = []

    for _, group in df.groupby(
        ["primitive", "horizon"],
        sort=True,
    ):
        rolling_groups.append(calculate_rolling(group))

    rolling = pd.concat(
        rolling_groups,
        ignore_index=True,
    )

    summary = build_summary(rolling)

    rolling_path = OUTPUT_DIR / "rolling_ic.csv"
    summary_path = OUTPUT_DIR / "rolling_ic_summary.csv"
    metadata_path = OUTPUT_DIR / "rolling_ic_metadata.json"

    rolling.to_csv(rolling_path, index=False)
    summary.to_csv(summary_path, index=False)

    metadata = {
        "input_file": str(INPUT_PATH.relative_to(ROOT)),
        "window_observations": WINDOW,
        "minimum_observations": MIN_PERIODS,
        "input_rows": int(len(df)),
        "rolling_rows": int(len(rolling)),
        "summary_rows": int(len(summary)),
        "primitive_count": int(df["primitive"].nunique()),
        "horizons": sorted(
            int(x) for x in df["horizon"].dropna().unique()
        ),
        "date_from": str(df["tradedate"].min().date()),
        "date_till": str(df["tradedate"].max().date()),
        "interpretation": (
            "Rolling means use up to 252 available daily IC observations "
            "per primitive and horizon. Minimum window is 126 observations."
        ),
    }

    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nSaved:")
    print(f"  {rolling_path}")
    print(f"  {summary_path}")
    print(f"  {metadata_path}")

    print("\nCURRENT ROLLING IC")
    display_columns = [
        "primitive",
        "horizon",
        "ic_current",
        "ic_current_ir",
        "ic_current_positive_share",
        "rank_ic_current",
        "rank_ic_current_ir",
        "rank_ic_current_positive_share",
        "ic_positive_window_share",
    ]

    if not summary.empty:
        print(
            summary[display_columns]
            .sort_values(
                ["horizon", "ic_current"],
                ascending=[True, False],
            )
            .to_string(index=False, float_format=lambda x: f"{x:.4f}")
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
