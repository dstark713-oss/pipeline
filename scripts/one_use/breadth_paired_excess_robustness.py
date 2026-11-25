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
LQDT_CSV = ROOT / "data/interim/position_exit_audit/lqdt_moex_iss_daily.csv"
OUT = ROOT / "data/interim/breadth_paired_excess_robustness"
TABLE = "adjusted_daily_bars"
BOARDS = ("TQBR", "EQBR")
SUSPEND = (pd.Timestamp("2022-02-28"), pd.Timestamp("2022-03-23"))
TICKERS = ("T", "GCHE")
HORIZONS = (1, 5, 20)
THRESHOLDS = (0.05, 0.10, 0.15)


def norm_date(values):
    return pd.to_datetime(values, errors="coerce").dt.normalize()


def load_inputs():
    panel = pd.read_parquet(PANEL)[["tradedate", "secid", "bar_available"]].copy()
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
                ORDER BY tradedate, secid, boardid""",
            con, params=list(BOARDS),
        )
    bars["tradedate"] = norm_date(bars["tradedate"])
    bars["adjusted_close"] = pd.to_numeric(bars["adjusted_close"], errors="coerce")
    bars = bars.dropna(subset=["tradedate", "secid"])
    bars = bars[(bars.tradedate < SUSPEND[0]) | (bars.tradedate > SUSPEND[1])]
    bars = bars.sort_values(
        ["tradedate", "secid", "boardid"],
        key=lambda x: x.map({"TQBR": 0, "EQBR": 1}) if x.name == "boardid" else x,
    )
    bars = bars.drop_duplicates(["tradedate", "secid"], keep="first")
    close = bars.pivot(index="tradedate", columns="secid", values="adjusted_close").sort_index()

    if not LQDT_CSV.exists():
        raise FileNotFoundError(
            f"{LQDT_CSV} not found. Run position_exit_audit.py first to fetch LQDT from MOEX ISS."
        )
    lqdt = pd.read_csv(LQDT_CSV)
    cols = {c.lower(): c for c in lqdt.columns}
    date_col = cols.get("date") or cols.get("tradedate")
    if not date_col or "close" not in cols:
        raise ValueError("LQDT ISS CSV must contain date and close columns")
    lqdt["date"] = pd.to_datetime(lqdt[date_col], errors="coerce").dt.normalize()
    lqdt["close"] = pd.to_numeric(lqdt[cols["close"]], errors="coerce")
    lqdt = lqdt.dropna(subset=["date", "close"]).drop_duplicates("date").sort_values("date")
    lqdt_ret = lqdt.set_index("date")["close"].pct_change(fill_method=None).rename("LQDT")
    calendar = close.index.intersection(breadth.index).sort_values()
    close = close.reindex(calendar)
    breadth = breadth.reindex(calendar)
    returns = close.pct_change(fill_method=None)

    # Rebuild the same daily PIT equal-weight TOP50 reference used in position_exit_audit.py.
    members = panel[panel.tradedate.isin(calendar)]
    ew_rows = []
    for date, group in members.groupby("tradedate"):
        names = group.secid.tolist()
        available = returns.columns.intersection(names)
        values = returns.loc[date, available].dropna()
        ew_rows.append((date, values.mean() if len(values) else np.nan, len(values)))
    ew = pd.DataFrame(ew_rows, columns=["date", "EW_TOP50", "ew_n"]).set_index("date")
    series = {"LQDT": lqdt_ret.reindex(calendar), "EW_TOP50": ew["EW_TOP50"].reindex(calendar)}
    for ticker in TICKERS:
        if ticker in returns.columns:
            series[ticker] = returns[ticker]
    return calendar, breadth["breadth"], series, lqdt


def forward_return(daily_returns: pd.Series, horizon: int) -> pd.Series:
    # At signal date t, compound returns on the next h trading sessions: t+1 ... t+h.
    return (1.0 + daily_returns).rolling(horizon, min_periods=horizon).apply(
        np.prod, raw=True
    ).shift(-horizon) - 1.0


def episode_labels(low_mask: np.ndarray) -> tuple[np.ndarray, int]:
    labels = np.full(len(low_mask), -1, dtype=int)
    episode = -1
    in_episode = False
    for i, flag in enumerate(low_mask):
        if flag and not in_episode:
            episode += 1
            in_episode = True
        elif not flag:
            in_episode = False
        if flag:
            labels[i] = episode
    return labels, episode + 1


def hac_ci(values: np.ndarray, valid: np.ndarray, lag: int) -> tuple[float, float]:
    n_total = len(values)
    count = int(valid.sum())
    if count < 10 or n_total < 20:
        return np.nan, np.nan
    mean = float(values[valid].mean())
    # Ratio-estimator influence series on the full trading-day calendar.
    p = count / n_total
    influence = np.zeros(n_total, dtype=float)
    influence[valid] = values[valid] - mean
    lrv = float(np.dot(influence, influence) / n_total)
    max_lag = min(lag, n_total - 1)
    for k in range(1, max_lag + 1):
        weight = 1.0 - k / (max_lag + 1.0)
        gamma = float(np.dot(influence[k:], influence[:-k]) / n_total)
        lrv += 2.0 * weight * gamma
    se = np.sqrt(max(lrv, 0.0) / n_total) / p
    return mean - 1.96 * se, mean + 1.96 * se


def block_bootstrap_ci(
    values: np.ndarray, valid: np.ndarray, block: int, reps: int, rng: np.random.Generator
) -> tuple[float, float]:
    n = len(values)
    if int(valid.sum()) < 10 or n < block:
        return np.nan, np.nan
    n_blocks = int(np.ceil(n / block))
    offsets = np.arange(block)
    estimates = []
    starts_max = n - block
    for _ in range(reps):
        starts = rng.integers(0, starts_max + 1, size=n_blocks)
        idx = (starts[:, None] + offsets[None, :]).reshape(-1)[:n]
        sampled_valid = valid[idx]
        if sampled_valid.sum() >= 10:
            estimates.append(float(values[idx][sampled_valid].mean()))
    if len(estimates) < reps * 0.8:
        return np.nan, np.nan
    return tuple(np.quantile(estimates, [0.025, 0.975]).tolist())


def summarize(
    asset_fwd: pd.Series,
    lqdt_fwd: pd.Series,
    breadth: pd.Series,
    threshold: float,
    hac_lag: int,
    block: int,
    reps: int,
    rng: np.random.Generator,
) -> dict:
    frame = pd.concat(
        [asset_fwd.rename("asset"), lqdt_fwd.rename("lqdt"), breadth.rename("breadth")],
        axis=1,
    )
    excess = (frame["asset"] - frame["lqdt"]).to_numpy(dtype=float)
    low = (frame["breadth"].to_numpy(dtype=float) <= threshold)
    valid = low & np.isfinite(excess)
    selected = excess[valid]
    labels, n_episodes = episode_labels(low & np.isfinite(frame["breadth"].to_numpy(dtype=float)))
    selected_labels = labels[valid]
    largest_episode = -1
    largest_n = 0
    if len(selected_labels):
        ids, counts = np.unique(selected_labels[selected_labels >= 0], return_counts=True)
        if len(ids):
            largest_episode = int(ids[np.argmax(counts)])
            largest_n = int(counts.max())
    without_largest = valid.copy()
    if largest_episode >= 0:
        without_largest &= labels != largest_episode
    hac_low, hac_high = hac_ci(excess, valid, hac_lag)
    boot_low, boot_high = block_bootstrap_ci(excess, valid, block, reps, rng)
    return {
        "n": int(valid.sum()),
        "episodes": int(n_episodes),
        "mean_excess": float(np.mean(selected)) if len(selected) else np.nan,
        "median_excess": float(np.median(selected)) if len(selected) else np.nan,
        "sd_excess": float(np.std(selected, ddof=1)) if len(selected) > 1 else np.nan,
        "positive_share": float(np.mean(selected > 0)) if len(selected) else np.nan,
        "hac95_low": hac_low,
        "hac95_high": hac_high,
        "block95_low": boot_low,
        "block95_high": boot_high,
        "largest_episode_n": largest_n,
        "mean_ex_ex_largest": float(np.mean(excess[without_largest])) if without_largest.any() else np.nan,
    }


def pct(x):
    return "NA" if not np.isfinite(x) else f"{x:+.3%}"


def main():
    parser = argparse.ArgumentParser(
        description="Robustness audit of paired asset-minus-LQDT forward returns under low breadth."
    )
    parser.add_argument("--bootstrap-reps", type=int, default=1000)
    parser.add_argument("--block-length", type=int, default=20)
    parser.add_argument("--hac-lag", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261125)
    args = parser.parse_args()
    if args.bootstrap_reps < 100 or args.block_length < 2 or args.hac_lag < 0:
        raise ValueError("Use bootstrap-reps >=100, block-length >=2 and hac-lag >=0")

    for path in (PANEL, FEATURES, DB):
        if not path.exists():
            raise FileNotFoundError(path)
    calendar, breadth, daily = load_inputs()
    lqdt_daily = daily["LQDT"]
    rng = np.random.default_rng(args.seed)
    rows = []
    report = [
        f"Snapshot: {calendar.max().date()} | calendar sessions={len(calendar)}",
        f"LQDT ISS candles={sum(1 for _ in open(LQDT_CSV, encoding='utf-8')) - 1} rows | aligned daily returns={int(lqdt_daily.notna().sum())}",
        f"Bootstrap: moving blocks, length={args.block_length}, reps={args.bootstrap_reps}, seed={args.seed}",
        f"HAC: Newey-West Bartlett, lag={args.hac_lag}",
        "Metric: paired forward excess = asset(t+1..t+h) minus LQDT(t+1..t+h), conditioned on breadth at t.",
        "All intervals are descriptive uncertainty estimates, not out-of-sample guarantees.",
    ]

    for horizon in HORIZONS:
        lqdt_fwd = forward_return(lqdt_daily, horizon)
        for asset in ("T", "GCHE", "EW_TOP50"):
            if asset not in daily:
                continue
            asset_fwd = forward_return(daily[asset], horizon)
            for threshold in THRESHOLDS:
                result = summarize(
                    asset_fwd, lqdt_fwd, breadth, threshold,
                    args.hac_lag, args.block_length, args.bootstrap_reps, rng,
                )
                rows.append({"asset": asset, "horizon": horizon, "threshold": threshold, **result})
                if threshold == 0.10:
                    report.append(
                        f"{asset} H{horizon} | n={result['n']} episodes={result['episodes']} "
                        f"mean={pct(result['mean_excess'])} median={pct(result['median_excess'])} "
                        f"positive={result['positive_share']:.1%} "
                        f"HAC95=[{pct(result['hac95_low'])}, {pct(result['hac95_high'])}] "
                        f"block95=[{pct(result['block95_low'])}, {pct(result['block95_high'])}] "
                        f"largest_episode_n={result['largest_episode_n']} "
                        f"mean_ex_largest={pct(result['mean_ex_ex_largest'])}"
                    )

    result_df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(OUT / "paired_excess_robustness.csv", index=False)
    text = "\n".join(report)
    (OUT / "paired_excess_robustness_report.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\nThreshold sensitivity and full metrics: {OUT.relative_to(ROOT)}/paired_excess_robustness.csv")
    print(f"Report: {OUT.relative_to(ROOT)}/paired_excess_robustness_report.txt")


if __name__ == "__main__":
    main()
