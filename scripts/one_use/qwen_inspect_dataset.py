# scripts/one_use/_qwen_data.py
"""Discover & call YOUR load_source_data(); normalize to wide close panel. Compact probe."""
import os, sys, glob, importlib.util
import pandas as pd, numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def find_loader():
    hits = []
    for py in glob.glob(os.path.join(ROOT, "scripts", "**", "*.py"), recursive=True):
        try: txt = open(py, encoding="utf-8").read()
        except Exception: continue
        if "def load_source_data" in txt: hits.append(py)
    if not hits: raise RuntimeError("load_source_data not found under scripts/")
    hits.sort(key=lambda p: ("one_use" in p, len(p)))
    return hits[0]

def load_panel():
    path = find_loader()
    os.chdir(ROOT)  # so relative DB_PATH resolves
    spec = importlib.util.spec_from_file_location("_qwen_src", path)
    mod = importlib.util.module_from_spec(spec); sys.modules["_qwen_src"] = mod
    spec.loader.exec_module(mod)
    df, dates = mod.load_source_data()
    return df, dates, path

def to_wide_close(df):
    low = {str(c).lower(): c for c in df.columns}
    # wide already: datetime index, ticker columns
    if isinstance(df.index, pd.DatetimeIndex) and not any(k in low for k in ("ticker","secid","close")):
        return df.apply(pd.to_numeric, errors="coerce"), "wide"
    tcol = next((low[k] for k in ("ticker","secid","symbol","security") if k in low), None)
    ccol = next((low[k] for k in ("adj_close","adjusted_close","close_adj","close","price") if k in low), None)
    dcol = next((low[k] for k in ("date","tradedate","trade_date") if k in low), None)
    if tcol and ccol:
        tmp = df
        if dcol is None:
            tmp = df.reset_index(); dcol = tmp.columns[0]
        w = tmp.pivot_table(index=dcol, columns=tcol, values=ccol, aggfunc="last")
        w.index = pd.to_datetime(w.index)
        return w.sort_index(), "long->wide"
    raise RuntimeError(f"schema? cols={list(df.columns)[:15]} idx={type(df.index).__name__}")

if __name__ == "__main__":
    df, dates, path = load_panel()
    print("loader:", os.path.relpath(path, ROOT))
    print("raw shape:", df.shape, "| idx:", type(df.index).__name__, "| cols:", list(df.columns)[:12])
    wide, fmt = to_wide_close(df)
    print("format:", fmt, "| panel:", wide.shape)
    print("dates:", str(wide.index.min().date()), "->", str(wide.index.max().date()))
    print("n_tickers:", wide.shape[1])
    print("tickers:", ",".join(map(str, wide.columns)))