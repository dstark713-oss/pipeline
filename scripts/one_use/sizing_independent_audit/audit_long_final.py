from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PANEL_DEFAULT = ROOT / "data" / "processed" / "top50" / "top50_panel.parquet"
OUT_DEFAULT = ROOT / "data" / "interim" / "sizing_independent_audit"
REPORT_DEFAULT = ROOT / "docs" / "sizing_long_final_audit_report.md"
REPORTED_LONG = ["CNRU", "HYDR", "SVCB", "T", "SMLT", "DOMRF", "MTSS", "PHOR", "VKCO", "RTKM"]
HORIZONS = (10, 20)
COSTS_BPS = (15.0, 30.0, 50.0)


def parse_args():
    p = argparse.ArgumentParser(description="Final independent robustness audit of Aggressive Long candidates.")
    p.add_argument("--panel", type=Path, default=PANEL_DEFAULT)
    p.add_argument("--output-dir", type=Path, default=OUT_DEFAULT)
    p.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    return p.parse_args()


def load_panel(path: Path) -> pd.DataFrame:
    x = pd.read_parquet(path)
    required = {"tradedate", "secid", "ranking_asof_date", "rank", "bar_available", "adjusted_close", "value"}
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
        raise ValueError("PIT look-ahead violation.")
    return x.sort_values(["tradedate", "rank", "secid"]).reset_index(drop=True)


def reconstruct_long(panel: pd.DataFrame):
    dates = pd.DatetimeIndex(sorted(panel.tradedate.unique()), name="tradedate")
    close = panel.pivot(index="tradedate", columns="secid", values="adjusted_close").reindex(dates)
    valid = panel.pivot(index="tradedate", columns="secid", values="bar_available").reindex(dates).eq(1)
    close = close.where(valid & close.gt(0))
    returns = {}
    for h in (5, 20):
        r = close.div(close.shift(h)).sub(1)
        complete = close.notna().rolling(h + 1, min_periods=h + 1).sum().eq(h + 1)
        returns[h] = r.where(complete)

    by_date = {d: g for d, g in panel.groupby("tradedate", sort=True)}
    rows = []
    for d in dates:
        r5, r20 = returns[5].loc[d], returns[20].loc[d]
        bench5, bench20 = r5.mean(), r20.mean()
        a = pd.DataFrame({
            "secid": close.columns,
            "return_5d": r5.to_numpy(),
            "return_20d": r20.to_numpy(),
            "rs_5d": (r5 - bench5).to_numpy(),
            "rs_20d": (r20 - bench20).to_numpy(),
            "close": close.loc[d].to_numpy(),
        })
        m = by_date[d][["secid", "rank", "bar_available", "value"]]
        a = a.merge(m, on="secid", how="inner", validate="one_to_one")
        a["eligible"] = (a.bar_available.eq(1) & a.close.gt(0) & a.value.gt(0)
                         & a[["return_5d", "return_20d", "rs_5d", "rs_20d"]].notna().all(axis=1))
        a["rs5_pct"] = a.rs_5d.rank(pct=True, method="average")
        a["rs5_q"] = np.ceil(a.rs5_pct * 5).clip(1, 5)
        a["rs20_within_rs5_pct"] = a.groupby("rs5_q", observed=False).rs_20d.rank(pct=True, method="average")
        a["long"] = a.eligible & a.rs_20d.gt(0) & a.rs20_within_rs5_pct.ge(.80)
        a["tradedate"] = d
        rows.append(a)
    return dates, close, pd.concat(rows, ignore_index=True)


def nw_mean_ci(values: pd.Series, lag: int):
    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    n = len(x)
    if n < max(30, lag + 2):
        return np.nan, np.nan, np.nan, n
    u = x - x.mean()
    lrv = np.dot(u, u) / n
    for j in range(1, lag + 1):
        gamma = np.dot(u[j:], u[:-j]) / n
        weight = 1.0 - j / (lag + 1.0)
        lrv += 2.0 * weight * gamma
    se = np.sqrt(max(lrv, 0.0) / n)
    t = x.mean() / se if se > 0 else np.nan
    return x.mean(), se, t, n


