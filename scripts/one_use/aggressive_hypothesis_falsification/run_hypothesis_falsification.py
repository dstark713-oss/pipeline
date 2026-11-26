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
OUTPUT_DIR = ROOT / "data" / "interim" / "aggressive_hypothesis_falsification"
REPORT_PATH = ROOT / "docs" / "aggressive_hypothesis_falsification_report.md"
SNAPSHOT_SCRIPT = ROOT / "scripts" / "one_use" / "aggressive_market_snapshot" / "build_market_snapshot.py"
DB_PATH = ROOT / "data" / "processed" / "moex_daily_adjusted.sqlite"
HORIZONS = (3, 5, 10, 20)
BOOTSTRAP_REPS = 1500
SEED = 713


def parse_args():
    p = argparse.ArgumentParser(description="Falsification tests for aggressive market hypotheses.")
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
        raise RuntimeError("No adjusted bars found.")
    return daily


def normal_p(t):
    return math.erfc(abs(float(t)) / math.sqrt(2.0)) if np.isfinite(t) else np.nan


def nw_mean(values, max_lag):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return (float(x.mean()) if n else np.nan), np.nan, np.nan
    mean = float(x.mean())
    e = x - mean
    lrv = float(np.dot(e, e) / n)
    for lag in range(1, min(max_lag, n - 1) + 1):
        gamma = float(np.dot(e[lag:], e[:-lag]) / n)
        lrv += 2.0 * (1.0 - lag / (max_lag + 1.0)) * gamma
    se = float(np.sqrt(max(lrv, 0.0) / n))
    return mean, se, mean / se if se > 0 else np.nan


def circular_block_ci(values, block_length, repetitions=BOOTSTRAP_REPS, seed=SEED):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < max(20, 2 * block_length):
        return np.nan, np.nan
    rng = np.random.default_rng(seed + n + block_length)
    blocks = int(np.ceil(n / block_length))
    estimates = np.empty(repetitions)
    offsets = np.arange(block_length)
    for b in range(repetitions):
        starts = rng.integers(0, n, size=blocks)
        sample = np.concatenate([x[(s + offsets) % n] for s in starts])[:n]
        estimates[b] = sample.mean()
    return tuple(np.quantile(estimates, [0.025, 0.975]))


def bh_adjust(p_values):
    p = np.asarray(p_values, dtype=float)
    q = np.full(len(p), np.nan)
    valid = np.flatnonzero(np.isfinite(p))
    if not len(valid):
        return q
    order = valid[np.argsort(p[valid])]
    raw = p[order] * len(order) / np.arange(1, len(order) + 1)
    q[order] = np.minimum(1.0, np.minimum.accumulate(raw[::-1])[::-1])
    return q


def future_outcomes(daily, benchmark, calendar):
    # Explicit global session calendar: row i+h is exactly h adjusted-market
    # sessions after row i. Missing ticker bars stay NaN; never jump to the
    # next available ticker observation and never forward-fill prices.
    close = (
        daily.pivot(index="tradedate", columns="secid", values="adjusted_close")
        .reindex(calendar)
        .sort_index()
    )
    if close.index.has_duplicates() or not close.index.equals(calendar):
        raise RuntimeError("Ticker close matrix is not aligned to the global session calendar.")
    bench = (
        benchmark.drop_duplicates("tradedate")
        .set_index("tradedate")["benchmark_return_1d"]
        .reindex(calendar)
    )
    frames = []
    for h in HORIZONS:
        future_close = close.shift(-h)
        ticker_ret = future_close.div(close).sub(1.0)
        ticker_ret = ticker_ret.where(close.notna() & future_close.notna())
        ticker_long = (
            ticker_ret.rename_axis(index="tradedate", columns="secid")
            .stack()
            .rename("ticker_forward")
            .reset_index()
        )
        b = pd.Series(np.nan, index=calendar, dtype=float)
        values = bench.to_numpy(dtype=float)
        out = np.full(len(values), np.nan)
        for i in range(len(values) - h):
            window = values[i + 1:i + h + 1]
            if np.isfinite(window).all():
                out[i] = np.prod(1.0 + window) - 1.0
        b.iloc[:] = out
        b.name = "benchmark_forward"
        part = ticker_long.merge(b.reset_index(), on="tradedate", how="left", validate="many_to_one")
        part["horizon"] = h
        part["forward_rs"] = part["ticker_forward"] - part["benchmark_forward"]
        frames.append(part)
    return pd.concat(frames, ignore_index=True), close


