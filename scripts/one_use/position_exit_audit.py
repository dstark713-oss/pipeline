from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "data/processed/top50/top50_panel.parquet"
FEATURES = ROOT / "data/interim/primitive_research/primitive_features.parquet"
DB = ROOT / "data/processed/moex_daily_adjusted.sqlite"
OUT = ROOT / "data/interim/position_exit_audit"
TABLE = "adjusted_daily_bars"
BOARDS = ("TQBR", "EQBR")
SUSPEND = (pd.Timestamp("2022-02-28"), pd.Timestamp("2022-03-23"))
HORIZONS = (1, 5, 20)


def norm_date(s):
    return pd.to_datetime(s, errors="coerce").dt.normalize()


def load_market():
    panel = pd.read_parquet(PANEL)
    panel = panel[["tradedate", "secid", "bar_available"]].copy()
    panel["tradedate"] = norm_date(panel["tradedate"])
    panel["secid"] = panel["secid"].astype(str).str.strip().str.upper()
    panel["bar_available"] = pd.to_numeric(panel["bar_available"], errors="coerce").fillna(0)
    panel = panel.dropna(subset=["tradedate", "secid"])
    panel = panel[panel.bar_available.eq(1)]
    if panel.duplicated(["tradedate", "secid"]).any():
        raise ValueError("Duplicate PIT panel keys")

    feat = pd.read_parquet(FEATURES)[["tradedate", "secid", "price_sma20"]].copy()
    feat["tradedate"] = norm_date(feat["tradedate"])
    feat["secid"] = feat["secid"].astype(str).str.strip().str.upper()
    feat["price_sma20"] = pd.to_numeric(feat["price_sma20"], errors="coerce")
    feat = feat.dropna(subset=["tradedate", "secid"])
    hist = panel.merge(feat, on=["tradedate", "secid"], how="left", validate="one_to_one")
    breadth = hist.groupby("tradedate").agg(
        breadth=("price_sma20", lambda x: (x.dropna() > 0).mean() if x.notna().any() else np.nan),
        breadth_n=("price_sma20", "count"),
        universe_n=("secid", "nunique"),
    )
    breadth.loc[breadth.breadth_n.eq(0), "breadth"] = np.nan

    marks = ",".join("?" for _ in BOARDS)
    with sqlite3.connect(DB.resolve().as_uri() + "?mode=ro", uri=True) as con:
        con.execute("PRAGMA query_only=ON")
        bars = pd.read_sql_query(
            f"""SELECT UPPER(TRIM(secid)) secid, tradedate, UPPER(TRIM(boardid)) boardid,
                       adjusted_close
                FROM "{TABLE}" WHERE boardid IN ({marks}) AND tradedate IS NOT NULL
                ORDER BY tradedate, secid, boardid""", con, params=list(BOARDS))
    bars["tradedate"] = norm_date(bars["tradedate"])
    bars["adjusted_close"] = pd.to_numeric(bars["adjusted_close"], errors="coerce")
    bars = bars.dropna(subset=["tradedate", "secid"])
    bars = bars[(bars.tradedate < SUSPEND[0]) | (bars.tradedate > SUSPEND[1])]
    bars = bars.sort_values(["tradedate", "secid", "boardid"],
                            key=lambda x: x.map({"TQBR": 0, "EQBR": 1}) if x.name == "boardid" else x)
    bars = bars.drop_duplicates(["tradedate", "secid"], keep="first")
    close = bars.pivot(index="tradedate", columns="secid", values="adjusted_close").sort_index()
    return panel, breadth, close


def load_lqdt(path):
    if not path:
        return None
    x = pd.read_csv(path)
    cols = {c.lower(): c for c in x.columns}
    if "tradedate" not in cols:
        raise ValueError("LQDT CSV must contain tradedate and close or daily_return")
    x["date"] = pd.to_datetime(x[cols["tradedate"]], errors="coerce").dt.normalize()
    if "daily_return" in cols:
        x["lqdt_ret"] = pd.to_numeric(x[cols["daily_return"]], errors="coerce")
    elif "close" in cols:
        close = pd.to_numeric(x[cols["close"]], errors="coerce")
        x["lqdt_ret"] = close.pct_change(fill_method=None)
    else:
        raise ValueError("LQDT CSV needs daily_return or close column")
    return x.dropna(subset=["date"]).set_index("date")["lqdt_ret"].sort_index()