def evaluate(panel, dates, close, signals):
    cost_rows, detail_rows, candidate_rows = [], [], []
    for h in HORIZONS:
        future = close.shift(-h).div(close).sub(1)
        complete = close.notna().iloc[::-1].rolling(h + 1, min_periods=h + 1).sum().iloc[::-1].eq(h + 1)
        future = future.where(complete)
        benchmark = future.mean(axis=1)
        excess = future.sub(benchmark, axis=0)
        f = future.rename_axis(index="tradedate", columns="secid").stack().rename("fwd").reset_index()
        e = excess.rename_axis(index="tradedate", columns="secid").stack().rename("excess").reset_index()
        q = signals.loc[signals.long, ["tradedate", "secid"]].merge(f, on=["tradedate", "secid"], how="inner")
        q = q.merge(e, on=["tradedate", "secid"], how="left")
        counts = q.groupby("tradedate").secid.transform("size")
        q["names_on_date"] = counts
        q["year"] = q.tradedate.dt.year
        q["gross_contribution"] = q.fwd / counts
        q["excess_contribution"] = q.excess / counts
        for bps in COSTS_BPS:
            cost = bps / 10000.0
            q["net"] = q.fwd - cost
            daily = q.groupby("tradedate").net.mean().reindex(dates, fill_value=0.0)
            daily_excess = (q.assign(net_excess=q.excess - cost)
                              .groupby("tradedate").net_excess.mean().reindex(dates, fill_value=0.0))
            active = q.groupby("tradedate").net.mean()
            mean, se, t, n = nw_mean_ci(daily, h - 1)
            ex_mean, ex_se, ex_t, _ = nw_mean_ci(daily_excess, h - 1)
            cost_rows.append({
                "horizon": h, "cost_bps_rt": bps, "signals": len(q), "active_dates": len(active),
                "mean_active_net": active.mean(), "median_signal_net": q.net.median(),
                "hit_rate": (q.net > 0).mean(), "date_level_cohort_mean": mean,
                "cohort_hac_se": se, "cohort_hac_t": t,
                "cohort_hac_ci_low": mean - 1.96 * se, "cohort_hac_ci_high": mean + 1.96 * se,
                "date_level_excess_mean": ex_mean, "excess_cohort_hac_se": ex_se, "excess_cohort_hac_t": ex_t,
                "excess_cohort_hac_ci_low": ex_mean - 1.96 * ex_se, "excess_cohort_hac_ci_high": ex_mean + 1.96 * ex_se,
                "positive_year_fraction": (q.assign(net=q.net).groupby("year").net.mean() > 0).mean(),
            })
            if bps == 15:
                q["net"] = q.fwd - cost
                by_ticker = q.groupby("secid").agg(
                    signals=("net", "size"), mean_net=("net", "mean"),
                    median_net=("net", "median"), hit_rate=("net", lambda z: (z > 0).mean()),
                    mean_excess=("excess", "mean")
                )
                positive_years = q.groupby(["secid", "year"]).net.mean().gt(0).groupby("secid").mean()
                by_ticker = by_ticker.join(positive_years.rename("positive_year_fraction")).reset_index()
                by_ticker["horizon"] = h
                candidate_rows.append(by_ticker)
                for year, g in q.groupby("year"):
                    detail_rows.append({"horizon": h, "year": year, "signals": len(g),
                                        "mean_net": g.net.mean(), "mean_excess": g.excess.mean()})
        # Concentration measured on equal-weight per-date contribution, at 15 bps.
        q["net_contribution"] = (q.fwd - .0015) / q.names_on_date
        ticker_contrib = q.groupby("secid").net_contribution.sum().clip(lower=0).sort_values(ascending=False)
        total_positive = ticker_contrib.sum()
        for pct in (.01, .05, .10):
            k = max(1, int(np.ceil(len(ticker_contrib) * pct)))
            detail_rows.append({"horizon": h, "year": f"TOP_{int(pct*100)}PCT_TICKERS",
                                "signals": k, "mean_net": ticker_contrib.head(k).sum() / total_positive
                                if total_positive > 0 else np.nan, "mean_excess": np.nan})
    return pd.DataFrame(cost_rows), pd.concat(candidate_rows, ignore_index=True), pd.DataFrame(detail_rows)


def latest_risk_snapshot(panel, dates, close, signals):
    latest = dates.max()
    current = signals.loc[signals.tradedate.eq(latest)]
    reconstructed = set(current.loc[current.long, "secid"])
    names = sorted(set(REPORTED_LONG) | reconstructed)
    returns = close.pct_change(fill_method=None)
    value_panel = panel.pivot(index="tradedate", columns="secid", values="value").reindex(dates)
    rows = []
    current_rows = panel.loc[panel.tradedate.eq(latest)].set_index("secid")
    for ticker in names:
        if ticker not in current_rows.index:
            rows.append({"ticker": ticker, "in_reported_list": ticker in REPORTED_LONG,
                         "reconstructed_long": ticker in reconstructed, "current_bar": False})
            continue
        r20 = returns[ticker].tail(20).dropna()
        r60 = returns[ticker].tail(60).dropna()
        v20 = r20.std(ddof=1) * np.sqrt(252) if len(r20) >= 15 else np.nan
        v60 = r60.std(ddof=1) * np.sqrt(252) if len(r60) >= 45 else np.nan
        val = pd.to_numeric(current_rows.loc[ticker, "value"], errors="coerce")
        hist_value = pd.to_numeric(value_panel[ticker].tail(20), errors="coerce").dropna()
        rows.append({"ticker": ticker, "in_reported_list": ticker in REPORTED_LONG,
                     "reconstructed_long": ticker in reconstructed, "current_bar": bool(current_rows.loc[ticker, "bar_available"] == 1),
                     "current_value": val, "median_value_last20sessions": hist_value.median(),
                     "vol20_ann": v20, "vol60_ann": v60,
                     "return20_abs": close[ticker].iloc[-1] / close[ticker].iloc[-21] - 1
                     if len(close[ticker].dropna()) >= 21 and close[ticker].iloc[-21] > 0 else np.nan})
    risk = pd.DataFrame(rows)
    corr_names = [x for x in REPORTED_LONG if x in close.columns]
    corr = returns[corr_names].tail(60).corr(min_periods=40)
    return risk, corr, reconstructed