def add_cross_sectional_features(snapshot):
    p = snapshot.copy()
    p["tradedate"] = pd.to_datetime(p.tradedate).dt.normalize()
    for col, out in [
        ("return_5d", "q_return_5d"),
        ("rs_5d", "q_rs_5d"),
        ("rs_20d", "q_rs_20d"),
        ("return_20d", "q_return_20d"),
    ]:
        p[out] = p.groupby("tradedate")[col].rank(pct=True, method="average")
    p["H1_impulse"] = (p.q_return_5d >= 0.80) & (p.return_5d > 0)
    p["H2_high_rs20"] = (p.q_rs_20d >= 0.80) & (p.rs_20d > 0)
    p["H3_aligned_positive"] = (p.return_5d > 0) & (p.return_20d > 0)
    p["valid_rs_pair"] = p.rs_5d.notna() & p.rs_20d.notna()
    p["H5_persistent_weakness"] = (
        p.valid_rs_pair & (p.q_rs_5d <= 0.20) & (p.q_rs_20d <= 0.20)
        & (p.rs_5d < 0) & (p.rs_20d < 0)
    )
    p["rs5_quintile"] = np.ceil(p.q_rs_5d * 5).clip(1, 5)
    p["rs20_top"] = p.q_rs_20d >= 0.80
    p["rs5_only_weak"] = (p.q_rs_5d <= 0.20) & (p.q_rs_20d > 0.20)
    p["rs20_only_weak"] = (p.q_rs_20d <= 0.20) & (p.q_rs_5d > 0.20)
    return p


def daily_group_contrast(panel, future, group_col, hypothesis, group_value=True, control_col=None, control_value=None):
    cols = ["tradedate", "secid", group_col]
    if control_col:
        cols.append(control_col)
    merged = panel[cols].merge(
        future[["tradedate", "secid", "horizon", "forward_rs"]],
        on=["tradedate", "secid"], how="left", validate="one_to_many"
    )
    rows = []
    for (h, date), day in merged.groupby(["horizon", "tradedate"], sort=True):
        sig_mask = day[group_col].eq(group_value)
        if control_col:
            ctl_mask = day[control_col].eq(control_value)
        else:
            ctl_mask = ~sig_mask
        sig = day.loc[sig_mask, "forward_rs"].dropna()
        ctl = day.loc[ctl_mask, "forward_rs"].dropna()
        if len(sig) < 2 or len(ctl) < 2:
            continue
        rows.append({
            "module": hypothesis, "horizon": int(h), "tradedate": date,
            "signal_n": len(sig), "control_n": len(ctl),
            "signal_mean": sig.mean(), "control_mean": ctl.mean(),
            "daily_spread": sig.mean() - ctl.mean(),
            "signal_hit_rate": (sig > 0).mean(),
            "signal_negative_rate": (sig < 0).mean(),
        })
    return pd.DataFrame(rows)


def h1_concentration(panel, close, calendar):
    logret = np.log(close.div(close.shift(1)))
    positions = {d: i for i, d in enumerate(calendar)}
    records = []
    for r in panel.loc[panel.H1_impulse, ["tradedate", "secid"]].itertuples(index=False):
        i = positions.get(r.tradedate)
        if i is None or i < 4 or r.secid not in logret.columns:
            continue
        path = logret.iloc[i - 4:i + 1][r.secid].to_numpy(dtype=float)
        if len(path) != 5 or not np.isfinite(path).all():
            continue
        gross_abs = np.abs(path).sum()
        gross_pos = path[path > 0].sum()
        records.append({
            "tradedate": r.tradedate, "secid": r.secid,
            "concentration_abs": np.max(np.abs(path)) / gross_abs if gross_abs > 0 else np.nan,
            "concentration_positive": np.max(path[path > 0]) / gross_pos if gross_pos > 0 else np.nan,
            "positive_days": int((path > 0).sum()),
            "net_log_return_5d": float(path.sum()),
        })
    metrics = pd.DataFrame(records)
    if metrics.empty:
        raise RuntimeError("No complete five-session paths for H1.")
    metrics["concentration_q"] = metrics.groupby("tradedate").concentration_abs.rank(pct=True)
    metrics["high_concentration"] = metrics.concentration_q >= 0.50
    metrics["low_concentration"] = metrics.concentration_q < 0.50
    return metrics