def beta_stats(asset, market, breadth, window):
    frame = pd.concat([asset.rename("asset"), market.rename("market"), breadth["breadth"]], axis=1).dropna()
    frame = frame.tail(window)
    if len(frame) < max(40, window // 2):
        return {"n": len(frame), "beta": np.nan, "corr": np.nan, "low_breadth_beta": np.nan}
    beta = frame.market.cov(frame.asset) / frame.market.var() if frame.market.var() > 0 else np.nan
    low = frame[frame.breadth <= 0.10]
    low_beta = low.market.cov(low.asset) / low.market.var() if len(low) >= 20 and low.market.var() > 0 else np.nan
    return {"n": len(frame), "beta": beta, "corr": frame.asset.corr(frame.market), "low_breadth_beta": low_beta}


def main():
    ap = argparse.ArgumentParser(description="One-off T/GCHE exit audit; no target weights or trade signals.")
    ap.add_argument("--lqdt-csv", help="Optional CSV: tradedate,daily_return OR tradedate,close")
    ap.add_argument("--low-breadth", type=float, default=0.10)
    args = ap.parse_args()

    for p in (PANEL, FEATURES, DB):
        if not p.exists():
            raise FileNotFoundError(p)
    panel, breadth, close = load_market()
    dates = close.index.intersection(breadth.index)
    close = close.loc[dates]
    breadth = breadth.loc[dates]
    ret = close.pct_change(fill_method=None)
    # Equal-weight PIT TOP50 return: membership and actual bars on each signal date.
    members = panel[panel.tradedate.isin(dates)].copy()
    ew_rows = []
    for d, group in members.groupby("tradedate"):
        names = group.secid.tolist()
        available = ret.columns.intersection(names)
        vals = ret.loc[d, available].dropna()
        ew_rows.append((d, vals.mean() if len(vals) else np.nan, len(vals)))
    ew = pd.DataFrame(ew_rows, columns=["date", "ew_ret", "ew_n"]).set_index("date").sort_index()
    market_ret = ew.ew_ret.reindex(dates)

    lqdt = load_lqdt(args.lqdt_csv)
    OUT.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append(f"Snapshot: {dates.max().date()} | breadth: {breadth.loc[dates.max(), 'breadth']:.1%}")
    lines.append("Beta vs daily PIT EW-TOP50 (not a causal estimate):")
    for ticker in ("T", "GCHE"):
        if ticker not in ret:
            lines.append(f"{ticker}: NOT ASSESSABLE (no adjusted-close series)")
            continue
        r = ret[ticker]
        pieces = [f"{ticker}"]
        for w in (120, 250):
            z = beta_stats(r, market_ret, breadth, w)
            pieces.append(f"{w}d beta={z['beta']:.2f} corr={z['corr']:.2f} low-breadth beta={z['low_breadth_beta']:.2f} n={z['n']}")
        lines.append(" | ".join(pieces))

    lines.append(f"Conditional forward returns when breadth <= {args.low_breadth:.0%}:")
    fwd_rows = []
    for h in HORIZONS:
        ew_fwd = (1 + market_ret).rolling(h).apply(np.prod, raw=True).shift(-h) - 1
        sample = pd.concat([ew_fwd.rename("ew_fwd"), breadth.breadth], axis=1).dropna()
        sample = sample[sample.breadth <= args.low_breadth]
        row = {"asset": "EW_TOP50", "horizon": h, "n": len(sample), "asset_mean": sample.ew_fwd.mean()}
        if lqdt is not None:
            lqdt_fwd = (1 + lqdt).rolling(h).apply(np.prod, raw=True).shift(-h) - 1
            joined = pd.concat([ew_fwd.rename("asset"), lqdt_fwd.rename("lqdt"), breadth.breadth], axis=1).dropna()
            joined = joined[joined.breadth <= args.low_breadth]
            row.update({"paired_n": len(joined), "lqdt_mean": joined.lqdt.mean(), "excess_mean": (joined.asset - joined.lqdt).mean()})
        fwd_rows.append(row)
        for ticker in ("T", "GCHE"):
            if ticker not in ret:
                continue
            asset_fwd = (1 + ret[ticker]).rolling(h).apply(np.prod, raw=True).shift(-h) - 1
            aligned = pd.concat([asset_fwd.rename("asset_fwd"), breadth.breadth], axis=1).dropna()
            aligned = aligned[aligned.breadth <= args.low_breadth]
            prow = {"asset": ticker, "horizon": h, "n": len(aligned), "asset_mean": aligned.asset_fwd.mean()}
            if lqdt is not None:
                paired = pd.concat([asset_fwd.rename("asset"), lqdt_fwd.rename("lqdt"), breadth.breadth], axis=1).dropna()
                paired = paired[paired.breadth <= args.low_breadth]
                prow.update({"paired_n": len(paired), "lqdt_mean": paired.lqdt.mean(), "excess_mean": (paired.asset - paired.lqdt).mean()})
            fwd_rows.append(prow)
            lines.append(f"{ticker} H{h}: n={prow['n']} mean={prow['asset_mean']:.3%}" +
                         (f" | paired n={prow.get('paired_n',0)} LQDT={prow.get('lqdt_mean',np.nan):.3%} excess={prow.get('excess_mean',np.nan):+.3%}" if lqdt is not None else " | LQDT: NOT PROVIDED"))
        lines.append(f"EW H{h}: n={row['n']} mean={row['asset_mean']:.3%}" +
                     (f" | paired n={row.get('paired_n',0)} LQDT={row.get('lqdt_mean',np.nan):.3%} excess={row.get('excess_mean',np.nan):+.3%}" if lqdt is not None else " | LQDT: NOT PROVIDED"))
    lines.append("NOTE: descriptive conditional means only; overlapping horizons, no CI, no costs, no alpha attribution. Results are not forecasts.")
    report = "\n".join(lines)
    print(report)
    (OUT / "position_exit_audit_report.txt").write_text(report + "\n", encoding="utf-8")
    pd.DataFrame(fwd_rows).to_csv(OUT / "conditional_ew_summary.csv", index=False)
    print(f"\nSaved: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
