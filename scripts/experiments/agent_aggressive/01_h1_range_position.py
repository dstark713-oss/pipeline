# -*- coding: utf-8 -*-
"""
Agent: Aggressive Trading | H1: 60-session range position -> 5-session fwd return
Stage A: confirm | Stage B: falsify (separate runs, separate reports)
Read-only. Deterministic (seed=42 for negative control). Vectorized wide-matrix ops.
Run from repo root:
  python -X utf8 scripts/experiments/agent_aggressive/01_h1_range_position.py confirm
  python -X utf8 scripts/experiments/agent_aggressive/01_h1_range_position.py falsify
"""
from __future__ import annotations
import sys, traceback
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PANEL_REL = Path("data/processed/top50/top50_panel.parquet")
OUT_REL = Path("data/interim/agent_checks")
H, W, MINP, MIN_N, SEED = 5, 60, 40, 20, 42
CRISIS_YEARS = {2008, 2009, 2020, 2022}
L: list[str] = []

def emit(s=""): L.append(str(s))

def find_root() -> Path:
    for b in [Path.cwd(), *Path(__file__).resolve().parents]:
        if (b / PANEL_REL).exists():
            return b
    raise FileNotFoundError("panel not found; run from repo root")

def period_label(years: np.ndarray) -> np.ndarray:
    return np.select(
        [years <= 2009, years <= 2014, years <= 2019, years <= 2021, years <= 2023],
        ["2005-2009", "2010-2014", "2015-2019", "2020-2021", "2022-2023"],
        default="2024-2026")

def rank_ic(x: pd.DataFrame, y: pd.DataFrame):
    m = x.notna() & y.notna()
    xr, yr = x.where(m).rank(axis=1), y.where(m).rank(axis=1)
    xc = xr.sub(xr.mean(axis=1), axis=0)
    yc = yr.sub(yr.mean(axis=1), axis=0)
    den = np.sqrt((xc * xc).sum(axis=1) * (yc * yc).sum(axis=1))
    ic = (xc * yc).sum(axis=1) / den.replace(0, np.nan)
    return ic, m.sum(axis=1)

def ic_stats(ic: pd.Series, tag: str):
    v = ic.dropna().to_numpy()
    if len(v) < 10:
        emit(f"{tag:28s} n={len(v)} INSUFFICIENT"); return
    t_raw = v.mean() / (v.std(ddof=1) / np.sqrt(len(v)))
    emit(f"{tag:28s} n={len(v):5d}  mean={v.mean():+.4f}  med={np.median(v):+.4f}"
         f"  pos={(v > 0).mean() * 100:5.1f}%  t_raw={t_raw:+6.2f}  t_ovlp~{t_raw / np.sqrt(H):+5.2f}")

def strategy(sig, y, ok_dates, cal):
    pct = sig.where(sig.notna() & y.notna()).rank(axis=1, pct=True)
    rd = cal[ok_dates.to_numpy()][::H]
    rows, prev = [], set()
    for d in rd:
        p, yy = pct.loc[d], y.loc[d]
        sel = p[p >= 0.8].index
        if len(sel) == 0:
            continue
        r = float(yy[sel].mean()); b = float(yy.dropna().mean())
        cur = set(sel)
        to = 1.0 if not prev else len(cur - prev) / len(cur)
        rows.append({"date": d, "port": r, "base": b, "turnover": to, "n": len(sel)})
        prev = cur
    return pd.DataFrame(rows)