def h1_daily_spreads(metrics, future):
    x = metrics[["tradedate", "secid", "high_concentration", "low_concentration"]].merge(
        future[["tradedate", "secid", "horizon", "forward_rs"]],
        on=["tradedate", "secid"], how="left", validate="one_to_many"
    )
    rows = []
    for (h, date), day in x.groupby(["horizon", "tradedate"], sort=True):
        hi = day.loc[day.high_concentration, "forward_rs"].dropna()
        lo = day.loc[day.low_concentration, "forward_rs"].dropna()
        if len(hi) < 2 or len(lo) < 2:
            continue
        rows.append({
            "module": "F4_H1_concentrated_minus_distributed",
            "horizon": int(h), "tradedate": date,
            "signal_n": len(hi), "control_n": len(lo),
            "signal_mean": hi.mean(), "control_mean": lo.mean(),
            "daily_spread": hi.mean() - lo.mean(),
            "signal_hit_rate": (hi > 0).mean(),
            "signal_negative_rate": (hi < 0).mean(),
        })
    return pd.DataFrame(rows)


def h2_conditional_tests(panel, future):
    # RS20 and absolute return20 are not separately identifiable cross-sectionally:
    # RS20 = return20 - same-date benchmark20, so their within-date ranks are identical.
    # Therefore the incremental test controls RS5 and absolute return5, but does
    # not include return20 alongside RS20 (perfect date-level collinearity).
    x = panel[[
        "tradedate", "secid", "rs5_quintile", "rs20_top",
        "rs_20d", "rs_5d", "return_5d",
    ]].merge(
        future[["tradedate", "secid", "horizon", "forward_rs"]],
        on=["tradedate", "secid"], how="left", validate="one_to_many"
    )
    contrasts = []
    regressions = []
    for (h, date), day in x.groupby(["horizon", "tradedate"], sort=True):
        # Matched within RS5 quintile: top-quintile RS20 versus the remainder
        # of the same RS5 quintile. Aggregate stratum spreads with equal weight.
        stratum_spreads = []
        n_signal = n_control = 0
        for _, stratum in day.groupby("rs5_quintile"):
            a = stratum.loc[stratum.rs20_top, "forward_rs"].dropna()
            b = stratum.loc[~stratum.rs20_top, "forward_rs"].dropna()
            if len(a) >= 1 and len(b) >= 1:
                stratum_spreads.append(float(a.mean() - b.mean()))
                n_signal += len(a)
                n_control += len(b)
        if stratum_spreads:
            contrasts.append({
                "module": "F1_H2_RS20_incremental_within_RS5",
                "horizon": int(h), "tradedate": date,
                "signal_n": n_signal, "control_n": n_control,
                "signal_mean": np.nan, "control_mean": np.nan,
                "daily_spread": float(np.mean(stratum_spreads)),
                "signal_hit_rate": np.nan, "signal_negative_rate": np.nan,
            })
        # Date-wise cross-sectional OLS. Standardize predictors within date;
        # coefficients are then comparable as relative cross-sectional effects.
        cols = ["rs_20d", "rs_5d", "return_5d", "forward_rs"]
        d = day[cols].replace([np.inf, -np.inf], np.nan).dropna()
        if len(d) < 12:
            continue
        z = d[cols[:3]].apply(
            lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) > 0 else np.nan
        )
        valid = z.notna().all(axis=1)
        if valid.sum() < 12:
            continue
        design = np.column_stack([np.ones(valid.sum()), z.loc[valid].to_numpy()])
        beta = np.linalg.lstsq(design, d.loc[valid, "forward_rs"].to_numpy(), rcond=None)[0]
        regressions.append({
            "module": "F1_H2_RS20_conditional_regression",
            "horizon": int(h), "tradedate": date,
            "n": int(valid.sum()), "beta_rs20": beta[1],
            "beta_rs5": beta[2], "beta_return5": beta[3],
        })
    return pd.DataFrame(contrasts), pd.DataFrame(regressions)


