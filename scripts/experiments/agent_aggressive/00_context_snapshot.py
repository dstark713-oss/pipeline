# -*- coding: utf-8 -*-
"""
Agent: Aggressive Trading | Step: CONTEXT (audit only)
Script 00: read-only snapshot of the PIT TOP50 value panel.

Inputs (read-only):
  data/processed/top50/top50_panel.parquet
  data/processed/top50/top50_membership.parquet
  data/interim/top50_build/summary.json  (optional)
Output:
  stdout + data/interim/agent_checks/aggressive_00_context.txt

Run from repo root:
  python -X utf8 scripts/experiments/agent_aggressive/00_context_snapshot.py
Deterministic. No randomness, no network, no dataset writes.
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PANEL_REL = Path("data/processed/top50/top50_panel.parquet")
MEMB_REL = Path("data/processed/top50/top50_membership.parquet")
SUMMARY_REL = Path("data/interim/top50_build/summary.json")
REPORT_REL = Path("data/interim/agent_checks/aggressive_00_context.txt")

OHLC = ["adjusted_open", "adjusted_high", "adjusted_low", "adjusted_close"]
EXCLUDED = {"GAZC", "GAZS", "GAZT"}
SUSP_START, SUSP_END = "2022-02-28", "2022-03-23"

LINES: list[str] = []


def emit(s: object = "") -> None:
    LINES.append(str(s))


def find_root() -> Path:
    for base in [Path.cwd(), *Path(__file__).resolve().parents]:
        if (base / PANEL_REL).exists():
            return base
    raise FileNotFoundError(
        f"{PANEL_REL} not found from cwd or script location. "
        "Run from the repository root."
    )


def main() -> None:
    root = find_root()
    panel_path = root / PANEL_REL
    st = panel_path.stat()

    emit("=" * 72)
    emit("AGENT: AGGRESSIVE TRADING | CONTEXT SNAPSHOT | SCRIPT 00")
    emit("=" * 72)

    # [0] META -------------------------------------------------------
    emit("\n[0] META")
    emit(f"run_utc           : {datetime.now(timezone.utc).isoformat()}")
    emit(f"python            : {sys.version.split()[0]}")
    emit(f"pandas            : {pd.__version__}")
    emit(f"numpy             : {np.__version__}")
    try:
        import pyarrow
        emit(f"pyarrow           : {pyarrow.__version__}")
    except ImportError:
        emit("pyarrow           : NOT INSTALLED")
    emit(f"root              : {root}")
    emit(f"panel_size_mb     : {st.st_size / 1e6:.2f}")
    emit(f"panel_mtime_utc   : {datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()}")
    sp = root / SUMMARY_REL
    if sp.exists():
        s = json.loads(sp.read_text(encoding="utf-8"))
        for k in ("created_at_utc", "pipeline_version", "panel_end_date",
                  "panel_rows", "membership_rows", "rows_without_current_day_bar"):
            emit(f"summary.{k:10s}: {s.get(k)}")
    else:
        emit("summary.json      : MISSING")

    df = pd.read_parquet(panel_path)
    df["tradedate"] = pd.to_datetime(df["tradedate"])
    df["ranking_asof_date"] = pd.to_datetime(df["ranking_asof_date"])

    # [1] SCHEMA -----------------------------------------------------
    emit("\n[1] SCHEMA")
    emit(f"rows={len(df):,}  cols={len(df.columns)}")
    for c in df.columns:
        n = int(df[c].isna().sum())
        emit(f"{c:22s} {str(df[c].dtype):16s} nulls={n:7d} ({n / len(df) * 100:5.2f}%)")
    emit(f"numtrades present     : {'numtrades' in df.columns}")
    emit(f"adjustment_status     : {'adjustment_status' in df.columns}")

    # [2] RANGE ------------------------------------------------------
    dates = pd.DatetimeIndex(sorted(df["tradedate"].unique()))
    emit("\n[2] RANGE")
    emit(f"tradedate         : {dates[0].date()} -> {dates[-1].date()}")
    emit(f"panel_dates       : {len(dates):,}")
    emit(f"unique_secid      : {df['secid'].nunique()}")
    mp = root / MEMB_REL
    if mp.exists():
        m = pd.read_parquet(mp, columns=["tradedate", "secid"])
        m["tradedate"] = pd.to_datetime(m["tradedate"])
        mg = m.merge(df[["tradedate", "secid"]], on=["tradedate", "secid"],
                     how="outer", indicator=True)
        emit(f"membership_rows   : {len(m):,}")
        emit(f"keys_match_panel  : {bool(mg['_merge'].eq('both').all())}")
    else:
        emit("membership        : MISSING")

    # [3] INTEGRITY (PASS/FAIL) --------------------------------------
    emit("\n[3] INTEGRITY")
    complete = df[OHLC].notna().all(axis=1)
    avail = df["bar_available"] == 1
    checks = {
        "unique(tradedate,secid)": not df.duplicated(["tradedate", "secid"]).any(),
        "ranking_asof < tradedate (PIT)": bool((df["ranking_asof_date"] < df["tradedate"]).all()),
        "universe_size <= 50": bool(df.groupby("tradedate")["secid"].nunique().max() <= 50),
        "no GAZC/GAZS/GAZT": not df["secid"].isin(EXCLUDED).any(),
        "no suspension dates": int(((df["tradedate"] >= SUSP_START) & (df["tradedate"] <= SUSP_END)).sum()) == 0,
        "bar_available=0 -> close NaN": bool(df.loc[~avail, "adjusted_close"].isna().all()),
        "no negative value": bool((df["value"] >= 0).all()),
    }
    for name, ok in checks.items():
        emit(f"{'PASS' if ok else 'FAIL'}  {name}")

    emit("\n[3b] COUNTERS (flags only, nothing corrected)")
    hi, lo = df["adjusted_high"], df["adjusted_low"]
    op, cl = df["adjusted_open"], df["adjusted_close"]
    emit(f"bar_available=0            : {int((~avail).sum()):,}")
    emit(f"incomplete OHLC | avail=1  : {int((avail & ~complete).sum()):,}")
    emit(f"close <= 0 (non-null)      : {int((cl <= 0).sum()):,}")
    emit(f"high < low  | complete     : {int((complete & (hi < lo)).sum()):,}")
    emit(f"close out of [low,high]    : {int((complete & ((cl > hi) | (cl < lo))).sum()):,}")
    emit(f"open out of [low,high]     : {int((complete & ((op > hi) | (op < lo))).sum()):,}")
    emit(f"value == 0 | avail=1       : {int((avail & (df['value'] == 0)).sum()):,}")
    emit(f"volume == 0 | avail=1      : {int((avail & (df['volume'] == 0)).sum()):,}")

    # [4] COVERAGE BY YEAR -------------------------------------------
    emit("\n[4] COVERAGE BY YEAR")
    tmp = df.assign(year=df["tradedate"].dt.year,
                    close_pos=(df["adjusted_close"] > 0).astype(float))
    yr = tmp.groupby("year").agg(sessions=("tradedate", "nunique"),
                                 rows=("secid", "size"),
                                 bar_cov=("bar_available", "mean"),
                                 close_pos=("close_pos", "mean"))
    for y, r in yr.iterrows():
        emit(f"{y}  sessions={int(r.sessions):4d}  mean_members={r.rows / r.sessions:5.1f}"
             f"  bar_cov={r.bar_cov * 100:6.2f}%  close>0={r.close_pos * 100:6.2f}%")

    # [5] FRESHNESS ---------------------------------------------------
    emit("\n[5] FRESHNESS")
    last = dates[-1]
    emit(f"last_panel_date   : {last.date()}")
    emit(f"today_local       : {datetime.now().date()}")
    emit(f"calendar_gap_days : {(datetime.now().date() - last.date()).days}")
    tail = df[df["tradedate"].isin(dates[-5:])].groupby("tradedate").agg(
        members=("secid", "size"),
        no_bar=("bar_available", lambda s: int((s == 0).sum())))
    emit("last 5 sessions:")
    emit(tail.to_string())

    # [6] CURRENT TOP50 ON LAST DATE ----------------------------------
    emit(f"\n[6] CURRENT MEMBERS @ {last.date()}")
    cur = df[df["tradedate"] == last].sort_values("rank").copy()
    show = pd.DataFrame({
        "rank": cur["rank"].astype(int),
        "secid": cur["secid"],
        "v60_bn": (cur["value_60d"] / 1e9).round(2),
        "v_day_mn": (cur["value"] / 1e6).round(1),
        "close": cur["adjusted_close"].round(4),
        "bar": cur["bar_available"].astype(int),
        "board": cur["price_board"].fillna("-"),
    })
    if "adjustment_status" in cur.columns:
        show["adj_status"] = cur["adjustment_status"].fillna("-")
    emit(show.to_string(index=False))

    # [7] STALENESS OF CURRENT MEMBERS --------------------------------
    emit("\n[7] STALE MEMBERS (last available bar behind last panel date)")
    last_bar = df.loc[avail].groupby("secid")["tradedate"].max()
    rows = []
    for sec in cur["secid"]:
        lb = last_bar.get(sec)
        lag = len(dates) - 1 - dates.get_loc(lb) if lb is not None else None
        if lb is None or lag > 0:
            rows.append({"secid": sec,
                         "last_bar": str(lb.date()) if lb is not None else "NEVER",
                         "sessions_behind": lag if lag is not None else "ALL"})
    emit(pd.DataFrame(rows).to_string(index=False) if rows else "none")

    emit("\nEND OF REPORT")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        emit("\nERROR:\n" + traceback.format_exc())
    report = "\n".join(LINES)
    print(report)
    try:
        out = find_root() / REPORT_REL
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"\n[saved] {out}")
    except Exception as e:
        print(f"[report not saved] {e}")