def main(stage: str):
    root = find_root()
    pp = root / PANEL_REL; st = pp.stat()
    df = pd.read_parquet(pp)
    df["tradedate"] = pd.to_datetime(df["tradedate"])
    close = df.pivot(index="tradedate", columns="secid", values="adjusted_close").sort_index()
    value = df.pivot(index="tradedate", columns="secid", values="value").reindex_like(close)
    opn = df.pivot(index="tradedate", columns="secid", values="adjusted_open").reindex_like(close)
    memb = df.assign(_o=1.0).pivot(index="tradedate", columns="secid", values="_o").reindex_like(close)
    v60 = df.pivot(index="tradedate", columns="secid", values="value_60d").reindex_like(close)
    cal = close.index
    per = pd.Series(period_label(cal.year.to_numpy()), index=cal)

    max60 = close.rolling(W, min_periods=MINP).max()
    pos = close / max60
    med60v = value.rolling(W, min_periods=MINP).median().shift(1)
    abv = value / med60v.where(med60v > 0)
    fwd = close.shift(-H) / close - 1.0
    valid = close.notna() & (close > 0) & (value > 0) & max60.notna() & (memb == 1)
    sig, y = pos.where(valid), fwd.where(valid)
    pairs = sig.notna() & y.notna()
    ok = pairs.sum(axis=1) >= MIN_N
    ic_all, _ = rank_ic(sig, y)
    ic_ok = ic_all[ok]

    emit("=" * 72)
    emit(f"AGENT: AGGRESSIVE TRADING | H1 RANGE POSITION | STAGE: {stage.upper()}")
    emit("=" * 72)
    emit(f"run_utc={datetime.now(timezone.utc).isoformat()}  asof={cal[-1].date()}")
    emit(f"panel_mtime_utc={datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()}")
    emit(f"params: H={H} W={W} MINP={MINP} MIN_N={MIN_N} seed={SEED}")
    emit(f"dates={len(cal)}  ok_dates(n>={MIN_N})={int(ok.sum())}  paired_rows={int(pairs.to_numpy().sum())}")
    emit("ok_dates by period: " + per[ok].value_counts().sort_index().to_dict().__str__())
    emit("NOTE: panel-only history; windows are market sessions; no forward-fill.")
    emit("NOTE: t_ovlp is a heuristic sqrt(H) deflation for overlapping windows, not rigorous NW.")

    if stage == "confirm":
        emit("\n[C1] RANK IC: pos vs fwd5")
        ic_stats(ic_ok, "ALL ok dates")
        for p in sorted(per.unique()):
            ic_stats(ic_ok[per[ok] == p], p)

        emit("\n[C2] DECILES of pos -> mean fwd5 (pooled) and daily Q10-Q1")
        pct = sig.where(pairs).rank(axis=1, pct=True)
        qmeans = {}
        for b in range(1, 11):
            m = (pct > (b - 1) / 10) & (pct <= b / 10)
            vals = y.where(m).to_numpy()
            qmeans[b] = float(np.nanmean(vals))
            emit(f"D{b:02d}  n={int(np.isfinite(vals).sum()):7d}  mean_fwd5={qmeans[b] * 1e4:+8.1f} bp")
        spread = y.where(pct > 0.9).mean(axis=1) - y.where(pct <= 0.1).mean(axis=1)
        sp = spread[ok].dropna().to_numpy()
        emit(f"Q10-Q1 daily: mean={sp.mean() * 1e4:+.1f} bp  t_ovlp~{sp.mean() / (sp.std(ddof=1) / np.sqrt(len(sp))) / np.sqrt(H):+.2f}")
        emit(f"monotonic pairs (Dk<Dk+1): {sum(qmeans[k] < qmeans[k + 1] for k in range(1, 10))}/9")

        emit("\n[C3] H1b: turnover regimes (abv = value / trailing 60d median)")
        for tag, m in [("abv>=1.5 (hot)", abv >= 1.5),
                       ("0.8<=abv<1.5 (mid)", (abv >= 0.8) & (abv < 1.5)),
                       ("abv<0.8 (quiet)", abv < 0.8)]:
            icr, nr = rank_ic(sig.where(m), y.where(m))
            icr = icr[nr >= MIN_N]
            ic_stats(icr, tag)

        emit("\n[C4] STRATEGY gross: top quintile pos, equal weight, rebal every 5 sessions")
        s = strategy(sig, y, ok, cal)
        s["per"] = period_label(s["date"].dt.year.to_numpy())
        for p, g in s.groupby("per"):
            eq = (1 + g["port"]).prod() - 1
            eb = (1 + g["base"]).prod() - 1
            emit(f"{p}  reb={len(g):4d}  mean={g['port'].mean() * 1e4:+7.1f} bp  hit={(g['port'] > 0).mean() * 100:4.1f}%"
                 f"  equity={eq * 100:+8.1f}%  base={eb * 100:+8.1f}%  to={g['turnover'].mean() * 100:4.1f}%")
        emit(f"TOTAL  reb={len(s)}  mean={(s['port'].mean()) * 1e4:+.1f} bp  edge_vs_base={(s['port'] - s['base']).mean() * 1e4:+.1f} bp"
             f"  equity={(1 + s['port']).prod() - 1:+.2f}x  base={(1 + s['base']).prod() - 1:+.2f}x")

        emit(f"\n[C5] PREVIEW @ {cal[-1].date()} (NOT a decision; checks pending)")
        cur = df[df["tradedate"] == cal[-1]].set_index("secid")
        last_pos = pos.loc[cal[-1]].rename("pos")
        last_abv = abv.loc[cal[-1]].rename("abv")
        snap = cur.join(last_pos).join(last_abv).sort_values("pos", ascending=False)
        emit(snap[["rank", "pos", "abv", "adjusted_close"]].head(15).round(4).to_string())

    else:  # falsify
        emit("\n[F1] ROLLING IC stability (250-session mean)")
        roll = ic_ok.rolling(250).mean().dropna()
        emit(f"windows={len(roll)}  share_negative={(roll < 0).mean() * 100:.1f}%  min={roll.min():+.4f}  last={roll.iloc[-1]:+.4f}")
        for p in sorted(per.unique()):
            v = ic_ok[per[ok] == p].dropna().to_numpy()
            if len(v) >= 10:
                emit(f"{p}  mean={v.mean():+.4f}  std={v.std():.4f}  worst_day={v.min():+.3f}")

        emit("\n[F2] CRISIS EXCLUSION (drop 2008,2009,2020,2022)")
        keep = ok & ~pd.Series(cal.year.isin(CRISIS_YEARS), index=cal)
        ic_stats(ic_all[keep], "ex-crisis")
        s2 = strategy(sig, y, keep, cal)
        emit(f"ex-crisis strategy: reb={len(s2)}  mean={s2['port'].mean() * 1e4:+.1f} bp  edge={(s2['port'] - s2['base']).mean() * 1e4:+.1f} bp")

        emit("\n[F3] CONCENTRATION")
        xr = sig.where(pairs).rank(axis=0); yr = y.where(pairs).rank(axis=0)
        xc = xr.sub(xr.mean(axis=0), axis=1); yc = yr.sub(yr.mean(axis=0), axis=1)
        den = np.sqrt((xc * xc).sum(axis=0) * (yc * yc).sum(axis=0))
        tic = ((xc * yc).sum(axis=0) / den.replace(0, np.nan))
        nobs = pairs.sum(axis=0)
        tic = tic[nobs >= 250]
        emit(f"per-ticker IC (n>=250): tickers={len(tic)}  median={tic.median():+.4f}  share_pos={(tic > 0).mean() * 100:.1f}%")
        top10 = v60.mean(axis=0).nlargest(10).index.tolist()
        emit("top10 by mean value_60d: " + ",".join(top10))
        ic_x, nx = rank_ic(sig.drop(columns=top10), y.drop(columns=top10))
        ic_stats(ic_x[nx >= MIN_N], "ex-top10 megacaps")
        cheap = close < 1.0
        ic_c, nc = rank_ic(sig.where(~cheap), y.where(~cheap))
        ic_stats(ic_c[nc >= MIN_N], "ex-price<1RUB rows")

        emit("\n[F4] DEFINITION SENSITIVITY: mean rank IC, windows x horizons")
        for w in (40, 60, 120):
            mw = close.rolling(w, min_periods=max(20, w * 2 // 3)).max()
            pw = (close / mw).where(valid)
            row = []
            for h in (3, 5, 10):
                fh = (close.shift(-h) / close - 1.0).where(valid)
                icg, ng = rank_ic(pw, fh)
                v = icg[ng >= MIN_N].dropna()
                row.append(f"h{h}:{v.mean():+.4f}")
            emit(f"W={w:3d}  " + "  ".join(row))

        emit("\n[F4b] EXECUTION LAG: entry next open, exit close t+5")
        entry = opn.shift(-1)
        fxe = (close.shift(-H) / entry - 1.0).where(valid & (entry > 0))
        ice, ne = rank_ic(sig, fxe)
        ic_stats(ice[ne >= MIN_N], "open-entry IC")

        emit("\n[F5] NEGATIVE CONTROL: shuffle fwd returns within date (seed=42)")
        rng = np.random.default_rng(SEED)
        yv = y.to_numpy().copy(); pm = pairs.to_numpy()
        for i in range(yv.shape[0]):
            vals = yv[i, pm[i]]
            rng.shuffle(vals)
            yv[i, pm[i]] = vals
        icn, nn = rank_ic(sig, pd.DataFrame(yv, index=cal, columns=close.columns))
        ic_stats(icn[nn >= MIN_N], "shuffled (expect ~0)")

        emit("\n[F6] CENSORING: signal valid but fwd5 missing")
        cens = valid & fwd.isna()
        m5 = memb.shift(-H)
        emit(f"censored_rows={int(cens.to_numpy().sum())}  of_valid={cens.to_numpy().sum() / max(1, valid.to_numpy().sum()) * 100:.2f}%")
        emit(f"  not_member_at_t5={int((cens & (m5 != 1)).to_numpy().sum())}  member_but_no_bar={int((cens & (m5 == 1)).to_numpy().sum())}")
        ycont = y.where(m5 == 1)
        icq, nq = rank_ic(sig, ycont)
        ic_stats(icq[nq >= MIN_N], "continuous-membership only")

        emit("\n[F7] COSTS (scenarios, NOT broker facts): top-quintile strategy")
        s = strategy(sig, y, ok, cal)
        to = s["turnover"].mean(); gross = s["port"].mean(); edge = (s["port"] - s["base"]).mean()
        emit(f"mean_turnover={to * 100:.1f}%/rebal  gross={gross * 1e4:+.1f} bp  edge_vs_base={edge * 1e4:+.1f} bp")
        for c in (0.0005, 0.0010, 0.0020):
            emit(f"one-way {c * 1e4:.0f} bp: net_abs={(gross - 2 * to * c) * 1e4:+7.1f} bp  net_edge={(edge - 2 * to * c) * 1e4:+7.1f} bp")
        emit(f"breakeven one-way: abs={gross / (2 * to) * 1e4:.1f} bp  vs_base={edge / (2 * to) * 1e4:.1f} bp")

    emit("\nEND OF REPORT")

if __name__ == "__main__":
    stage = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if stage not in ("confirm", "falsify"):
        print("usage: python 01_h1_range_position.py confirm|falsify"); sys.exit(1)
    try:
        main(stage)
    except Exception:
        emit("\nERROR:\n" + traceback.format_exc())
    rep = "\n".join(L)
    print(rep)
    try:
        out = find_root() / OUT_REL / f"aggressive_01_h1_{stage}.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rep, encoding="utf-8")
        print(f"\n[saved] {out}")
    except Exception as e:
        print(f"[report not saved] {e}")