def h3_quadrants(panel, future):
    x = panel[["tradedate", "secid", "return_5d", "return_20d"]].copy()
    valid = x.return_5d.notna() & x.return_20d.notna()
    x["quadrant"] = np.select(
        [
            valid & (x.return_5d > 0) & (x.return_20d > 0),
            valid & (x.return_5d > 0) & (x.return_20d <= 0),
            valid & (x.return_5d <= 0) & (x.return_20d > 0),
            valid & (x.return_5d <= 0) & (x.return_20d <= 0),
        ],
        ["positive_both", "positive_5_only", "positive_20_only", "negative_both"],
        default="",
    )
    x.loc[~valid, "quadrant"] = np.nan
    x = x.merge(
        future[["tradedate", "secid", "horizon", "forward_rs"]],
        on=["tradedate", "secid"], how="left", validate="one_to_many"
    )
    rows = []
    for (h, date), day in x.groupby(["horizon", "tradedate"], sort=True):
        means = day.groupby("quadrant").forward_rs.mean()
        counts = day.groupby("quadrant").forward_rs.count()
        for quadrant in ["positive_both", "positive_5_only", "positive_20_only", "negative_both"]:
            rows.append({
                "horizon": int(h), "tradedate": date, "quadrant": quadrant,
                "n": int(counts.get(quadrant, 0)), "mean_forward_rs": means.get(quadrant, np.nan),
            })
    # Daily continuous interaction model: forward RS ~ z(return5) + z(return20)
    # + interaction. Interaction coefficient tests whether alignment adds value
    # beyond the two individual horizons.
    interaction = []
    for (h, date), day in x.groupby(["horizon", "tradedate"], sort=True):
        d = day[["return_5d", "return_20d", "forward_rs"]].replace(
            [np.inf, -np.inf], np.nan
        ).dropna()
        if len(d) < 12:
            continue
        z5 = (d.return_5d - d.return_5d.mean()) / d.return_5d.std(ddof=0)
        z20 = (d.return_20d - d.return_20d.mean()) / d.return_20d.std(ddof=0)
        if not np.isfinite(z5).all() or not np.isfinite(z20).all():
            continue
        design = np.column_stack([np.ones(len(d)), z5, z20, z5 * z20])
        beta = np.linalg.lstsq(design, d.forward_rs.to_numpy(), rcond=None)[0]
        interaction.append({
            "horizon": int(h), "tradedate": date, "n": len(d),
            "beta_return5": beta[1], "beta_return20": beta[2],
            "beta_interaction": beta[3],
        })
    return pd.DataFrame(rows), pd.DataFrame(interaction)


def h5_weakness_tests(panel, future):
    x = panel[[
        "tradedate", "secid", "H5_persistent_weakness",
        "rs5_only_weak", "rs20_only_weak", "valid_rs_pair",
    ]].merge(
        future[["tradedate", "secid", "horizon", "forward_rs"]],
        on=["tradedate", "secid"], how="left", validate="one_to_many"
    )
    rows = []
    for (h, date), day in x.groupby(["horizon", "tradedate"], sort=True):
        both = day.loc[day.H5_persistent_weakness, "forward_rs"].dropna()
        one5 = day.loc[day.rs5_only_weak, "forward_rs"].dropna()
        one20 = day.loc[day.rs20_only_weak, "forward_rs"].dropna()
        rest = day.loc[
            day.valid_rs_pair
            & ~(day.H5_persistent_weakness | day.rs5_only_weak | day.rs20_only_weak),
            "forward_rs"
        ].dropna()
        for label, control in [("vs_RS5_only", one5), ("vs_RS20_only", one20), ("vs_other", rest)]:
            if len(both) >= 2 and len(control) >= 2:
                rows.append({
                    "module": "F3_H5_persistent_weakness",
                    "contrast": label, "horizon": int(h), "tradedate": date,
                    "signal_n": len(both), "control_n": len(control),
                    "signal_mean": both.mean(), "control_mean": control.mean(),
                    "daily_spread": both.mean() - control.mean(),
                    "signal_hit_rate": (both > 0).mean(),
                    "signal_negative_rate": (both < 0).mean(),
                })
    return pd.DataFrame(rows)


