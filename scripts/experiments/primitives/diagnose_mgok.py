
# Folder: scripts/experiments/primitives/
# File: diagnose_mgok.py
# Purpose: Diagnose panel/database inconsistency for MGOK.

import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]

PANEL = ROOT / "data/processed/top50/top50_panel.parquet"
DB = ROOT / "data/processed/moex_daily_adjusted.sqlite"

panel = pd.read_parquet(PANEL)
panel["tradedate"] = pd.to_datetime(panel["tradedate"])
panel["secid"] = panel["secid"].astype(str).str.strip().str.upper()

mgok_panel = panel[
    (panel["secid"] == "MGOK")
    & (panel["bar_available"] == 1)
].copy()

print("\n=== FILES ===")
for path in [PANEL, DB]:
    stat = path.stat()
    print(
        path.name,
        "size:", stat.st_size,
        "modified:", pd.Timestamp(stat.st_mtime, unit="s"),
    )

print("\n=== PANEL: MGOK ===")
print("Rows with bar_available=1:", len(mgok_panel))
if not mgok_panel.empty:
    print("Date range:", mgok_panel["tradedate"].min(),
          "—", mgok_panel["tradedate"].max())
    print(mgok_panel[
        ["tradedate", "secid", "rank", "bar_available", "adjusted_close"]
        if "adjusted_close" in mgok_panel.columns
        else ["tradedate", "secid", "rank", "bar_available"]
    ].head(10).to_string(index=False))

print("\n=== SQLITE: MGOK ===")
conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)

queries = [
    (
        "Exact SECID, all boards",
        """
        SELECT boardid, COUNT(*), MIN(tradedate), MAX(tradedate)
        FROM adjusted_daily_bars
        WHERE secid = 'MGOK'
        GROUP BY boardid
        """
    ),
    (
        "Exact SECID, approved boards",
        """
        SELECT boardid, COUNT(*), MIN(tradedate), MAX(tradedate)
        FROM adjusted_daily_bars
        WHERE secid = 'MGOK'
          AND boardid IN ('TQBR', 'EQBR')
        GROUP BY boardid
        """
    ),
    (
        "Normalized SECID",
        """
        SELECT secid, boardid, COUNT(*), MIN(tradedate), MAX(tradedate)
        FROM adjusted_daily_bars
        WHERE UPPER(TRIM(secid)) = 'MGOK'
        GROUP BY secid, boardid
        """
    ),
]

for title, query in queries:
    print(f"\n{title}:")
    rows = conn.execute(query).fetchall()
    if rows:
        for row in rows:
            print(row)
    else:
        print("NO ROWS")

print("\n=== PANEL DATES VS SQLITE ===")
if not mgok_panel.empty:
    dates = mgok_panel["tradedate"].dt.strftime("%Y-%m-%d").tolist()
    placeholders = ",".join("?" for _ in dates)

    query = f"""
        SELECT tradedate, boardid, adjusted_close
        FROM adjusted_daily_bars
        WHERE UPPER(TRIM(secid)) = 'MGOK'
          AND tradedate IN ({placeholders})
        ORDER BY tradedate, boardid
    """

    rows = conn.execute(query, dates).fetchall()
    print("Matching DB rows:", len(rows))
    for row in rows[:20]:
        print(row)

conn.close()
print("\nDIAGNOSTIC COMPLETE")
