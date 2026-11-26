from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PANEL_DEFAULT = ROOT / "data" / "processed" / "top50" / "top50_panel.parquet"
OUT_DEFAULT = ROOT / "data" / "interim" / "sizing_independent_audit"
REPORT_DEFAULT = ROOT / "docs" / "sizing_independent_audit_report.md"
COST_BPS_RT = 15.0
HORIZONS = (10, 20)
LONG_REPORTED = ["CNRU", "HYDR", "SVCB", "T", "SMLT", "DOMRF", "MTSS", "PHOR", "VKCO", "RTKM"]
SHORT_REPORTED = ["RNFT", "FEES", "SGZH", "GAZP"]


def parse_args():
    p = argparse.ArgumentParser(description="Independent falsification audit of Aggressive and Conservative agent handoffs.")
    p.add_argument("--panel", type=Path, default=PANEL_DEFAULT)
    p.add_argument("--output-dir", type=Path, default=OUT_DEFAULT)
    p.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    p.add_argument("--cost-bps-rt", type=float, default=COST_BPS_RT)
    return p.parse_args()


def load_panel(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"PIT TOP50 panel not found: {path}")
    x = pd.read_parquet(path)
    required = {"tradedate", "secid", "ranking_asof_date", "rank", "bar_available",
                "adjusted_close", "value"}
    missing = required - set(x.columns)
    if missing:
        raise ValueError(f"Panel missing columns: {sorted(missing)}")
    x = x.copy()
    x["tradedate"] = pd.to_datetime(x["tradedate"]).dt.normalize()
    x["ranking_asof_date"] = pd.to_datetime(x["ranking_asof_date"]).dt.normalize()
    x["secid"] = x["secid"].astype(str).str.upper()
    for c in ["rank", "bar_available", "adjusted_close", "value"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    if x.duplicated(["tradedate", "secid"]).any():
        raise ValueError("Duplicate PIT ticker/session rows.")
    if not (x["ranking_asof_date"] < x["tradedate"]).all():
        raise ValueError("PIT look-ahead violation: ranking_asof_date must precede tradedate.")
    return x.sort_values(["tradedate", "rank", "secid"]).reset_index(drop=True)


def build_signal_history(panel: pd.DataFrame):
    dates = pd.DatetimeIndex(sorted(panel.tradedate.unique()), name="tradedate")
    close = panel.pivot(index="tradedate", columns="secid", values="adjusted_close").reindex(dates)
    valid = panel.pivot(index="tradedate", columns="secid", values="bar_available").reindex(dates).eq(1)
    close = close.where(valid & close.gt(0))
    daily_ret = close.pct_change(fill_method=None)
    records = []
    for h in (5, 20):
        ret = close.div(close.shift(h)).sub(1)
        complete = close.notna().rolling(h + 1, min_periods=h + 1).sum().eq(h + 1)
        ret = ret.where(complete)
        # Relative return versus the PIT cross-section, calculated only from
        # securities with a valid same-date h-session return.
        bench = ret.mean(axis=1)
        rs = ret.sub(bench, axis=0)
        records.append((h, ret, rs))
    ret5, rs5 = records[0][1], records[0][2]
    ret20, rs20 = records[1][1], records[1][2]

    rows = []
    panel_by_date = {date: group for date, group in panel.groupby("tradedate", sort=True)}
    for date in dates:
        a = pd.DataFrame({
            "secid": close.columns,
            "return_5d": ret5.loc[date].to_numpy(),
            "rs_5d": rs5.loc[date].to_numpy(),
            "return_20d": ret20.loc[date].to_numpy(),
            "rs_20d": rs20.loc[date].to_numpy(),
            "close": close.loc[date].to_numpy(),
        })
        membership = panel_by_date[date][["secid", "rank", "bar_available", "value"]]
        a = a.merge(membership, on="secid", how="inner", validate="one_to_one")
        a["eligible"] = (a.bar_available.eq(1) & a.close.gt(0) & a.value.gt(0)
                         & a[["return_5d", "rs_5d", "return_20d", "rs_20d"]].notna().all(axis=1))
        a["rs5_pct"] = a.rs_5d.rank(pct=True, method="average")
        a["rs5_quintile"] = np.ceil(a.rs5_pct * 5).clip(1, 5)
        a["rs20_pct_within_rs5"] = a.groupby("rs5_quintile", observed=False).rs_20d.rank(pct=True, method="average")
        a["rs20_pct"] = a.rs_20d.rank(pct=True, method="average")
        a["long"] = a.eligible & a.rs_20d.gt(0) & a.rs20_pct_within_rs5.ge(.80)
        a["short"] = (a.eligible & a.rs5_pct.le(.20) & a.rs20_pct.le(.20)
                      & a.rs_5d.lt(0) & a.rs_20d.lt(0))
        a["tradedate"] = date
        rows.append(a)
    signals = pd.concat(rows, ignore_index=True)
    return dates, close, daily_ret, signals


def evaluate_aggressive(dates, close, signals, cost_bps):
    cost = cost_bps / 10000.0
    results = []
    for horizon in HORIZONS:
        future = close.shift(-horizon).div(close).sub(1)
        # Require every intervening global session bar; endpoints alone can hide gaps.
        future_complete = close.notna().iloc[::-1].rolling(
            horizon + 1, min_periods=horizon + 1
        ).sum().iloc[::-1].eq(horizon + 1)
        future = future.where(future_complete)
        future_benchmark = future.mean(axis=1)
        future_excess = future.sub(future_benchmark, axis=0)
        future_long = future.rename_axis(index="tradedate", columns="secid").stack().rename("fwd_return").reset_index()
        excess_long = future_excess.rename_axis(index="tradedate", columns="secid").stack().rename("fwd_excess").reset_index()
        day = signals[["tradedate", "secid", "long", "short", "rs_5d", "rs_20d", "return_20d"]]
        z = day.merge(future_long, on=["tradedate", "secid"], how="left", validate="one_to_one")
        z = z.merge(excess_long, on=["tradedate", "secid"], how="left", validate="one_to_one")
        for side, col in [("LONG", "long"), ("SHORT", "short")]:
            q = z.loc[z[col] & z.fwd_return.notna()].copy()
            if side == "SHORT":
                q["net_return"] = -q.fwd_return - cost
            else:
                q["net_return"] = q.fwd_return - cost
            daily = q.groupby("tradedate").net_return.mean()
            years = q.assign(year=q.tradedate.dt.year).groupby("year").net_return.mean()
            results.append({
                "side": side, "horizon": horizon, "signals": len(q),
                "signal_dates": int(daily.size), "mean_net": q.net_return.mean(),
                "median_net": q.net_return.median(), "hit_rate_net": (q.net_return > 0).mean(),
                "mean_excess": q.fwd_excess.mean(),
                "positive_year_fraction": (years > 0).mean() if len(years) else np.nan,
                "worst_year_mean": years.min() if len(years) else np.nan,
                "best_year_mean": years.max() if len(years) else np.nan,
                "mean_names_per_date": q.groupby("tradedate").size().mean() if len(q) else np.nan,
            })
    return pd.DataFrame(results)


def conservative_audit(panel: pd.DataFrame):
    x = panel.loc[panel.bar_available.eq(1) & panel.adjusted_close.gt(0),
                  ["tradedate", "secid", "adjusted_close"]].copy()
    dates = pd.DatetimeIndex(sorted(x.tradedate.unique()))
    close = x.pivot(index="tradedate", columns="secid", values="adjusted_close").reindex(dates)
    ret = close.pct_change(fill_method=None)
    daily = pd.DataFrame(index=dates)
    daily["breadth"] = ret.gt(0).sum(axis=1) / ret.notna().sum(axis=1).replace(0, np.nan)
    daily["equal_weight_return"] = ret.mean(axis=1)
    daily["median_return"] = ret.median(axis=1)
    positive = ret.clip(lower=0)
    share_top5 = positive.apply(lambda r: r.nlargest(5).sum() / r.sum() if r.sum() > 0 else np.nan, axis=1)
    daily["top5_positive_share"] = share_top5
    daily = daily.dropna(subset=["breadth", "equal_weight_return"])
    groups = [("FULL", daily), ("LAST_120", daily.tail(120)), ("LAST_60", daily.tail(60)),
              ("LAST_20", daily.tail(20))]
    q4 = daily.loc[daily.index >= pd.Timestamp("2026-10-01")]
    if not q4.empty:
        groups.append(("2026_Q4", q4))
    out = []
    for name, g in groups:
        out.append({
            "period": name, "start": g.index.min().date().isoformat(),
            "end": g.index.max().date().isoformat(), "sessions": len(g),
            "breadth_mean": g.breadth.mean(), "breadth_gt50": (g.breadth > .5).mean(),
            "ew_return_mean": g.equal_weight_return.mean(),
            "median_return_mean": g.median_return.mean(),
            "top5_positive_share_mean": g.top5_positive_share.mean(),
        })
    # Fundamental/sector proof is not present in the quantitative panel schema.
    fundamental_columns = [c for c in panel.columns if any(k in c.lower() for k in
                           ("revenue", "ebitda", "ebit", "free_cash", "operating_cash",
                            "net_debt", "sector", "industry", "fundamental"))]
    return pd.DataFrame(out), fundamental_columns


def fmt_pct(x):
    return "n/a" if pd.isna(x) else f"{x:+.2%}"


def main():
    args = parse_args()
    panel = load_panel(args.panel)
    dates, close, daily_ret, signals = build_signal_history(panel)
    aggressive = evaluate_aggressive(dates, close, signals, args.cost_bps_rt)
    conservative, fundamental_cols = conservative_audit(panel)
    latest = dates.max()
    current = signals.loc[signals.tradedate.eq(latest)]
    current_long = current.loc[current.long, "secid"].tolist()
    current_short = current.loc[current.short, "secid"].tolist()
    reported_long = set(LONG_REPORTED)
    reported_short = set(SHORT_REPORTED)
    long_overlap = len(set(current_long) & reported_long)
    short_overlap = len(set(current_short) & reported_short)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    aggressive.to_csv(args.output_dir / "aggressive_historical_falsification.csv", index=False)
    conservative.to_csv(args.output_dir / "conservative_regime_recheck.csv", index=False)
    pd.DataFrame({"side": ["LONG", "SHORT"],
                  "rebuilt_latest_count": [len(current_long), len(current_short)],
                  "reported_count": [len(reported_long), len(reported_short)],
                  "ticker_overlap": [long_overlap, short_overlap],
                  "rebuilt_tickers": [",".join(current_long), ",".join(current_short)],
                  "reported_tickers": [",".join(sorted(reported_long)), ",".join(sorted(reported_short))]}).to_csv(
                      args.output_dir / "latest_packet_reconciliation.csv", index=False)

    lines = [
        "# Sizing independent audit — first iteration",
        "",
        f"- Panel: {args.panel}",
        f"- Data: {dates.min().date()} to {latest.date()}, {len(dates):,} sessions, {panel.secid.nunique()} tickers.",
        f"- PIT guard: ranking_asof_date strictly precedes tradedate: PASS.",
        f"- Cost assumption: {args.cost_bps_rt:.1f} bps round-trip, charged once per completed holding period.",
        "- Historical signal tests use daily PIT TOP50 membership; future returns require the exact h-session endpoint. Missing bars are not forward-filled.",
        "",
        "## Aggressive Trading — falsification",
        "",
        aggressive.to_string(index=False, float_format=lambda x: f"{x:.4f}"),
        "",
        f"Latest snapshot rebuilt from panel: {len(current_long)} Long / {len(current_short)} Short. "
        f"Overlap with reported 26-Nov list: Long {long_overlap}/10; Short {short_overlap}/4.",
        "A low overlap means the committed name packet is not reproducible from this independent reconstruction; inspect benchmark/feature definitions before sizing.",
        "Long results also report excess return versus the same-date PIT equal-weight cross-section; Short results are evaluated on absolute short P&L. Every intervening session bar is required for forward outcomes.",
        "Historical cohort means are diagnostics, not a fully executable portfolio backtest: signals overlap and no turnover/borrow/slippage model beyond the stated round-trip cost is included.",
        "",
        "## Conservative Investment — falsification",
        "",
        conservative.to_string(index=False, float_format=lambda x: f"{x:.4f}"),
        "",
        f"Sector/fundamental columns present in panel: {fundamental_cols if fundamental_cols else 'NONE'}.",
        "The panel can challenge broad-market participation claims but cannot validate sector economics, company fundamentals, valuation, or a positive BUY case.",
        "Therefore the current 100% cash posture is consistent with absence of verified fundamental evidence, but is NOT proven optimal by this price-only audit.",
        "",
        "## Decision gate",
        "",
        "- Do not size either handoff until the user returns this script's output and the latest actual portfolio / risk constraints are supplied.",
        "- Aggressive Longs are candidate signals, not independently validated allocations. Shorts remain conditional and require explicit permission plus borrow/implementation evidence.",
        "- Conservative has no sector/company BUY thesis in its journal; no capital deployment is justified by breadth diagnostics alone.",
        "- Mandate remains 50% Aggressive sleeve / 50% Conservative sleeve. This audit does not alter that split.",
        "",
        "## Output files",
        "",
        "- aggressive_historical_falsification.csv",
        "- conservative_regime_recheck.csv",
        "- latest_packet_reconciliation.csv",
        "",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print("\nSIZING INDEPENDENT AUDIT")
    print("=" * 72)
    print(f"Panel as-of: {latest.date()} | sessions={len(dates):,} | tickers={panel.secid.nunique()}")
    print(f"PIT look-ahead: PASS | cost={args.cost_bps_rt:.1f} bps RT")
    print("\nAGGRESSIVE: historical cohort falsification (net of stated cost)")
    print(aggressive.to_string(index=False, formatters={
        "mean_net": fmt_pct, "median_net": fmt_pct, "mean_excess": fmt_pct, "hit_rate_net": lambda x: f"{x:.1%}",
        "positive_year_fraction": lambda x: f"{x:.1%}",
        "worst_year_mean": fmt_pct, "best_year_mean": fmt_pct,
    }))
    print(f"Latest reconstructed candidates: LONG {len(current_long)} ({long_overlap}/10 overlap), SHORT {len(current_short)} ({short_overlap}/4 overlap)")
    print("\nCONSERVATIVE: regime recheck")
    print(conservative.to_string(index=False, formatters={
        "breadth_mean": lambda x: f"{x:.1%}", "breadth_gt50": lambda x: f"{x:.1%}",
        "ew_return_mean": fmt_pct, "median_return_mean": fmt_pct,
        "top5_positive_share_mean": lambda x: f"{x:.1%}",
    }))
    print(f"Sector/fundamental columns: {fundamental_cols if fundamental_cols else 'NONE'}")
    print("\nNo allocation weights produced. Await returned panel output and verified portfolio/risk context.")
    print(f"Report: {args.report}")
    print(f"CSV outputs: {args.output_dir}")
    print("=" * 72)


if __name__ == "__main__":
    main()