def summarize_spreads(spreads, keys):
    rows = []
    for group_key, g in spreads.groupby(keys, dropna=False, sort=True):
        if not isinstance(group_key, tuple):
            group_key = (group_key,)
        mean, se, t = nw_mean(g.sort_values("tradedate").daily_spread, max(HORIZONS) - 1)
        lo, hi = circular_block_ci(g.sort_values("tradedate").daily_spread, block_length=5)
        row = dict(zip(keys, group_key))
        row.update({
            "n_dates": g.tradedate.nunique(), "mean_daily_spread": mean,
            "nw_se": se, "nw_t": t,
            "nw_ci_low": mean - 1.96 * se if np.isfinite(se) else np.nan,
            "nw_ci_high": mean + 1.96 * se if np.isfinite(se) else np.nan,
            "block_ci_low": lo, "block_ci_high": hi,
            "normal_p": normal_p(t),
            "mean_signal_hit_rate": g.signal_hit_rate.mean(),
            "mean_signal_negative_rate": g.signal_negative_rate.mean(),
        })
        rows.append(row)
    result = pd.DataFrame(rows)
    if "normal_p" in result:
        result["bh_q"] = bh_adjust(result.normal_p.to_numpy())
    return result


def summarize_date_series(frame, value_cols, group_cols):
    rows = []
    for group_key, g in frame.groupby(group_cols, sort=True):
        if not isinstance(group_key, tuple):
            group_key = (group_key,)
        for value_col in value_cols:
            mean, se, t = nw_mean(g.sort_values("tradedate")[value_col], max(HORIZONS) - 1)
            lo, hi = circular_block_ci(g.sort_values("tradedate")[value_col], block_length=5)
            row = dict(zip(group_cols, group_key))
            row.update({
                "coefficient": value_col, "mean": mean, "nw_se": se, "nw_t": t,
                "nw_ci_low": mean - 1.96 * se if np.isfinite(se) else np.nan,
                "nw_ci_high": mean + 1.96 * se if np.isfinite(se) else np.nan,
                "block_ci_low": lo, "block_ci_high": hi,
                "n_dates": g.tradedate.nunique(), "normal_p": normal_p(t),
            })
            rows.append(row)
    out = pd.DataFrame(rows)
    if len(out):
        out["bh_q"] = bh_adjust(out.normal_p.to_numpy())
    return out


def add_periods(frame):
    x = frame.copy()
    year = pd.to_datetime(x.tradedate).dt.year
    x["period"] = np.select(
        [year <= 2012, year <= 2019],
        ["through_2012", "2013_2019"], default="2020_plus"
    )
    return x


