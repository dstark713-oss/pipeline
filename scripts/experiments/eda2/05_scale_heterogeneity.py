from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PANEL = ROOT / "data" / "processed" / "top50" / "top50_panel.parquet"
DEFAULT_OUTPUT = ROOT / "data" / "interim" / "eda2" / "block_05"
DEFAULT_DOCS = ROOT / "docs" / "research" / "eda2" / "results" / "block_05"
WINDOWS = (20, 60, 120, 240)
PERIODS = (
    ("2005_2012", "2005-01-01", "2012-12-31"),
    ("2013_2019", "2013-01-01", "2019-12-31"),
    ("2020_2026", "2020-01-01", "2026-12-31"),
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="EDA2 Block 5: scale heterogeneity.")
    p.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS)
    return p.parse_args()


def load_returns(panel_path: Path) -> tuple[pd.DataFrame, dict]:
    columns = ["tradedate", "secid", "adjusted_close", "bar_available"]
    panel = pd.read_parquet(panel_path, columns=columns)
    panel["tradedate"] = pd.to_datetime(panel["tradedate"], errors="coerce")
    panel["secid"] = panel["secid"].astype(str).str.upper()
    panel["adjusted_close"] = pd.to_numeric(panel["adjusted_close"], errors="coerce")
    panel["bar_available"] = pd.to_numeric(panel["bar_available"], errors="coerce")
    panel = panel.dropna(subset=["tradedate", "secid"]).sort_values(["tradedate", "secid"])
    if panel.duplicated(["tradedate", "secid"]).any():
        raise ValueError("Duplicate (tradedate, secid) rows in PIT panel.")

    dates = pd.DatetimeIndex(sorted(panel["tradedate"].unique()))
    prices = panel.pivot(index="tradedate", columns="secid", values="adjusted_close").reindex(index=dates)
    available = panel.pivot(index="tradedate", columns="secid", values="bar_available").reindex(index=dates).fillna(0).eq(1)
    prev = prices.shift(1)
    valid = available & available.shift(1) & prices.gt(0) & prev.gt(0)
    arr = np.log(prices.to_numpy(dtype=np.float64) / prev.to_numpy(dtype=np.float64))
    arr[~valid.to_numpy()] = np.nan
    returns = pd.DataFrame(arr, index=dates, columns=prices.columns).iloc[1:].copy()
    meta = {
        "panel_path": str(panel_path), "panel_rows_read": int(len(panel)),
        "panel_dates": int(len(dates)), "panel_tickers": int(panel["secid"].nunique()),
        "return_dates": int(len(returns)), "return_observations": int(np.isfinite(returns.to_numpy()).sum()),
        "return_definition": "Adjacent panel-session log adjusted-close returns; both endpoints bar_available=1.",
        "no_fill_or_gap_bridging": True,
    }
    return returns, meta