def main():
    args = parse_args()
    panel = load_panel(args.panel)
    dates, close, signals = reconstruct_long(panel)
    robustness, by_ticker, detail = evaluate(panel, dates, close, signals)
    risk, corr, reconstructed = latest_risk_snapshot(panel, dates, close, signals)
    overlap = len(reconstructed & set(REPORTED_LONG))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    robustness.to_csv(args.output_dir / "long_final_robustness.csv", index=False)
    by_ticker.to_csv(args.output_dir / "long_final_by_ticker.csv", index=False)
    detail.to_csv(args.output_dir / "long_final_years_and_concentration.csv", index=False)
    risk.to_csv(args.output_dir / "long_latest_risk_snapshot.csv", index=False)
    corr.to_csv(args.output_dir / "long_latest_60d_correlation.csv")

    lines = [
        "# Sizing — final independent Long audit", "",
        f"- Panel as-of: {dates.max().date()}; {len(dates):,} sessions; {panel.secid.nunique()} tickers.",
        "- PIT guard: ranking_asof_date < tradedate; duplicates rejected.",
        "- Long reconstruction: positive RS20 and top-quintile RS20 within the same RS5 quintile; RS benchmark is the same-date valid PIT cross-section equal-weight mean.",
        "- Forward outcomes require all h+1 close observations across intervening sessions; no forward fill.",
        "- Cost sensitivity: 15 / 30 / 50 bps round-trip, charged once per completed h-session signal.",
        "- HAC uncertainty is calculated on the date-level equal-weight mean of overlapping h-session cohort forward returns, with zero return on dates without an eligible signal; lag = horizon - 1 to account for overlapping forward windows.",
        "- HAC intervals are asymptotic diagnostics, not a substitute for a fully executable portfolio backtest or a multiple-testing correction.",
        "", "## Cost and HAC robustness", robustness.to_string(index=False),
        "", "## Historical performance by reported candidate", by_ticker.to_string(index=False),
        "", "## Annual means and ticker contribution concentration", detail.to_string(index=False),
        "", "## Latest name-level risk and liquidity snapshot", risk.to_string(index=False),
        "", "## Latest reported-candidate 60-session return correlation", corr.to_string(),
        "", f"- Latest reconstructed Long candidates: {len(reconstructed)}; overlap with reported list: {overlap}/10.",
        "- Candidate-level history is conditional on the independent reconstruction and must not be interpreted as a standalone ticker forecast.",
        "- Volatility and traded value are sizing inputs, not alpha evidence. Pairwise correlations are descriptive and may be unstable in a 60-session window.",
        "- No weights are produced by this audit. The next stage is name selection and sizing, including zero weights where evidence or constraints do not justify capital.",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nSIZING — FINAL LONG AUDIT")
    print("=" * 72)
    print(f"Panel as-of: {dates.max().date()} | sessions={len(dates):,} | tickers={panel.secid.nunique()} | PIT=PASS")
    print("\nCOST + HAC ROBUSTNESS (date-level cohort mean of overlapping horizon returns)")
    print(robustness[["horizon", "cost_bps_rt", "signals", "date_level_cohort_mean", "daily_hac_se",
                     "daily_hac_t", "daily_hac_ci_low", "daily_hac_ci_high",
                     "date_level_excess_mean", "excess_hac_t", "excess_hac_ci_low",
                     "excess_hac_ci_high", "positive_year_fraction"]].to_string(index=False,
                     formatters={c: (lambda x: f"{x:+.3%}") for c in
                                 ["date_level_cohort_mean", "daily_hac_se", "daily_hac_ci_low",
                                  "daily_hac_ci_high", "date_level_excess_mean", "excess_hac_ci_low",
                                  "excess_hac_ci_high"]}))
    print(f"\nLatest reconstructed Long: {len(reconstructed)} | overlap with reported list: {overlap}/10")
    print("\nLATEST NAME RISK SNAPSHOT")
    print(risk.to_string(index=False, formatters={
        "vol20_ann": lambda x: "n/a" if pd.isna(x) else f"{x:.1%}",
        "vol60_ann": lambda x: "n/a" if pd.isna(x) else f"{x:.1%}",
        "return20_abs": lambda x: "n/a" if pd.isna(x) else f"{x:+.1%}",
    }))
    print(f"\nFiles: {args.output_dir} | report: {args.report}")
    print("=" * 72)


if __name__ == "__main__":
    main()