def write_report(path, panel, future, f1, f1_reg, f1_reg_summary, f2, f2_interaction, f2_int_summary, f2_quadrant_summary, f3, f3_ex_summary, f4, summaries):
    path.parent.mkdir(parents=True, exist_ok=True)
    calendar_min = panel.tradedate.min().date()
    calendar_max = panel.tradedate.max().date()
    valid_future = future.forward_rs.notna().mean()
    lines = [
        "# Aggressive Agent: Hypothesis Falsification Report", "",
        f"- Signal sample: **{calendar_min} to {calendar_max}**",
        f"- PIT TOP50 rows with current bars: **{len(panel):,}**",
        f"- Securities: **{panel.secid.nunique():,}**",
        f"- Non-missing ticker/benchmark forward-RS observations across all horizons: **{valid_future:.1%}**",
        "- Benchmark: daily rebalanced equal-weight PIT TOP50, with prior-session membership.",
        "- Horizons: 3, 5, 10, and 20 global adjusted-market sessions.",
        "- No ticker price forward-fill. A missing close at exact t+h produces a missing outcome.",
        "- Daily date-level spreads retain the full cross-section before time-series inference; date-block resampling therefore preserves within-date cross-sectional dependence.",
        "- No strategy return, BUY/SELL instruction, or position sizing is produced.",
        "", "## Important identification note", "",
        "- RS20 equals absolute return20 minus the same-date benchmark return20. Within a date, these differ only by a constant; their cross-sectional ranks are identical and their coefficients cannot be separately identified with date effects.",
        "- Therefore F1 tests RS20 incremental to RS5 and absolute return5. It does not pretend to estimate a separate RS20 effect after controlling for absolute return20, which is mathematically collinear.",
        "", "## F1: Does RS20 add information beyond RS5?", "",
        "Two complementary tests: (a) within each RS5 quintile, compare top-quintile RS20 names with the remaining names in that same RS5 stratum; (b) date-wise cross-sectional regressions of forward RS on standardized RS20, RS5, and absolute return5. The coefficient series is then tested through time.",
        "", "## F2: Does 5D/20D alignment add information?", "",
        "Report forward relative returns for all four sign quadrants and estimate a date-wise continuous interaction model: forward RS ~ standardized return5 + standardized return20 + their interaction. Alignment is not credited merely because the positive-both group beats the universe; its incremental interaction must also be considered.",
        "", "## F3: Is persistent weakness more than a one-horizon effect?", "",
        "Compare names weak on both RS5 and RS20 with RS5-only weak names, RS20-only weak names, and the remaining cross-section. Stability is reported by historical subperiod. A negative result is not automatically a short signal.",
        "", "## F4: Do concentrated impulses underperform distributed impulses?", "",
        "Within the positive 5D-return top quintile, split names by the within-date median of largest absolute daily log-return share. Compare forward RS, positive hit rate, and negative forward-RS frequency over each horizon.",
        "", "## Primary contrast summaries", "",
    ]
    for name, frame in summaries.items():
        lines += [f"### {name}", ""]
        if frame.empty:
            lines += ["No valid observations.", ""]
            continue
        lines += ["| Contrast | Horizon | Mean spread | NW 95% CI | Block 95% CI | Dates | q |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for r in frame.itertuples(index=False):
            label = getattr(r, "contrast", getattr(r, "module", ""))
            h = getattr(r, "horizon", "")
            mean = getattr(r, "mean_daily_spread", np.nan)
            lo = getattr(r, "nw_ci_low", np.nan)
            hi = getattr(r, "nw_ci_high", np.nan)
            blo = getattr(r, "block_ci_low", np.nan)
            bhi = getattr(r, "block_ci_high", np.nan)
            n = getattr(r, "n_dates", 0)
            q = getattr(r, "bh_q", np.nan)
            lines.append(
                f"| {label} | {h} | {mean:.3%} | [{lo:.3%}, {hi:.3%}] | "
                f"[{blo:.3%}, {bhi:.3%}] | {n:,} | {q:.3f} |"
            )
        lines.append("")
    lines += [
        "## F1 conditional regression coefficients", "",
        "| Horizon | Coefficient | Mean | NW 95% CI | Dates | q |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for r in f1_reg_summary.itertuples(index=False):
        lines.append(
            f"| {r.horizon} | {r.coefficient} | {r.mean:.5f} | "
            f"[{r.nw_ci_low:.5f}, {r.nw_ci_high:.5f}] | {r.n_dates:,} | {r.bh_q:.3f} |"
        )
    lines += [
        "", "## F2 momentum quadrants", "",
        "| Horizon | Quadrant | Mean forward RS | NW 95% CI | Dates | q |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for r in f2_quadrant_summary.itertuples(index=False):
        lines.append(
            f"| {r.horizon} | {r.quadrant} | {r.mean:.3%} | "
            f"[{r.nw_ci_low:.3%}, {r.nw_ci_high:.3%}] | {r.n_dates:,} | {r.bh_q:.3f} |"
        )
    lines += [
        "", "## F2 continuous interaction", "",
        "| Horizon | Coefficient | Mean | NW 95% CI | Dates | q |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for r in f2_int_summary.itertuples(index=False):
        lines.append(
            f"| {r.horizon} | {r.coefficient} | {r.mean:.5f} | "
            f"[{r.nw_ci_low:.5f}, {r.nw_ci_high:.5f}] | {r.n_dates:,} | {r.bh_q:.3f} |"
        )
    lines += [
        "", "## F3 persistent weakness outside predefined crisis windows", "",
        "Crisis windows excluded in this diagnostic: 2008-09-15 to 2009-06-30, "
        "2020-02-20 to 2020-06-30, and 2022-02-24 to 2022-12-30. These exclusions "
        "are a robustness view only; the full-sample results remain primary.",
        "", "### F3 full sample vs crisis-excluded", "",
        "| Contrast | Horizon | Mean spread | NW 95% CI | Dates | q |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in f3_ex_summary.itertuples(index=False):
        lines.append(
            f"| {r.contrast} | {r.horizon} | {r.mean_daily_spread:.3%} | "
            f"[{r.nw_ci_low:.3%}, {r.nw_ci_high:.3%}] | {r.n_dates:,} | {r.bh_q:.3f} |"
        )
    lines += [
        "", "## Inference and limitations", "",
        "- HAC Newey-West intervals and circular moving-block bootstrap are applied to daily date-level estimates. This preserves contemporaneous cross-sectional dependence because the resampling unit is the date-level statistic, not individual ticker rows.",
        "- The bootstrap uses five-session circular blocks for all reported contrast series; this is a common dependence-aware robustness check, not an exact finite-sample test.",
        "- Forward horizons overlap. NW lag is conservatively set to 19 sessions for the reported date-level series.",
        "- BH q-values are screening adjustments within each summary table. Effect size, interval, sample size, period stability, and economic plausibility matter more than a threshold alone.",
        "- The subperiod split is descriptive and fixed: through 2012, 2013-2019, and 2020 onward.",
        "- The 4 modules are falsification diagnostics, not optimized trading rules. Any surviving effect must still pass out-of-sample and implementation checks before a name-level signal is considered.",
        "", "## Outputs", "",
        "Markdown report: docs/aggressive_hypothesis_falsification_report.md",
        "CSV files: data/interim/aggressive_hypothesis_falsification/",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    args = parse_args()
    for p in (args.snapshot, args.benchmark, args.db, SNAPSHOT_SCRIPT):
        if not p.is_file():
            raise FileNotFoundError(f"Required input not found: {p}")

    print("Loading PIT snapshot and benchmark...")
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
        raise RuntimeError(f"Snapshot missing columns: {sorted(missing)}")
    snapshot = snapshot.loc[snapshot.bar_available.eq(1)].copy()
    snapshot["secid"] = snapshot.secid.astype(str).str.upper()

    print("Loading adjusted closes and building exact-session forward outcomes...")
    daily = load_prices(
        args.db, snapshot.tradedate.min() - pd.Timedelta(days=500),
        snapshot.tradedate.max()
    )
    daily["secid"] = daily.secid.astype(str).str.upper()
    calendar = pd.DatetimeIndex(
        daily.tradedate.drop_duplicates().sort_values(), name="tradedate"
    )
    future, close = future_outcomes(daily, benchmark, calendar)
    panel = add_cross_sectional_features(snapshot)

    print("Running F1: incremental RS20...")
    f1, f1_reg = h2_conditional_tests(panel, future)
    print("Running F2: aligned momentum...")
    f2, f2_interaction = h3_quadrants(panel, future)
    print("Running F3: persistent weakness...")
    f3 = h5_weakness_tests(panel, future)
    print("Running F4: impulse concentration...")
    concentration = h1_concentration(panel, close, calendar)
    f4 = h1_daily_spreads(concentration, future)

    f1_summary = summarize_spreads(f1, ["module", "horizon"]) if len(f1) else pd.DataFrame()
    # F2 quadrant means are reported as descriptive cross-sectional series;
    # inference on the incremental interaction is reported separately.
    f3_summary = summarize_spreads(f3, ["module", "contrast", "horizon"]) if len(f3) else pd.DataFrame()
    f4_summary = summarize_spreads(f4, ["module", "horizon"]) if len(f4) else pd.DataFrame()
    f1_reg_summary = summarize_date_series(
        f1_reg, ["beta_rs20", "beta_rs5", "beta_return5"], ["module", "horizon"]
    ) if len(f1_reg) else pd.DataFrame()
    f2_int_summary = summarize_date_series(
        f2_interaction, ["beta_return5", "beta_return20", "beta_interaction"], ["horizon"]
    ) if len(f2_interaction) else pd.DataFrame()
    f2_quadrant_summary = summarize_date_series(
        f2, ["mean_forward_rs"], ["horizon", "quadrant"]
    ) if len(f2) else pd.DataFrame()

    # Predefined crisis-window robustness for F3. Full sample remains primary.
    crisis_windows = [
        ("2008-09-15", "2009-06-30"),
        ("2020-02-20", "2020-06-30"),
        ("2022-02-24", "2022-12-30"),
    ]
    if len(f3):
        f3["in_crisis_window"] = False
        for start, end in crisis_windows:
            f3["in_crisis_window"] |= f3.tradedate.between(pd.Timestamp(start), pd.Timestamp(end))
        f3_ex = f3.loc[~f3.in_crisis_window].copy()
    else:
        f3_ex = pd.DataFrame()

    f3_ex_summary = summarize_spreads(
        f3_ex, ["module", "contrast", "horizon"]
    ) if len(f3_ex) else pd.DataFrame()

    # Fixed subperiod robustness for all daily contrast series.
    period_frames = []
    for name, frame, keys in [
        ("F1", f1, ["module", "horizon"]),
        ("F3", f3, ["module", "contrast", "horizon"]),
        ("F4", f4, ["module", "horizon"]),
    ]:
        if frame.empty:
            continue
        tmp = add_periods(frame)
        for group_key, g in tmp.groupby(keys + ["period"], sort=True):
            if not isinstance(group_key, tuple):
                group_key = (group_key,)
            mean, se, t = nw_mean(g.sort_values("tradedate").daily_spread, 19)
            period_frames.append({
                "module_set": name, **dict(zip(keys + ["period"], group_key)),
                "n_dates": g.tradedate.nunique(), "mean_daily_spread": mean,
                "nw_ci_low": mean - 1.96 * se if np.isfinite(se) else np.nan,
                "nw_ci_high": mean + 1.96 * se if np.isfinite(se) else np.nan,
                "nw_t": t,
            })
    # F2 interaction coefficient stability by the same fixed periods.
    if len(f2_interaction):
        tmp = add_periods(f2_interaction)
        for (horizon, period), g in tmp.groupby(["horizon", "period"], sort=True):
            mean, se, t = nw_mean(g.sort_values("tradedate").beta_interaction, 19)
            period_frames.append({
                "module_set": "F2_interaction", "horizon": int(horizon),
                "period": period, "n_dates": g.tradedate.nunique(),
                "mean_daily_spread": mean,
                "nw_ci_low": mean - 1.96 * se if np.isfinite(se) else np.nan,
                "nw_ci_high": mean + 1.96 * se if np.isfinite(se) else np.nan,
                "nw_t": t,
            })
    periods = pd.DataFrame(period_frames)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "f1_rs20_matched_daily.csv": f1,
        "f1_rs20_regression_coefficients.csv": f1_reg,
        "f1_rs20_regression_summary.csv": f1_reg_summary,
        "f2_momentum_quadrants.csv": f2,
        "f2_interaction_coefficients.csv": f2_interaction,
        "f2_interaction_summary.csv": f2_int_summary,
        "f3_persistent_weakness_daily.csv": f3,
        "f3_persistent_weakness_ex_crisis_summary.csv": f3_ex_summary,
        "f4_impulse_concentration_metrics.csv": concentration,
        "f4_impulse_concentration_daily.csv": f4,
        "period_stability.csv": periods,
    }
    for filename, frame in outputs.items():
        frame.to_csv(args.output_dir / filename, index=False, encoding="utf-8-sig")

    summaries = {
        "F1 RS20 matched within RS5": f1_summary,
        "F3 persistent weakness": f3_summary,
        "F4 impulse concentration": f4_summary,
    }
    write_report(
        args.report, panel, future, f1, f1_reg, f1_reg_summary,
        f2, f2_interaction, f2_int_summary, f2_quadrant_summary,
        f3, f3_ex_summary, f4, summaries
    )
    print("\nFALSIFICATION RUN COMPLETE")
    print("=" * 68)
    print(f"F1 matched contrasts: {len(f1):,} date-horizon rows")
    print(f"F1 regression dates:  {len(f1_reg):,}")
    print(f"F2 quadrant rows:     {len(f2):,}")
    print(f"F2 interaction dates: {len(f2_interaction):,}")
    print(f"F3 contrast rows:     {len(f3):,}")
    print(f"F4 contrast rows:     {len(f4):,}")
    print(f"Markdown report:      {args.report}")
    print(f"CSV outputs:          {args.output_dir}")
    print("=" * 68)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
