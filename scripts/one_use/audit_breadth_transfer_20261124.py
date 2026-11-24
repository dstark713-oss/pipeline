from __future__ import annotations

"""
One-use robustness audit for the existing PIT breadth research.

Run from repository root:
  python scripts/one_use/audit_breadth_transfer_20261124.py

Optional matched historical LQDT close series:
  python scripts/one_use/audit_breadth_transfer_20261124.py --lqdt-csv path/to/lqdt_daily.csv

CSV requirements for --lqdt-csv: tradedate, close.
The script is read-only. It does not alter canonical data or portfolio files.

Important:
- Uses the existing breadth_daily.csv outcome convention:
  forward_return_h = close[T+h] / open[T+1] - 1.
- This is not close-to-close and must not be mixed with another return convention.
- LQDT comparison is only calculated when a historical LQDT price series is supplied.
  A current 5d/20d realized LQDT return is NOT a historical matched benchmark.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data/interim/primitive_research/breadth/breadth_daily.csv"
OUT = ROOT / "data/interim/primitive_research/breadth_transfer_audit"
HORIZONS = (5, 20)
CURRENT_BREADTH = 0.08
NW_LAGS = (0, 4, 9, 19, 29, 39)
BUCKETS = [0.0, 0.10, 0.20, 0.30, 0.50, 1.000001]
BUCKET_LABELS = ["0-10%", "10-20%", "20-30%", "30-50%", ">50%"]


def require(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise RuntimeError(f"{label}: missing columns {missing}. Available: {list(frame.columns)}")


def hac_table(data: pd.DataFrame, xcol: str, ycol: str, horizon: int) -> pd.DataFrame:
    pair = data[[xcol, ycol]].replace([np.inf, -np.inf], np.nan).dropna()
    rows = []
    if len(pair) < 50:
        return pd.DataFrame([{"horizon": horizon, "lag": np.nan, "n": len(pair),
                              "beta": np.nan, "se": np.nan, "t": np.nan,
                              "p": np.nan, "ci_low": np.nan, "ci_high": np.nan}])
    X = sm.add_constant(pair[xcol].astype(float))
    y = pair[ycol].astype(float)
    for lag in NW_LAGS:
        fit = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": min(lag, len(pair)-1)})
        ci = fit.conf_int().loc[xcol]
        rows.append({
            "horizon": horizon, "lag": lag, "n": len(pair),
            "beta": float(fit.params[xcol]), "se": float(fit.bse[xcol]),
            "t": float(fit.tvalues[xcol]), "p": float(fit.pvalues[xcol]),
            "ci_low": float(ci.iloc[0]), "ci_high": float(ci.iloc[1]),
            "intercept": float(fit.params["const"]),
        })
    return pd.DataFrame(rows)


def nonoverlap(data: pd.DataFrame, ycol: str, horizon: int) -> pd.DataFrame:
    base = data[["tradedate", "breadth_sma20", ycol]].copy()
    base = base.replace([np.inf, -np.inf], np.nan).dropna()
    base = base.sort_values("tradedate").reset_index(drop=True)
    rows = []
    for offset in range(horizon):
        sample = base.iloc[offset::horizon]
        low = sample[sample["breadth_sma20"] <= 0.10]
        if len(low):
            rows.append({
                "horizon": horizon, "calendar_offset": offset,
                "n_low_breadth": len(low),
                "mean_return_low_breadth": low[ycol].mean(),
                "median_return_low_breadth": low[ycol].median(),
                "positive_share": (low[ycol] > 0).mean(),
            })
    return pd.DataFrame(rows)


def walk_forward(data: pd.DataFrame, ycol: str, horizon: int) -> pd.DataFrame:
    frame = data[["tradedate", "breadth_sma20", ycol]].copy()
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna().sort_values("tradedate")
    frame = frame.reset_index(drop=True)
    predictions = []
    min_train = 756
    # Expanding-window OLS, forecast only after a minimum of 3 years.
    for i in range(min_train, len(frame)):
        train = frame.iloc[:i]
        test = frame.iloc[[i]]
        X_train = sm.add_constant(train[["breadth_sma20"]].astype(float))
        model = sm.OLS(train[ycol].astype(float), X_train).fit()
        X_test = sm.add_constant(test[["breadth_sma20"]].astype(float), has_constant="add")
        pred = float(model.predict(X_test).iloc[0])
        predictions.append({
            "tradedate": test["tradedate"].iloc[0],
            "horizon": horizon,
            "breadth_sma20": float(test["breadth_sma20"].iloc[0]),
            "actual_forward_return": float(test[ycol].iloc[0]),
            "predicted_forward_return": pred,
            "low_breadth": bool(test["breadth_sma20"].iloc[0] <= 0.10),
        })
    return pd.DataFrame(predictions)


def load_lqdt(path: Path) -> pd.DataFrame:
    q = pd.read_csv(path)
    require(q, ["tradedate", "close"], "LQDT CSV")
    q["tradedate"] = pd.to_datetime(q["tradedate"], errors="coerce").dt.normalize()
    q["close"] = pd.to_numeric(q["close"], errors="coerce")
    q = q.dropna(subset=["tradedate", "close"]).sort_values("tradedate")
    q = q.drop_duplicates("tradedate", keep="last").set_index("tradedate")
    return q


def matched_lqdt_returns(signal_dates: pd.Series, lqdt: pd.DataFrame, horizon: int) -> pd.Series:
    # Align on the next available LQDT close after the signal date, then H
    # subsequent LQDT observations. No forward fill and no synthetic dates.
    dates = lqdt.index
    values = []
    for raw_date in signal_dates:
        d = pd.Timestamp(raw_date).normalize()
        start_pos = dates.searchsorted(d, side="right")
        end_pos = start_pos + horizon
        if start_pos < len(dates) and end_pos < len(dates):
            values.append(lqdt["close"].iloc[end_pos] / lqdt["close"].iloc[start_pos] - 1.0)
        else:
            values.append(np.nan)
    return pd.Series(values, index=signal_dates.index, dtype=float)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lqdt-csv", type=Path, default=None)
    args = parser.parse_args()

    if not INPUT.is_file():
        raise FileNotFoundError(
            f"Missing {INPUT}. First run: python scripts/experiments/primitives/breadth/run_breadth_research.py"
        )

    daily = pd.read_csv(INPUT)
    daily["tradedate"] = pd.to_datetime(daily["tradedate"], errors="coerce").dt.normalize()
    require(daily, ["tradedate", "breadth_sma20"], "breadth_daily.csv")

    OUT.mkdir(parents=True, exist_ok=True)
    lqdt = load_lqdt(args.lqdt_csv) if args.lqdt_csv else None
    all_hac, all_nonoverlap, all_oos, all_buckets, all_matched = [], [], [], [], []

    for h in HORIZONS:
        ycol = f"top50_cohort_forward_mean_return_{h}"
        ncol = f"top50_cohort_forward_n_{h}"
        require(daily, [ycol, ncol], f"breadth_daily.csv horizon {h}")
        sample = daily[["tradedate", "breadth_sma20", ycol, ncol]].copy()
        sample = sample[sample[ncol] >= 20]
        sample = sample.replace([np.inf, -np.inf], np.nan).dropna(subset=["breadth_sma20", ycol])
        sample["low_breadth"] = sample["breadth_sma20"] <= 0.10

        hac = hac_table(sample, "breadth_sma20", ycol, h)
        hac["sample_start"] = sample["tradedate"].min()
        hac["sample_end"] = sample["tradedate"].max()
        all_hac.append(hac)

        all_nonoverlap.append(nonoverlap(sample, ycol, h))
        oos = walk_forward(sample, ycol, h)
        all_oos.append(oos)

        sample["breadth_bucket"] = pd.cut(
            sample["breadth_sma20"], bins=BUCKETS,
            labels=BUCKET_LABELS, right=False, include_lowest=True
        )
        buckets = sample.groupby("breadth_bucket", observed=False)[ycol].agg(
            n="count", mean="mean", median="median",
            positive_share=lambda x: float((x > 0).mean())
        ).reset_index()
        buckets["horizon"] = h
        all_buckets.append(buckets)

        if lqdt is not None:
            sample["lqdt_forward_return"] = matched_lqdt_returns(sample["tradedate"], lqdt, h)
            sample["excess_vs_lqdt"] = sample[ycol] - sample["lqdt_forward_return"]
            matched = sample.dropna(subset=["lqdt_forward_return"])
            low = matched[matched["low_breadth"]]
            all_matched.append({
                "horizon": h, "n_all_matched": len(matched), "n_low_breadth": len(low),
                "mean_equity_return_low": low[ycol].mean() if len(low) else np.nan,
                "mean_lqdt_return_matched": low["lqdt_forward_return"].mean() if len(low) else np.nan,
                "mean_excess_low": low["excess_vs_lqdt"].mean() if len(low) else np.nan,
                "share_equity_beats_lqdt": (low["excess_vs_lqdt"] > 0).mean() if len(low) else np.nan,
            })

    pd.concat(all_hac, ignore_index=True).to_csv(OUT / "hac_lag_sensitivity.csv", index=False)
    pd.concat(all_nonoverlap, ignore_index=True).to_csv(OUT / "nonoverlap_low_breadth.csv", index=False)
    pd.concat(all_oos, ignore_index=True).to_csv(OUT / "walk_forward_predictions.csv", index=False)
    pd.concat(all_buckets, ignore_index=True).to_csv(OUT / "breadth_buckets.csv", index=False)
    if all_matched:
        pd.DataFrame(all_matched).to_csv(OUT / "matched_lqdt_comparison.csv", index=False)

    print(f"Input dates: {len(daily):,}; range: {daily['tradedate'].min()} .. {daily['tradedate'].max()}")
    print(f"Current breadth reference: {CURRENT_BREADTH:.1%}")
    print(f"Outputs: {OUT}")
    if lqdt is None:
        print("WARNING: no historical LQDT series supplied; no historical excess-vs-LQDT claim is produced.")
    else:
        print("Matched historical LQDT comparison written. Check calendar alignment and return convention before interpretation.")


if __name__ == "__main__":
    main()
