
# pipeline/scripts/experiments/primitives/03_period_stability.py

from pathlib import Path
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
INPUT = ROOT / "data/interim/primitive_research/daily_ic.csv"
OUTPUT = ROOT / "data/interim/primitive_research/period_stability.csv"

PERIODS = {
    "2005-2012": ("2005-01-01", "2012-12-31"),
    "2013-2019": ("2013-01-01", "2019-12-31"),
    "2020-2026": ("2020-01-01", "2026-12-31"),
}


def main():
    df = pd.read_csv(INPUT)
    df.columns = [c.strip().lower() for c in df.columns]

    print("Columns:", df.columns.tolist())

    required = {"tradedate", "primitive", "horizon"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df["tradedate"] = pd.to_datetime(df["tradedate"])

    ic_col = next(
        (c for c in ["ic", "pearson_ic", "mean_ic"] if c in df.columns),
        None,
    )
    rank_col = next(
        (c for c in ["rank_ic", "spearman_ic", "mean_rank_ic"]
         if c in df.columns),
        None,
    )

    if ic_col is None or rank_col is None:
        raise ValueError(
            "Cannot identify IC columns. Available columns: "
            + ", ".join(df.columns)
        )

    rows = []

    for (primitive, horizon), group in df.groupby(
        ["primitive", "horizon"], sort=False
    ):
        for period, (start, end) in PERIODS.items():
            part = group.loc[
                group["tradedate"].between(start, end)
            ]

            for metric in [ic_col, rank_col]:
                values = pd.to_numeric(
                    part[metric], errors="coerce"
                ).dropna()

                n = len(values)
                mean = values.mean() if n else np.nan
                std = values.std(ddof=1) if n > 1 else np.nan

                rows.append({
                    "primitive": primitive,
                    "horizon": horizon,
                    "period": period,
                    "metric": metric,
                    "n_dates": n,
                    "mean": mean,
                    "std": std,
                    "ir": mean / std if n > 1 and std > 0 else np.nan,
                    "positive_share": (
                        (values > 0).mean() if n else np.nan
                    ),
                })

    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT, index=False, float_format="%.8f")

    print("\nPERIOD STABILITY SUMMARY")
    print(
        result.sort_values(
            ["primitive", "horizon", "metric", "period"]
        ).to_string(index=False)
    )
    print(f"\nSaved: {OUTPUT}")
    print(f"Rows: {len(result):,}")


if __name__ == "__main__":
    main()
