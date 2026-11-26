from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PANEL = ROOT / "data" / "processed" / "top50" / "top50_panel.parquet"
DEFAULT_OUT = ROOT / "data" / "interim" / "one_use" / "regime_check"
REQUIRED = {"tradedate", "secid", "adjusted_close", "bar_available"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Descriptive confirmation/falsification checks for the Russian equity regime hypothesis."
    )
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--start-date", default="2010-01-01")
    parser.add_argument("--recent-start", default=None,
                        help="Optional start date for a recent subperiod, e.g. 2026-07-01.")
    parser.add_argument("--market-context", type=Path, default=None,
                        help="Optional CSV: tradedate, imoex_return, brent_return, usdrub_return, key_rate, inflation.")
    parser.add_argument("--fundamentals", type=Path, default=None,
                        help="Optional manually curated company evidence CSV. Narrative, not automated fundamentals.")
    return parser.parse_args()


def write_templates(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    narrative = out_dir / "manual_fundamental_evidence_template.csv"
    if not narrative.exists():
        pd.DataFrame(columns=[
            "as_of_date", "secid", "period", "metric_or_claim",
            "value", "unit", "direction", "source_url_or_document",
            "publication_date", "analyst_note", "evidence_strength"
        ]).to_csv(narrative, index=False, encoding="utf-8-sig")
    market = out_dir / "market_context_template.csv"
    if not market.exists():
        pd.DataFrame(columns=[
            "tradedate", "imoex_return", "brent_return",
            "usdrub_return", "key_rate", "inflation"
        ]).to_csv(market, index=False, encoding="utf-8-sig")


def load_panel(path: Path, start_date: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Panel not found: {path}")
    df = pd.read_parquet(path)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Panel missing required columns: {sorted(missing)}")

    df = df.copy()
    df["tradedate"] = pd.to_datetime(df["tradedate"], errors="coerce")
    df["adjusted_close"] = pd.to_numeric(df["adjusted_close"], errors="coerce")
    df["bar_available"] = pd.to_numeric(df["bar_available"], errors="coerce").fillna(0).astype(int)
    df["secid"] = df["secid"].astype(str).str.upper()
    df = df.dropna(subset=["tradedate"]).sort_values(["secid", "tradedate"])
    df = df[df["tradedate"] >= pd.Timestamp(start_date)].copy()

    if df.duplicated(["tradedate", "secid"]).any():
        raise ValueError("Duplicate SECID/date rows in panel.")
    if not df["bar_available"].isin([0, 1]).all():
        raise ValueError("bar_available must be binary.")
    return df


def build_returns(panel: pd.DataFrame) -> pd.DataFrame:
    dates = pd.DatetimeIndex(sorted(panel["tradedate"].unique()))
    date_pos = pd.Series(np.arange(len(dates)), index=dates)
    x = panel.copy()
    x["_date_pos"] = x["tradedate"].map(date_pos)
    x["_prev_close"] = x.groupby("secid")["adjusted_close"].shift(1)
    x["_prev_available"] = x.groupby("secid")["bar_available"].shift(1)
    x["_prev_date_pos"] = x.groupby("secid")["_date_pos"].shift(1)

    consecutive = (x["_date_pos"] - x["_prev_date_pos"]) == 1
    valid = (
        (x["bar_available"] == 1)
        & (x["_prev_available"] == 1)
        & (x["adjusted_close"] > 0)
        & (x["_prev_close"] > 0)
        & consecutive
    )
    x["simple_return"] = np.where(valid, x["adjusted_close"] / x["_prev_close"] - 1.0, np.nan)
    x["log_return"] = np.where(valid, np.log(x["adjusted_close"] / x["_prev_close"]), np.nan)
    return x


def daily_breadth(returns: pd.DataFrame) -> pd.DataFrame:
    valid = returns.dropna(subset=["simple_return"]).copy()
    if valid.empty:
        raise ValueError("No valid adjacent-session returns in selected period.")

    def summarize(g: pd.DataFrame) -> pd.Series:
        r = g["simple_return"].to_numpy(dtype=float)
        positive = np.clip(r, 0, None)
        pos_sum = positive.sum()
        shares = positive / pos_sum if pos_sum > 0 else np.zeros_like(positive)
        ordered = np.sort(shares)[::-1]
        return pd.Series({
            "n_valid": len(r),
            "breadth_positive": np.mean(r > 0),
            "breadth_negative": np.mean(r < 0),
            "breadth_zero": np.mean(r == 0),
            "equal_weight_return": np.mean(r),
            "median_return": np.median(r),
            "cross_sectional_std": np.std(r, ddof=1) if len(r) > 1 else np.nan,
            "positive_return_share_top1": ordered[:1].sum(),
            "positive_return_share_top5": ordered[:5].sum(),
            "positive_return_share_top10": ordered[:10].sum(),
            "positive_return_hhi": np.square(shares).sum(),
            "top10_positive_contribution_count": min(10, len(r)),
        })

    out = valid.groupby("tradedate", sort=True).apply(summarize, include_groups=False).reset_index()
    out["tradedate"] = pd.to_datetime(out["tradedate"])
    return out


def period_summary(daily: pd.DataFrame, recent_start: str | None) -> pd.DataFrame:
    groups = [("full_sample", daily)]
    if recent_start:
        recent = daily[daily["tradedate"] >= pd.Timestamp(recent_start)]
        if not recent.empty:
            groups.append(("recent_subperiod", recent))
    rows = []
    for name, g in groups:
        rows.append({
            "period": name,
            "start": g["tradedate"].min().date().isoformat(),
            "end": g["tradedate"].max().date().isoformat(),
            "n_sessions": len(g),
            "mean_breadth_positive": g["breadth_positive"].mean(),
            "median_breadth_positive": g["breadth_positive"].median(),
            "share_sessions_breadth_gt_50pct": (g["breadth_positive"] > 0.5).mean(),
            "mean_equal_weight_return": g["equal_weight_return"].mean(),
            "mean_median_return": g["median_return"].mean(),
            "mean_top5_positive_share": g["positive_return_share_top5"].mean(),
            "mean_top10_positive_share": g["positive_return_share_top10"].mean(),
            "mean_positive_return_hhi": g["positive_return_hhi"].mean(),
        })
    return pd.DataFrame(rows)


def merge_market_context(daily: pd.DataFrame, path: Path | None, out_dir: Path) -> tuple[pd.DataFrame, dict]:
    if path is None:
        template = out_dir / "market_context_template.csv"
        return daily, {"status": "NOT_PROVIDED", "template": str(template)}
    if not path.exists():
        raise FileNotFoundError(f"Market context file not found: {path}")
    m = pd.read_csv(path)
    if "tradedate" not in m:
        raise ValueError("Market context CSV requires tradedate.")
    m["tradedate"] = pd.to_datetime(m["tradedate"], errors="coerce")
    m = m.dropna(subset=["tradedate"])
    if m["tradedate"].duplicated().any():
        raise ValueError("Duplicate tradedate in market context CSV.")
    merged = daily.merge(m, on="tradedate", how="left", validate="one_to_one")
    correlations = {}
    for col in ["imoex_return", "brent_return", "usdrub_return"]:
        if col in merged and merged[col].notna().sum() >= 30:
            pair = merged[["equal_weight_return", col]].dropna()
            correlations[col] = {
                "n": len(pair),
                "pearson": pair.corr(method="pearson").iloc[0, 1],
                "spearman": pair.corr(method="spearman").iloc[0, 1],
            }
    return merged, {"status": "LOADED", "rows": len(m), "correlations": correlations}


def inspect_fundamentals(path: Path | None, out_dir: Path) -> dict:
    if path is None:
        path = out_dir / "manual_fundamental_evidence_template.csv"
    if not path.exists():
        return {"status": "NOT_PROVIDED", "path": str(path), "note": "No automated fundamental claims are made."}
    df = pd.read_csv(path)
    if df.empty:
        return {"status": "EMPTY_TEMPLATE", "path": str(path), "rows": 0,
                "note": "Fundamental evidence must be manually entered and source-linked."}
    return {
        "status": "MANUAL_EVIDENCE_PRESENT",
        "path": str(path),
        "rows": len(df),
        "securities": int(df["secid"].nunique()) if "secid" in df else None,
        "source_link_coverage": float(df["source_url_or_document"].notna().mean())
            if "source_url_or_document" in df else None,
        "note": "Narrative/hand-entered evidence only; no automated accounting validation.",
    }


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_templates(args.output_dir)

    panel = load_panel(args.panel, args.start_date)
    returns = build_returns(panel)
    daily = daily_breadth(returns)
    periods = period_summary(daily, args.recent_start)
    daily, market_meta = merge_market_context(daily, args.market_context, args.output_dir)
    fundamental_meta = inspect_fundamentals(args.fundamentals, args.output_dir)

    valid = returns.dropna(subset=["simple_return"])
    security = valid.groupby("secid").agg(
        n_observations=("simple_return", "size"),
        mean_return=("simple_return", "mean"),
        median_return=("simple_return", "median"),
        positive_fraction=("simple_return", lambda s: (s > 0).mean()),
    ).reset_index()

    daily.to_csv(args.output_dir / "daily_regime_metrics.csv", index=False, encoding="utf-8-sig")
    periods.to_csv(args.output_dir / "period_summary.csv", index=False, encoding="utf-8-sig")
    security.to_csv(args.output_dir / "security_return_summary.csv", index=False, encoding="utf-8-sig")

    metadata = {
        "hypothesis": "The market rebound does not yet establish a broad, durable improvement in the fundamental regime.",
        "as_of_run": pd.Timestamp.now(tz="UTC").isoformat(),
        "input_panel": str(args.panel.resolve()),
        "input_rows": len(panel),
        "date_start": panel["tradedate"].min().date().isoformat(),
        "date_end": panel["tradedate"].max().date().isoformat(),
        "securities": int(panel["secid"].nunique()),
        "sessions": int(panel["tradedate"].nunique()),
        "valid_adjacent_session_returns": len(valid),
        "return_rule": "Adjusted close-to-close return only when both bars are available and the observations are on adjacent panel sessions; no forward fill or gap bridging.",
        "universe_rule": "Existing point-in-time TOP50 panel; daily equal-weight cross-section, not official IMOEX weights.",
        "market_context": market_meta,
        "fundamental_evidence": fundamental_meta,
        "limitations": [
            "TOP50 equal-weight breadth is not the MOEX index and cannot reproduce index constituent weights.",
            "No sector classification is assumed; sector concentration is not measured unless a reliable mapping is added separately.",
            "No machine-readable company reports are available. Fundamentals are narrative/manual and must be source-linked.",
            "Return breadth and concentration metrics cannot by themselves establish fundamental improvement or deterioration.",
            "Correlations with optional market drivers are descriptive, not causal.",
        ],
        "outputs": [
            "daily_regime_metrics.csv",
            "period_summary.csv",
            "security_return_summary.csv",
            "manual_fundamental_evidence_template.csv",
            "market_context_template.csv",
        ],
    }
    (args.output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2, default=str))
    print(f"\nOutputs: {args.output_dir}")


if __name__ == "__main__":
    main()
