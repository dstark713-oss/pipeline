# Folder: scripts/experiments/primitives/portfolios/
# File: audit_results.py
# Purpose: Diagnose extreme portfolio results without changing source data or
#          rerunning/changing the original experiment's trading rules.
#
# Run from repository root:
#   python scripts/experiments/primitives/portfolios/audit_results.py

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))

from config import OUTPUT_DIR, TRANSACTION_COST_BPS
from data import load_inputs
from portfolio import build_target_weights


AUDIT_DIR = OUTPUT_DIR / "audit"
DAILY_PATH = OUTPUT_DIR / "daily_equity_curves.csv"
METRICS_PATH = OUTPUT_DIR / "full_sample_metrics.csv"


def log(message: str) -> None:
    print(message, flush=True)


def require_columns(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise RuntimeError(f"{label} is missing required columns: {missing}")


def safe_cagr(returns: pd.Series, periods_per_year: int = 252) -> float:
    values = pd.to_numeric(returns, errors="coerce").dropna()
    if values.empty:
        return np.nan
    wealth = float((1.0 + values).prod())
    years = len(values) / periods_per_year
    if wealth <= 0 or years <= 0:
        return np.nan
    return wealth ** (1.0 / years) - 1.0


def max_drawdown(returns: pd.Series) -> float:
    values = pd.to_numeric(returns, errors="coerce").dropna()
    if values.empty:
        return np.nan
    equity = (1.0 + values).cumprod()
    return float((equity / equity.cummax() - 1.0).min())


def concentration_report(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (strategy, cost), group in daily.groupby(
        ["strategy", "transaction_cost_bps"], sort=True
    ):
        if float(cost) != 0.0:
            continue
        returns = pd.to_numeric(group["net_return"], errors="coerce").dropna()
        positive = returns.clip(lower=0.0)
        positive_sum = float(positive.sum())
        ranked = positive.sort_values(ascending=False)
        n = len(ranked)
        row = {
            "strategy": strategy,
            "observations": n,
            "positive_day_count": int((returns > 0).sum()),
            "positive_return_sum": positive_sum,
        }
        for fraction in (0.01, 0.05, 0.10):
            count = max(1, int(np.ceil(n * fraction))) if n else 0
            contribution = float(ranked.head(count).sum()) if count else np.nan
            row[f"top_{int(fraction * 100)}pct_positive_day_share"] = (
                contribution / positive_sum if positive_sum > 0 else np.nan
            )
            row[f"top_{int(fraction * 100)}pct_day_count"] = count
        for count in (1, 5, 10, 20):
            contribution = float(ranked.head(count).sum())
            row[f"top_{count}_positive_days_share"] = (
                contribution / positive_sum if positive_sum > 0 else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def daily_extremes(daily: pd.DataFrame) -> pd.DataFrame:
    zero = daily[pd.to_numeric(daily["transaction_cost_bps"]).eq(0)].copy()
    zero = zero.sort_values("net_return")
    columns = [
        "strategy", "signal_date", "execution_date", "exit_date",
        "net_return", "gross_return", "equity_net", "effective_exposure",
        "turnover_one_way", "missing_return_weight", "constituents",
    ]
    worst = zero.groupby("strategy", group_keys=False).head(20).copy()
    best = zero.groupby("strategy", group_keys=False).tail(20).copy()
    worst["extreme_type"] = "worst"
    best["extreme_type"] = "best"
    result = pd.concat([worst, best], ignore_index=True)
    return result[[c for c in ["extreme_type", *columns] if c in result.columns]]


def robustness_report(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    zero = daily[pd.to_numeric(daily["transaction_cost_bps"]).eq(0)].copy()
    for strategy, group in zero.groupby("strategy", sort=True):
        group = group.sort_values("exit_date")
        r = pd.to_numeric(group["net_return"], errors="coerce")
        valid = r.notna()
        r = r[valid]
        if r.empty:
            continue
        # Diagnostic only: remove the largest positive daily observations.
        # This is not a valid investable strategy and must not be presented as one.
        for trim_n in (0, 1, 5, 10, 20):
            trimmed = r.copy()
            if trim_n:
                trimmed = trimmed.drop(trimmed.nlargest(min(trim_n, len(trimmed))).index)
            rows.append({
                "strategy": strategy,
                "removed_best_days": trim_n,
                "remaining_days": len(trimmed),
                "total_return": float((1.0 + trimmed).prod() - 1.0),
                "cagr_252": safe_cagr(trimmed),
                "max_drawdown_recomputed": max_drawdown(trimmed),
                "note": "Diagnostic deletion only; not an investable return series.",
            })
    return pd.DataFrame(rows)


def ticker_attribution(
    features: pd.DataFrame,
    weight_frames: dict[str, pd.DataFrame],
    asset_returns: pd.DataFrame,
    daily: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    zero = daily[pd.to_numeric(daily["transaction_cost_bps"]).eq(0)].copy()
    # Reconstruct the exact signal-date target weights from the experiment modules.
    # For the missing-forward-price treatment, invalid ticker returns are zeroed
    # and their target weights are excluded, matching the original simulator.
    for strategy, weights in weight_frames.items():
        if strategy not in set(zero["strategy"]):
            continue
        if strategy not in weight_frames:
            continue
        target = weights.reindex(asset_returns.index).fillna(0.0)
        returns = asset_returns.reindex(index=target.index, columns=target.columns)
        contribution = target.mul(returns.where(returns.notna(), 0.0))
        contribution = contribution.where(returns.notna(), 0.0)
        summed = contribution.sum(axis=0).sort_values(ascending=False)
        total_positive = float(summed.clip(lower=0.0).sum())
        total_net = float(summed.sum())
        for secid, value in summed.head(20).items():
            rows.append({
                "strategy": strategy,
                "secid": secid,
                "summed_gross_contribution": float(value),
                "share_of_positive_ticker_contributions": (
                    float(value / total_positive)
                    if value > 0 and total_positive > 0 else np.nan
                ),
                "all_ticker_net_contribution_sum": total_net,
                "note": (
                    "Approximate ticker attribution from target weights and "
                    "forward OPEN returns; excludes portfolio compounding and "
                    "turnover costs. Use to locate concentration, not reconcile "
                    "exactly to compounded portfolio wealth."
                ),
            })
        for secid, value in summed.tail(20).items():
            rows.append({
                "strategy": strategy,
                "secid": secid,
                "summed_gross_contribution": float(value),
                "share_of_positive_ticker_contributions": np.nan,
                "all_ticker_net_contribution_sum": total_net,
                "note": "Bottom ticker contributions; approximate, see note above.",
            })
    return pd.DataFrame(rows)


def period_metrics(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    zero = daily[pd.to_numeric(daily["transaction_cost_bps"]).eq(0)].copy()
    zero["exit_date"] = pd.to_datetime(zero["exit_date"])
    for (strategy, year), group in zero.groupby(
        ["strategy", zero["exit_date"].dt.year], sort=True
    ):
        r = pd.to_numeric(group.sort_values("exit_date")["net_return"], errors="coerce").dropna()
        if r.empty:
            continue
        rows.append({
            "strategy": strategy,
            "year": int(year),
            "observations": len(r),
            "total_return": float((1.0 + r).prod() - 1.0),
            "cagr_252": safe_cagr(r),
            "max_drawdown": max_drawdown(r),
            "mean_daily_return": float(r.mean()),
            "median_daily_return": float(r.median()),
            "p01": float(r.quantile(0.01)),
            "p05": float(r.quantile(0.05)),
            "p95": float(r.quantile(0.95)),
            "p99": float(r.quantile(0.99)),
            "worst_day": float(r.min()),
            "best_day": float(r.max()),
        })
    return pd.DataFrame(rows)


def write_report(
    path: Path,
    daily: pd.DataFrame,
    concentration: pd.DataFrame,
    robustness: pd.DataFrame,
    periods: pd.DataFrame,
    attribution: pd.DataFrame,
) -> None:
    zero = daily[pd.to_numeric(daily["transaction_cost_bps"]).eq(0)].copy()
    summary = zero.groupby("strategy").agg(
        observations=("net_return", "count"),
        average_exposure=("effective_exposure", "mean"),
        average_missing_return_weight=("missing_return_weight", "mean"),
        average_turnover=("turnover_one_way", "mean"),
        max_missing_return_weight=("missing_return_weight", "max"),
    ).reset_index()
    summary["cagr_252"] = summary["strategy"].map({
        s: safe_cagr(g.sort_values("exit_date")["net_return"])
        for s, g in zero.groupby("strategy")
    })

    lines = [
        "# Portfolio experiment: diagnostic audit",
        "",
        "## Scope",
        "",
        "Read-only diagnostic. Does not modify SQLite, Parquet, experiment CSVs, or the original strategy logic.",
        "The script recomputes ticker attribution from the same feature/price inputs and the experiment's target-weight builder. Attribution is approximate and is explicitly not treated as a reconciliation of compounded portfolio wealth.",
        "",
        "## Core diagnostics (0 bps)",
        "",
        summary.to_markdown(index=False, floatfmt=".5f"),
        "",
        "## Concentration of positive daily returns",
        "",
        concentration.to_markdown(index=False, floatfmt=".5f"),
        "",
        "## Removing the best daily observations",
        "",
        "This is a diagnostic stress test only. It is not an investable strategy and must not be interpreted as a corrected backtest.",
        "",
        robustness.to_markdown(index=False, floatfmt=".5f"),
        "",
        "## Calendar-year diagnostics",
        "",
        periods.to_markdown(index=False, floatfmt=".5f"),
        "",
        "## Ticker contribution leaders and laggards",
        "",
        attribution.to_markdown(index=False, floatfmt=".6f") if not attribution.empty else "_Ticker attribution unavailable._",
        "",
        "## Audit limitations and next checks",
        "",
        "- Missing forward OPEN observations are treated as cash by the original simulator. This can create a favourable selection effect. Inspect missing_return_weight and compare results under a strict policy that excludes the entire date or holds the last valid portfolio only if economically justified.",
        "- The original simulator calculates daily simple weighted returns and compounds portfolio equity. Ticker attribution here sums un-compounded weighted returns, so it is a concentration diagnostic, not an exact decomposition of terminal wealth.",
        "- The experiment uses adjusted OPEN prices. Corporate-action adjustment correctness must be audited separately against raw bars and the adjustment register, especially around extreme daily returns.",
        "- This audit does not model market impact, bid/ask spread, taxes, lot sizes, partial fills, suspensions, or price limits.",
        "- Signal/entry/exit alignment is T close -> T+1 OPEN -> T+2 OPEN. This is checked from the code's date map but not independently verified against exchange execution feasibility.",
        "- If the extreme result remains after these checks, next step is a strict execution audit: ticker/date-level order eligibility, corporate actions, and independent return reconstruction.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if not DAILY_PATH.is_file():
        raise FileNotFoundError(
            f"Experiment output not found: {DAILY_PATH}. Run run_experiment.py first."
        )
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    log("Loading experiment daily results...")
    daily = pd.read_csv(DAILY_PATH, parse_dates=["signal_date", "execution_date", "exit_date"])
    require_columns(
        daily,
        [
            "strategy", "signal_date", "execution_date", "exit_date",
            "gross_return", "net_return", "turnover_one_way",
            "transaction_cost_bps", "effective_exposure",
            "missing_return_weight", "equity_net", "constituents",
        ],
        "daily_equity_curves.csv",
    )

    log("Calculating daily concentration and extremes...")
    concentration = concentration_report(daily)
    extremes = daily_extremes(daily)
    robustness = robustness_report(daily)
    periods = period_metrics(daily)

    log("Reconstructing PIT weights and ticker-level contribution diagnostics...")
    features, breadth, asset_returns, date_map = load_inputs()
    weight_frames, specs = build_target_weights(features, breadth)
    attribution = ticker_attribution(
        features, weight_frames, asset_returns, daily
    )

    concentration.to_csv(AUDIT_DIR / "daily_concentration.csv", index=False, encoding="utf-8-sig")
    extremes.to_csv(AUDIT_DIR / "daily_extremes_top20.csv", index=False, encoding="utf-8-sig")
    robustness.to_csv(AUDIT_DIR / "best_day_removal_stress.csv", index=False, encoding="utf-8-sig")
    periods.to_csv(AUDIT_DIR / "calendar_year_diagnostics.csv", index=False, encoding="utf-8-sig")
    attribution.to_csv(AUDIT_DIR / "ticker_contribution_diagnostics.csv", index=False, encoding="utf-8-sig")

    report_path = AUDIT_DIR / "audit_report.md"
    write_report(report_path, daily, concentration, robustness, periods, attribution)

    log("=" * 72)
    log("AUDIT DIAGNOSTICS COMPLETE")
    log(f"Report: {report_path}")
    log(f"Output directory: {AUDIT_DIR}")
    log("Source databases and original experiment outputs were not modified.")
    log("=" * 72)


if __name__ == "__main__":
    main()
