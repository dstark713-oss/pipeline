from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_DIR = ROOT / "data" / "interim" / "aggressive_market_snapshot"
OUTPUT_DIR = ROOT / "data" / "interim" / "aggressive_hypothesis_confirmation"
REPORT_PATH = ROOT / "docs" / "aggressive_hypothesis_confirmation_report.md"
SNAPSHOT_SCRIPT = ROOT / "scripts" / "one_use" / "aggressive_market_snapshot" / "build_market_snapshot.py"
DB_PATH = ROOT / "data" / "processed" / "moex_daily_adjusted.sqlite"
HORIZONS = (3, 5, 10, 20)
NW_LAGS = {3: 2, 5: 4, 10: 9, 20: 19}


def args_parser():
    p = argparse.ArgumentParser(description="Historical confirmation tests for aggressive hypotheses.")
    p.add_argument("--snapshot", type=Path, default=SNAPSHOT_DIR / "market_snapshot.parquet")
    p.add_argument("--benchmark", type=Path, default=SNAPSHOT_DIR / "equal_weight_top50_benchmark.parquet")
    p.add_argument("--db", type=Path, default=DB_PATH)
    p.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    p.add_argument("--report", type=Path, default=REPORT_PATH)
    return p.parse_args()


def load_builder():
    spec = importlib.util.spec_from_file_location("aggressive_snapshot_builder", SNAPSHOT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import snapshot builder: {SNAPSHOT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_prices(db_path, start, end):
    builder = load_builder()
    daily = builder.load_adjusted_daily(db_path, start)
    daily = daily.loc[
        (daily.tradedate <= end)
        & ~daily.tradedate.between(builder.SUSPENSION_START, builder.SUSPENSION_END)
    ].copy()
    if daily.empty:
        raise RuntimeError("No adjusted bars found for the snapshot period.")
    return daily


def nw_mean(values, max_lag):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return (float(x.mean()) if n else np.nan), np.nan, np.nan
    mean = float(x.mean())
    residual = x - mean
    long_run = float(np.dot(residual, residual) / n)
    for lag in range(1, min(max_lag, n - 1) + 1):
        weight = 1.0 - lag / (max_lag + 1.0)
        gamma = float(np.dot(residual[lag:], residual[:-lag]) / n)
        long_run += 2.0 * weight * gamma
    se = float(np.sqrt(max(long_run, 0.0) / n))
    return mean, se, mean / se if se > 0 else np.nan


def add_flags(snapshot):
    p = snapshot.copy()
    for col, out in [
        ("return_5d", "q_return_5d"),
        ("rs_5d", "q_rs_5d"),
        ("rs_20d", "q_rs_20d"),
        ("realized_vol_20d_ann", "q_vol_20d"),
    ]:
        p[out] = p.groupby("tradedate")[col].rank(pct=True, method="average")
    # Ex-ante fixed definitions, evaluated within each date's PIT TOP50.
    p["H1_impulse"] = (p.q_return_5d >= 0.80) & (p.return_5d > 0)
    p["H2_high_rs20"] = (p.q_rs_20d >= 0.80) & (p.rs_20d > 0)
    p["H3_aligned_positive"] = (p.return_5d > 0) & (p.return_20d > 0)
    p["H4_high_rs5"] = (p.q_rs_5d >= 0.80) & (p.rs_5d > 0)
    p["H4_low_vol_high_rs"] = p["H4_high_rs5"] & (p.q_vol_20d <= 1 / 3)
    p["H4_high_vol_high_rs"] = p["H4_high_rs5"] & (p.q_vol_20d >= 2 / 3)
    p["H5_persistent_weakness"] = (
        (p.q_rs_5d <= 0.20) & (p.q_rs_20d <= 0.20)
        & (p.rs_5d < 0) & (p.rs_20d < 0)
    )
    return p


def future_outcomes(daily, benchmark, calendar):
    close = daily.pivot(index="tradedate", columns="secid", values="adjusted_close").reindex(calendar)
    bench_daily = benchmark.set_index("tradedate").benchmark_return_1d.reindex(calendar)
    frames = []
    for h in HORIZONS:
        ticker = close.shift(-h).div(close).sub(1).stack().rename("ticker_forward").reset_index()
        ticker.columns = ["tradedate", "secid", "ticker_forward"]
        # At date t, compound benchmark returns t+1 through t+h.
        b = pd.Series(index=calendar, dtype=float)
        values = bench_daily.to_numpy(dtype=float)
        out = np.full(len(values), np.nan)
        for i in range(len(values) - h):
            window = values[i + 1:i + h + 1]
            if len(window) == h and np.isfinite(window).all():
                out[i] = np.prod(1.0 + window) - 1.0
        b.loc[:] = out
        b = b.rename("benchmark_forward").reset_index()
        b.columns = ["tradedate", "benchmark_forward"]
        part = ticker.merge(b, on="tradedate", how="left")
        part["horizon"] = h
        part["forward_rs"] = part.ticker_forward - part.benchmark_forward
        frames.append(part)
    return pd.concat(frames, ignore_index=True), close


def daily_spreads(panel, future, flag):
    left = panel[["tradedate", "secid", flag]]
    merged = left.merge(
        future[["tradedate", "secid", "horizon", "forward_rs"]],
        on=["tradedate", "secid"], how="left", validate="one_to_many"
    )
    records = []
    for h, data in merged.groupby("horizon"):
        for date, day in data.groupby("tradedate"):
            signal = day.loc[day[flag].fillna(False), "forward_rs"].dropna()
            control = day.loc[~day[flag].fillna(False), "forward_rs"].dropna()
            if len(signal) < 2 or len(control) < 2:
                continue
            records.append({
                "hypothesis": flag, "horizon": int(h), "tradedate": date,
                "signal_n": len(signal), "control_n": len(control),
                "signal_mean_forward_rs": signal.mean(),
                "control_mean_forward_rs": control.mean(),
                "daily_mean_difference": signal.mean() - control.mean(),
                "signal_hit_rate": (signal > 0).mean(),
            })
    return pd.DataFrame(records)


def block_bootstrap_ci(values, block_length, repetitions=1000, seed=713):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < max(10, block_length * 2):
        return np.nan, np.nan
    rng = np.random.default_rng(seed + block_length + n)
    estimates = np.empty(repetitions)
    blocks_needed = int(np.ceil(n / block_length))
    for i in range(repetitions):
        starts = rng.integers(0, n, size=blocks_needed)
        sample = np.concatenate([
            x[(start + np.arange(block_length)) % n] for start in starts
        ])[:n]
        estimates[i] = sample.mean()
    return tuple(np.quantile(estimates, [0.025, 0.975]))


def normal_two_sided_p(t_stat):
    if not np.isfinite(t_stat):
        return np.nan
    return math.erfc(abs(float(t_stat)) / math.sqrt(2.0))


def benjamini_hochberg(p_values):
    p = np.asarray(p_values, dtype=float)
    q = np.full(len(p), np.nan)
    valid = np.flatnonzero(np.isfinite(p))
    if not len(valid):
        return q
    order = valid[np.argsort(p[valid])]
    ranked = p[order] * len(order) / np.arange(1, len(order) + 1)
    adjusted = np.minimum.accumulate(ranked[::-1])[::-1]
    q[order] = np.minimum(adjusted, 1.0)
    return q


def summarize(spreads):
    rows = []
    for (hypothesis, horizon), g in spreads.groupby(["hypothesis", "horizon"]):
        mean, se, t = nw_mean(g.daily_mean_difference, NW_LAGS[int(horizon)])
        boot_low, boot_high = block_bootstrap_ci(
            g.sort_values("tradedate").daily_mean_difference,
            block_length=int(horizon),
        )
        rows.append({
            "hypothesis": hypothesis, "horizon": int(horizon),
            "n_dates": g.tradedate.nunique(),
            "mean_daily_difference": mean, "newey_west_se": se, "newey_west_t": t,
            "nw_ci95_low": mean - 1.96 * se if np.isfinite(se) else np.nan,
            "nw_ci95_high": mean + 1.96 * se if np.isfinite(se) else np.nan,
            "block_bootstrap_ci95_low": boot_low,
            "block_bootstrap_ci95_high": boot_high,
            "normal_approx_p": normal_two_sided_p(t),
            "mean_signal_hit_rate": g.signal_hit_rate.mean(),
            "mean_signal_n": g.signal_n.mean(), "mean_control_n": g.control_n.mean(),
        })
    result = pd.DataFrame(rows)
    result["bh_q_value"] = benjamini_hochberg(result["normal_approx_p"].to_numpy())
    return result


def stability_table(spreads):
    x = spreads.copy()
    years = pd.to_datetime(x.tradedate).dt.year
    x["period"] = np.select(
        [years <= 2012, years <= 2019],
        ["through_2012", "2013_2019"], default="2020_plus"
    )
    rows = []
    for (hypothesis, horizon, period), g in x.groupby(["hypothesis", "horizon", "period"]):
        mean, se, t = nw_mean(g.daily_mean_difference, NW_LAGS[int(horizon)])
        rows.append({
            "hypothesis": hypothesis, "horizon": int(horizon), "period": period,
            "n_dates": g.tradedate.nunique(), "mean_daily_difference": mean,
            "newey_west_t": t, "ci95_low": mean - 1.96 * se if np.isfinite(se) else np.nan,
            "ci95_high": mean + 1.96 * se if np.isfinite(se) else np.nan,
        })
    return pd.DataFrame(rows)


def h1_path_metrics(panel, close, calendar):
    logret = np.log(close.div(close.shift(1)))
    pos = {d: i for i, d in enumerate(calendar)}
    rows = []
    selected = panel.loc[panel.H1_impulse]
    for r in selected[["tradedate", "secid"]].itertuples(index=False):
        i = pos.get(r.tradedate)
        if i is None or i < 4 or r.secid not in logret:
            continue
        path = logret.iloc[i - 4:i + 1][r.secid].dropna().to_numpy()
        if len(path) != 5:
            continue
        positive = path[path > 0].sum()
        absolute = np.abs(path).sum()
        rows.append({
            "tradedate": r.tradedate, "secid": r.secid,
            "largest_abs_day_share": np.max(np.abs(path)) / absolute if absolute else np.nan,
            "largest_positive_day_share": np.max(path[path > 0]) / positive if positive > 0 else np.nan,
            "positive_days": int((path > 0).sum()), "negative_days": int((path < 0).sum()),
            "gross_positive_log_move": positive, "gross_negative_log_move": path[path < 0].sum(),
        })
    return pd.DataFrame(rows)


def h4_metrics(panel):
    daily_rho = []
    high_vol_shares = []
    for date, day in panel.groupby("tradedate"):
        clean = day[["rs_5d", "realized_vol_20d_ann"]].dropna()
        if len(clean) >= 10 and clean.nunique().min() > 1:
            daily_rho.append(clean.rs_5d.rank().corr(clean.realized_vol_20d_ann.rank()))
        top = day.loc[day.H4_high_rs5]
        if len(top):
            high_vol_shares.append((date, (top.q_vol_20d >= 2 / 3).mean()))
    values = [v for v in daily_rho if pd.notna(v)]
    shares = [v for _, v in high_vol_shares]
    metrics = pd.DataFrame([{
        "n_dates_spearman": len(values),
        "median_daily_spearman_rs5_vs_vol20": np.median(values) if values else np.nan,
        "mean_daily_spearman_rs5_vs_vol20": np.mean(values) if values else np.nan,
        "mean_high_vol_share_within_top_rs5": np.mean(shares) if shares else np.nan,
    }])
    daily = pd.DataFrame(high_vol_shares, columns=["tradedate", "high_vol_share_within_top_rs5"])
    return metrics, daily


def write_report(path, panel, summary, stability, impulse, h4):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Aggressive Agent: Hypothesis Confirmation Report", "",
        f"- Period: **{panel.tradedate.min().date()} to {panel.tradedate.max().date()}**",
        f"- PIT TOP50 rows with available bars: **{len(panel):,}**",
        f"- Unique securities: **{panel.secid.nunique():,}**",
        "- Benchmark: daily rebalanced equal-weight PIT TOP50.",
        "- Signal thresholds: cross-sectional quintiles by date, fixed in code before outcomes were examined.",
        "- Outcome: forward ticker return minus compounded forward benchmark return over 3, 5, 10, and 20 sessions.",
        "- Inference: Newey-West standard errors on daily signal-minus-control spreads; lag = horizon - 1.",
        "- This is historical confirmation evidence only. No BUY/SELL, position sizing, strategy return, or decision is produced.",
        "", "## Fixed hypothesis definitions", "",
        "1. **H1 impulse concentration:** positive 5-session return in the top cross-sectional quintile.",
        "2. **H2 relative-strength persistence:** positive 20-session RS in the top cross-sectional quintile.",
        "3. **H3 aligned momentum:** positive absolute returns over both 5 and 20 sessions.",
        "4. **H4 volatility explanation:** positive 5-session RS in the top cross-sectional quintile; inspect its association with 20-session realized volatility.",
        "5. **H5 persistent weakness:** negative 5-session and 20-session RS, both in the bottom cross-sectional quintile.",
        "", "## Main results", "",
        "| Hypothesis | Horizon | Mean daily spread | NW 95% CI | Block-bootstrap 95% CI | NW t | BH q | Dates | Hit rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary.sort_values(["hypothesis", "horizon"]).itertuples(index=False):
        lines.append(
            f"| {r.hypothesis} | {r.horizon} | {r.mean_daily_difference:.3%} | "
            f"[{r.nw_ci95_low:.3%}, {r.nw_ci95_high:.3%}] | "
            f"[{r.block_bootstrap_ci95_low:.3%}, {r.block_bootstrap_ci95_high:.3%}] | "
            f"{r.newey_west_t:.2f} | {r.bh_q_value:.3f} | {r.n_dates:,} | {r.mean_signal_hit_rate:.1%} |"
        )
    lines += ["", "## H1 path concentration", ""]
    if len(impulse):
        lines += [
            f"- Complete 5-session signal paths: **{len(impulse):,}**.",
            f"- Median largest absolute day / total absolute movement: **{impulse.largest_abs_day_share.median():.1%}**.",
            f"- Median largest positive day / total positive movement: **{impulse.largest_positive_day_share.median():.1%}**.",
            f"- Mean number of positive days: **{impulse.positive_days.mean():.2f} of 5**.",
        ]
    else:
        lines.append("- No complete impulse paths available.")
    lines += ["", "## H4 volatility diagnostics", ""]
    if len(h4):
        r = h4.iloc[0]
        lines += [
            f"- Median daily Spearman correlation, RS5 vs realized volatility 20D: **{r.median_daily_spearman_rs5_vs_vol20:.3f}**.",
            f"- Mean high-volatility share within top-RS5 group: **{r.mean_high_vol_share_within_top_rs5:.1%}**.",
        ]
    lines += [
        "", "## Stability by historical period", "",
        "| Hypothesis | Horizon | Period | Mean daily spread | 95% CI | NW t | Dates |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for r in stability.sort_values(["hypothesis", "horizon", "period"]).itertuples(index=False):
        lines.append(
            f"| {r.hypothesis} | {r.horizon} | {r.period} | {r.mean_daily_difference:.3%} | "
            f"[{r.ci95_low:.3%}, {r.ci95_high:.3%}] | {r.newey_west_t:.2f} | {r.n_dates:,} |"
        )
    lines += [
        "", "## Interpretation limits", "",
        "- Positive spread means the signal group outperformed the same-date complement on forward relative return. It is not a strategy return.",
        "- Newey-West inference addresses serial correlation in date-level spreads, but not every universe, data-quality, or selection issue.",
        "- Forward windows overlap; inference remains approximate.",
        "- H1 and H4 diagnostics are descriptive and do not establish causal mechanisms.",
        "- The summary CSV includes a Benjamini-Hochberg q-value across all reported hypothesis/horizon tests. P-values use a normal approximation to the Newey-West t-statistic and are screening diagnostics, not exact finite-sample inference.",
        "- Block-bootstrap confidence intervals resample circular date blocks with block length equal to the forward horizon; they are an additional robustness interval, not a substitute for the Newey-West interval.",
        "- Review effect size, confidence interval, sample size, and subperiod stability together. Do not treat one p-value as a verdict.",
        "", "## Local machine-readable outputs", "",
        "All CSV files are written to data/interim/aggressive_hypothesis_confirmation/.",
        "- hypothesis_summary.csv",
        "- period_stability.csv",
        "- daily_group_differences.csv",
        "- impulse_path_metrics.csv",
        "- h4_volatility_diagnostics.csv",
        "- h4_volatility_daily.csv", "",
    ]
    path.write_text("\\n".join(lines), encoding="utf-8")


def main():
    args = args_parser()
    for p in (args.snapshot, args.benchmark, args.db, SNAPSHOT_SCRIPT):
        if not p.is_file():
            raise FileNotFoundError(f"Required input not found: {p}")

    print("Loading snapshot and benchmark...")
    snapshot = pd.read_parquet(args.snapshot)
    benchmark = pd.read_parquet(args.benchmark)
    snapshot["tradedate"] = pd.to_datetime(snapshot.tradedate).dt.normalize()
    benchmark["tradedate"] = pd.to_datetime(benchmark.tradedate).dt.normalize()
    required = {
        "tradedate", "secid", "bar_available", "return_5d", "return_20d",
        "rs_5d", "rs_20d", "realized_vol_20d_ann",
    }
    missing = required - set(snapshot.columns)
    if missing:
        raise RuntimeError(f"Snapshot is missing required columns: {sorted(missing)}")
    snapshot = snapshot.loc[snapshot.bar_available.eq(1)].copy()

    print("Loading adjusted bars and calculating forward outcomes...")
    daily = load_prices(args.db, snapshot.tradedate.min() - pd.Timedelta(days=500), snapshot.tradedate.max())
    calendar = pd.DatetimeIndex(daily.tradedate.drop_duplicates().sort_values(), name="tradedate")
    future, close = future_outcomes(daily, benchmark, calendar)
    panel = add_flags(snapshot)
    print("Calculating date-level signal/control comparisons...")
    flags = ["H1_impulse", "H2_high_rs20", "H3_aligned_positive", "H4_high_rs5", "H5_persistent_weakness"]
    frames = [daily_spreads(panel, future, flag) for flag in flags]
    spreads = pd.concat([x for x in frames if not x.empty], ignore_index=True)
    if spreads.empty:
        raise RuntimeError("No valid comparisons. Check the PIT universe and forward-data coverage.")

    summary = summarize(spreads)
    stability = stability_table(spreads)
    impulse = h1_path_metrics(panel, close, calendar)
    h4, h4_daily = h4_metrics(panel)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "hypothesis_summary.csv": summary,
        "period_stability.csv": stability,
        "daily_group_differences.csv": spreads,
        "impulse_path_metrics.csv": impulse,
        "h4_volatility_diagnostics.csv": h4,
        "h4_volatility_daily.csv": h4_daily,
    }
    for name, frame in outputs.items():
        frame.to_csv(args.output_dir / name, index=False, encoding="utf-8-sig")

    write_report(args.report, panel, summary, stability, impulse, h4)
    print("\\nHYPOTHESIS CONFIRMATION SUMMARY")
    print("=" * 72)
    print(summary.to_string(index=False, float_format=lambda x: f"{x:+.4f}"))
    print("=" * 72)
    print(f"Markdown report: {args.report}")
    print(f"CSV outputs:     {args.output_dir}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