def rolling_scale(returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    min_obs_fraction = 1.0  # complete windows: missing observations invalidate the window
    for ticker in returns.columns:
        s = returns[ticker]
        for window in WINDOWS:
            roll = s.rolling(window=window, min_periods=int(window * min_obs_fraction))
            std = roll.std(ddof=1)
            # Rolling median absolute deviation, unscaled.
            mad = roll.apply(lambda x: float(np.median(np.abs(x - np.median(x)))), raw=True)
            valid = std.notna() & mad.notna()
            if valid.any():
                block = pd.DataFrame({"tradedate": std.index[valid], "secid": ticker,
                                      "window_sessions": window, "rolling_std": std[valid].values,
                                      "rolling_mad": mad[valid].values})
                rows.append(block)
    if not rows:
        return pd.DataFrame(columns=["tradedate", "secid", "window_sessions", "rolling_std", "rolling_mad"])
    return pd.concat(rows, ignore_index=True)


def quantile_summary(x: pd.Series) -> dict:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if not len(x):
        return {"n": 0}
    return {"n": int(len(x)), "mean": float(x.mean()), "median": float(x.median()),
            "std": float(x.std(ddof=1)) if len(x) > 1 else np.nan,
            "q10": float(x.quantile(.10)), "q25": float(x.quantile(.25)),
            "q75": float(x.quantile(.75)), "q90": float(x.quantile(.90)),
            "min": float(x.min()), "max": float(x.max())}


def aggregate_distribution(roll: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for window in WINDOWS:
        sample = roll.loc[roll["window_sessions"] == window]
        for metric in ("rolling_std", "rolling_mad"):
            rows.append({"window_sessions": window, "metric": metric,
                         **quantile_summary(sample[metric])})
    return pd.DataFrame(rows)


def per_security_temporal(roll: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (ticker, window), sample in roll.groupby(["secid", "window_sessions"]):
        for metric in ("rolling_std", "rolling_mad"):
            x = sample[metric].dropna()
            if len(x):
                rows.append({"secid": ticker, "window_sessions": int(window), "metric": metric,
                             **quantile_summary(x), "time_iqr": float(x.quantile(.75)-x.quantile(.25)),
                             "time_range": float(x.max()-x.min())})
    return pd.DataFrame(rows)


def period_security_scale(roll: pd.DataFrame) -> pd.DataFrame:
    dates = pd.to_datetime(roll["tradedate"])
    rows = []
    for name, start, end in PERIODS:
        subset = roll.loc[(dates >= start) & (dates <= end)]
        for (ticker, window), sample in subset.groupby(["secid", "window_sessions"]):
            for metric in ("rolling_std", "rolling_mad"):
                x = sample[metric].dropna()
                if len(x):
                    rows.append({"period": name, "secid": ticker, "window_sessions": int(window),
                                 "metric": metric, "period_median": float(x.median()),
                                 "period_mean": float(x.mean()), "n_windows": int(len(x))})
    return pd.DataFrame(rows)


def rank_stability(period_stats: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (window, metric), sample in period_stats.groupby(["window_sessions", "metric"]):
        wide = sample.pivot(index="secid", columns="period", values="period_median")
        for i, p1 in enumerate([p[0] for p in PERIODS]):
            for p2 in [p[0] for p in PERIODS][i+1:]:
                pair = wide[[p1, p2]].dropna()
                if len(pair) >= 3:
                    rows.append({"window_sessions": int(window), "metric": metric,
                                 "period_1": p1, "period_2": p2, "n_common_securities": int(len(pair)),
                                 "spearman_rank_corr": float(pair[p1].corr(pair[p2], method="spearman")),
                                 "pearson_corr": float(pair[p1].corr(pair[p2], method="pearson"))})
    return pd.DataFrame(rows)


def write_report(path: Path, meta: dict, distribution: pd.DataFrame,
                 temporal: pd.DataFrame, stability: pd.DataFrame) -> None:
    lines = ["# EDA2 — Блок 5. Неоднородность масштаба и волатильности", "",
             "## Выборка", f"- Даты панели: {meta['panel_dates']:,}",
             f"- Бумаг: {meta['panel_tickers']:,}", f"- Наблюдений доходности: {meta['return_observations']:,}",
             f"- Период: {meta['return_dates']:,} panel sessions", "",
             "## Распределение rolling scale", "",
             "| Окно | Метрика | N | Median | Q10 | Q25 | Q75 | Q90 |",
             "|---:|---|---:|---:|---:|---:|---:|---:|"]
    for row in distribution.itertuples(index=False):
        vals = [row.median, row.q10, row.q25, row.q75, row.q90]
        formatted = [f"{v:.6g}" if pd.notna(v) else "NA" for v in vals]
        lines.append(f"| {row.window_sessions} | {row.metric} | {row.n} | " + " | ".join(formatted) + " |")
    lines += ["", "## Временная изменчивость внутри бумаги", 
              "Per-security temporal summaries (median, quantiles, temporal IQR/range) находятся в per_security_temporal_variability.csv.",
              "## Устойчивость относительного масштаба между периодами",
              "Rank correlations сравнивают медианный rolling scale каждой бумаги в двух периодах, по общим бумагам.",
              "", "| Окно | Метрика | Периоды | N | Spearman | Pearson |",
              "|---:|---|---|---:|---:|---:|"]
    for row in stability.itertuples(index=False):
        sp = f"{row.spearman_rank_corr:.5f}" if pd.notna(row.spearman_rank_corr) else "NA"
        pe = f"{row.pearson_corr:.5f}" if pd.notna(row.pearson_corr) else "NA"
        lines.append(f"| {row.window_sessions} | {row.metric} | {row.period_1} vs {row.period_2} | {row.n_common_securities} | {sp} | {pe} |")
    lines += ["", "## Ограничения", "- Rolling estimates require complete windows; no imputation or gap stitching.",
              "- MAD is unscaled median absolute deviation.",
              "- Rank correlations describe cross-period stability, not causal persistence or predictive utility.",
              "- The 2020–2026 period is incomplete.",
              "- No GARCH, forecasting, models, IC, feature selection or trading conclusions.",
              "", "## Outputs", "- rolling_scale_distribution_summary.csv",
              "- per_security_temporal_variability.csv", "- period_security_scale.csv",
              "- cross_period_rank_stability.csv", "- EDA2_BLOCK_05_REPORT.md"]
    path.write_text("\n".join(lines)+"\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.docs_dir.mkdir(parents=True, exist_ok=True)
    returns, meta = load_returns(args.panel)
    rolling = rolling_scale(returns)
    distribution = aggregate_distribution(rolling)
    temporal = per_security_temporal(rolling)
    periods = period_security_scale(rolling)
    stability = rank_stability(periods)

    rolling["tradedate"] = pd.to_datetime(rolling["tradedate"]).dt.strftime("%Y-%m-%d")
    rolling.to_csv(args.output_dir / "rolling_scale_by_security.csv", index=False)
    periods.to_csv(args.output_dir / "period_security_scale.csv", index=False)
    distribution.to_csv(args.docs_dir / "rolling_scale_distribution_summary.csv", index=False)
    temporal.to_csv(args.docs_dir / "per_security_temporal_variability.csv", index=False)
    periods.to_csv(args.docs_dir / "period_security_scale.csv", index=False)
    stability.to_csv(args.docs_dir / "cross_period_rank_stability.csv", index=False)
    meta.update({"created_at_utc": datetime.now(timezone.utc).isoformat(), "block": 5,
                 "windows_sessions": list(WINDOWS), "periods": [{"name": n, "start": s, "end": e} for n,s,e in PERIODS],
                 "min_periods_rule": "full window; no gaps or missing return observations within window",
                 "machine_outputs": ["rolling_scale_by_security.csv", "period_security_scale.csv", "run_metadata.json"],
                 "research_outputs": ["rolling_scale_distribution_summary.csv", "per_security_temporal_variability.csv",
                                    "period_security_scale.csv", "cross_period_rank_stability.csv", "EDA2_BLOCK_05_REPORT.md"]})
    (args.output_dir / "run_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(args.docs_dir / "EDA2_BLOCK_05_REPORT.md", meta, distribution, temporal, stability)
    print("EDA2 Block 5 completed.")
    print(f"Return observations: {meta['return_observations']:,}")
    print(f"Rolling records: {len(rolling):,}")
    print(f"Machine outputs: {args.output_dir}")
    print(f"Research outputs: {args.docs_dir}")


if __name__ == "__main__":
    main()
